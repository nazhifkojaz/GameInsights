"""Shared helper functions for BaseSource and AsyncBaseSource.

Pure non-I/O helpers that both base classes delegate to, eliminating
duplication between sync and async source implementations.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from gameinsights.sources.base import ErrorResult


def build_error_result(
    error_message: str,
    log_fn: Callable[..., None],
    verbose: bool = True,
) -> ErrorResult:
    log_fn(error_message, level="error", verbose=verbose)
    return {"success": False, "error": error_message}


def prepare_identifier(
    identifier: str,
    log_fn: Callable[..., None],
    verbose: bool = True,
) -> str:
    identifier_str = str(identifier)
    log_fn(
        f"Fetching data for appid {identifier_str}.",
        level="info",
        verbose=verbose,
    )
    return identifier_str


def fetch_and_parse_json(
    response: Any,
    extra_json_exceptions: tuple[type[Exception], ...] = (),
) -> dict[str, Any] | None:
    if response.status_code != 200:
        return None
    try:
        data = response.json()
        if isinstance(data, dict):
            return data
        return None
    except Exception as exc:
        if isinstance(exc, ValueError) or isinstance(exc, extra_json_exceptions):
            return None
        raise


def filter_valid_labels(
    selected_labels: list[str],
    valid_labels: list[str] | tuple[str, ...] | None = None,
    class_valid_labels_set: frozenset[str] | None = None,
    class_valid_labels: tuple[str, ...] | None = None,
    log_fn: Callable[..., None] | None = None,
) -> list[str]:
    if valid_labels is not None:
        validation_set: frozenset[str] = frozenset(valid_labels)
    else:
        validation_set = class_valid_labels_set  # type: ignore[assignment]
    valid: list[str] = []
    invalid: list[str] = []
    for label in selected_labels:
        (valid if label in validation_set else invalid).append(label)
    if invalid and log_fn is not None:
        reference_labels = valid_labels if valid_labels is not None else class_valid_labels
        log_fn(
            f"Ignoring the following invalid labels: {invalid}, "
            f"valid labels are: {reference_labels}",
            level="warning",
            verbose=True,
        )
    return valid


def apply_label_filter(
    data: dict[str, Any],
    selected_labels: list[str] | None,
    filtered_labels: list[str],
) -> dict[str, Any]:
    if selected_labels:
        return {label: data[label] for label in filtered_labels if label in data}
    return data
