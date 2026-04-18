"""Pure utility functions shared between Collector and AsyncCollector."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Generic, NamedTuple, TypeVar

from gameinsights.exceptions import (
    GameInsightsError,
    GameNotFoundError,
    SourceUnavailableError,
)

SourceT = TypeVar("SourceT", covariant=True)


@dataclass
class FetchResult:
    """Result of fetching data for a single game/user."""

    identifier: str
    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


class _SourceConfig(NamedTuple, Generic[SourceT]):
    source: SourceT
    fields: list[str]
    is_primary: bool = False


def post_process_raw_data(raw_data: dict[str, Any], boxleiter_multiplier: int) -> None:
    """Derive fields that depend on aggregated data from multiple sources.

    Called after all source fetches complete, before GameDataModel construction.
    Mutates raw_data in place.

    Derived fields:
        - early_access: True if "Early Access" is in categories list
        - copies_sold: Boxleiter estimate (total_reviews * multiplier) when not already set
        - estimated_revenue: copies_sold * price_final when not already set
    """
    categories = raw_data.get("categories")
    if isinstance(categories, list) and categories and raw_data.get("early_access") is None:
        raw_data["early_access"] = "Early Access" in categories

    if raw_data.get("copies_sold") is None:
        total_reviews = raw_data.get("total_reviews")
        if isinstance(total_reviews, (int, float)) and total_reviews > 0:
            raw_data["copies_sold"] = int(total_reviews * boxleiter_multiplier)

    if raw_data.get("estimated_revenue") is None:
        copies_sold = raw_data.get("copies_sold")
        price_final = raw_data.get("price_final")
        if isinstance(copies_sold, (int, float)) and isinstance(price_final, (int, float)):
            raw_data["estimated_revenue"] = int(copies_sold * price_final)


def classify_source_error(source_name: str, error_message: str) -> GameInsightsError:
    """Translate an ErrorResult string into a typed exception.

    Single authoritative mapping from raw error strings to exception types.

    Classification logic (first match wins):
      - SteamStore "not available in region" -> GameNotFoundError (primary source)
      - "failed to parse" -> SourceUnavailableError (parse errors)
      - "failed to fetch/obtain" -> SourceUnavailableError (fetch errors)
      - Network/timeout/connection errors -> SourceUnavailableError
      - HTTP error status codes -> SourceUnavailableError
      - "not found" with appid/steamid -> GameNotFoundError (game/user doesn't exist)
      - anything else -> GameInsightsError (base)

    Args:
        source_name: Name of the source that failed (e.g., "SteamStore")
        error_message: The error string from ErrorResult

    Returns:
        Appropriate exception instance based on error classification
    """
    lowered = error_message.lower()

    if "not available in the specified region" in lowered:
        match = re.search(r"appid\s+(\S+)", lowered)
        identifier_hint = match.group(1).rstrip(".,") if match else "unknown"
        return GameNotFoundError(identifier=identifier_hint, message=error_message)

    if "failed to parse" in lowered:
        return SourceUnavailableError(source=source_name, reason=error_message)

    if "failed to fetch" in lowered or "failed to obtain" in lowered:
        return SourceUnavailableError(source=source_name, reason=error_message)

    network_keywords = [
        "status code: 599",
        "failed to connect",
        "connection",
        "timeout",
        "ssl",
        "toomanyredirects",
    ]
    if any(keyword in lowered for keyword in network_keywords):
        return SourceUnavailableError(source=source_name, reason=error_message)

    if re.search(r"status(?:\s+code)?:?\s*[45]\d{2}", lowered):
        return SourceUnavailableError(source=source_name, reason=error_message)

    if "not found" in lowered:
        identifier_hint = "unknown"
        for pattern in [r"appid\s+(\S+)", r"steamid\s+(\S+)"]:
            match = re.search(pattern, lowered)
            if match:
                identifier_hint = match.group(1).rstrip(".,")
                break
        return GameNotFoundError(identifier=identifier_hint, message=error_message)

    return GameInsightsError(error_message)


def raise_for_fetch_failure(
    source_name: str,
    error_message: str,
    is_primary: bool = False,
) -> None:
    """Convert an ErrorResult into a typed exception and raise it.

    The is_primary flag marks SteamStore (and SteamUser for user data) as
    the authoritative existence check. When a supplementary source fails
    with "not found", we raise SourceUnavailableError instead — the game/user
    still exists, that source just lacks data.

    Args:
        source_name: Name of the source that failed
        error_message: The error string from ErrorResult
        is_primary: True if this is the primary source (SteamStore/SteamUser)

    Raises:
        GameNotFoundError: If primary source reports "not found"
        SourceUnavailableError: If supplementary source fails or primary has network error
        GameInsightsError: For other errors
    """
    exc = classify_source_error(source_name, error_message)

    if not is_primary and isinstance(exc, GameNotFoundError):
        raise SourceUnavailableError(source=source_name, reason=error_message)

    raise exc


def record_fetch_outcome(
    source_name: str,
    scope: str,
    logger: Any,
    identifier: str,
    verbose: bool,
    timing: Any,
    success: bool,
) -> None:
    """Record metrics and log the outcome of a source fetch."""
    from gameinsights.utils import metrics

    duration_ms = round(timing.duration * 1000, 2)
    metrics.counter("source_fetch_total", source=source_name, scope=scope)
    if success:
        metrics.counter("source_fetch_success_total", source=source_name, scope=scope)
    else:
        metrics.counter("source_fetch_error_total", source=source_name, scope=scope)
    logger.log_event(
        "source_fetch_complete",
        verbose=verbose,
        scope=scope,
        identifier=identifier,
        success=success,
        duration_ms=duration_ms,
    )


def record_fetch_exception(
    source_name: str,
    scope: str,
    logger: Any,
    identifier: str,
    error: str,
) -> None:
    """Record metrics and log for a source fetch exception."""
    from gameinsights.utils import metrics

    metrics.counter("source_fetch_exception_total", source=source_name, scope=scope)
    logger.log_event(
        "source_fetch_exception",
        level="error",
        verbose=True,
        scope=scope,
        identifier=identifier,
        error=error,
    )


def normalize_active_player_rows(
    all_data: list[dict[str, Any]],
    all_months: set[str],
    fill_na_as: int = -1,
) -> tuple[list[dict[str, Any]], list[str], list[str], list[str]]:
    """Normalize active-player monthly data, filling missing months.

    Returns:
        (normalized_data, sorted_months, fixed_columns, numeric_columns)
    """
    sorted_months = sorted(all_months)
    fixed_columns = ["steam_appid", "name", "peak_active_player_all_time"]
    numeric_columns = ["peak_active_player_all_time"] + sorted_months

    normalized_data: list[dict[str, Any]] = []
    for record in all_data:
        normalized_record: dict[str, Any] = {}
        for col in fixed_columns + sorted_months:
            value = record.get(col)
            if col in numeric_columns:
                normalized_record[col] = value if value is not None else fill_na_as
            else:
                normalized_record[col] = value
        normalized_data.append(normalized_record)

    return normalized_data, sorted_months, fixed_columns, numeric_columns
