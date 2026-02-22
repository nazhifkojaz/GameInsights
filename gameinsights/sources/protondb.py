# ---------------------------
# ProtonDB Source
# Fetches Linux/Steam Deck compatibility data from protondb.com
#
# Uses the ProtonDB JSON API at /api/v1/reports/summaries/{appid}.json
# which returns tier, score, confidence, and trending data.
#
# Data Attribution: Compatibility data is sourced from protondb.com
# ---------------------------

from typing import Any

from gameinsights.sources.base import BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited

_PROTONDB_LABELS = (
    "protondb_tier",
    "protondb_score",
    "protondb_trending",
    "protondb_confidence",
    "protondb_total",
)


class ProtonDB(BaseSource):
    """ProtonDB source for Linux/Steam Deck compatibility data.

    The source fetches compatibility report summaries from ProtonDB's JSON API
    for a given Steam app ID. ProtonDB uses a tier system (pending, bronze,
    silver, gold, platinum) to indicate how well a game runs on Linux through Proton.

    API Response shape:
        {
            "bestReportedTier": "platinum",
            "confidence": "strong",
            "score": 0.96,
            "tier": "platinum",
            "total": 323,
            "trendingTier": "platinum"
        }
    """

    _base_url = "https://www.protondb.com"
    _valid_labels: tuple[str, ...] = _PROTONDB_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_PROTONDB_LABELS)

    @logged_rate_limited(calls=60, period=60)
    def fetch(
        self,
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        """Fetch ProtonDB compatibility data based on Steam app ID.

        Args:
            steam_appid: The Steam app ID of the game.
            verbose: If True, will log the fetching process.
            selected_labels: A list of labels to filter the data.

        Returns:
            SourceResult: A dictionary containing the status and compatibility data.
        """
        steam_appid = self._prepare_identifier(steam_appid, verbose=verbose)

        response = self._make_request(
            endpoint=f"/api/v1/reports/summaries/{steam_appid}.json",
        )

        if response.status_code == 404:
            return self._build_error_result(
                f"Game {steam_appid} not found on ProtonDB.", verbose=verbose
            )
        if response.status_code != 200:
            return self._build_error_result(
                f"Failed to fetch data with status code: {response.status_code}", verbose=verbose
            )

        try:
            summary = response.json()
        except Exception:
            return self._build_error_result(
                f"Failed to parse ProtonDB response for game {steam_appid}.", verbose=verbose
            )

        data_packed = self._transform_data(summary)
        data_packed["steam_appid"] = steam_appid

        # Apply label filtering
        if selected_labels:
            data_packed = {
                label: data_packed[label]
                for label in self._filter_valid_labels(selected_labels)
                if label in data_packed
            }

        return SuccessResult(success=True, data=data_packed)

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform ProtonDB API summary into the expected format.

        API fields mapped:
            - tier -> protondb_tier (e.g., "platinum", "gold", "silver", "bronze", "pending")
            - score -> protondb_score (float 0-1, e.g., 0.96)
            - trendingTier -> protondb_trending (tier string for recent reports)
            - confidence -> protondb_confidence (e.g., "strong", "good", "inadequate")
            - total -> protondb_total (integer count of reports)

        Args:
            data: Raw summary data from ProtonDB API.

        Returns:
            Dict with valid labels only.
        """
        return {
            "protondb_tier": data.get("tier"),
            "protondb_score": data.get("score"),
            "protondb_trending": data.get("trendingTier"),
            "protondb_confidence": data.get("confidence"),
            "protondb_total": data.get("total"),
        }
