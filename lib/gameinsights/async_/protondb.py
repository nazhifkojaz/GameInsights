from typing import Any

import aiohttp

from gameinsights.async_.base import AsyncBaseSource
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.sources.protondb import _PROTONDB_LABELS
from gameinsights.utils.async_ratelimit import async_rate_limited


class AsyncProtonDB(AsyncBaseSource):
    _base_url = "https://www.protondb.com"
    _valid_labels: tuple[str, ...] = _PROTONDB_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_PROTONDB_LABELS)

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        super().__init__(session=session)

    @async_rate_limited(calls=60, period=60)
    async def fetch(
        self,
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        steam_appid = self._prepare_identifier(steam_appid, verbose=verbose)
        response = await self._make_request(
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

        data = self._fetch_and_parse_json(response)
        if data is None:
            return self._build_error_result(
                f"Failed to parse ProtonDB response for game {steam_appid}.", verbose=verbose
            )

        data_packed = self._transform_data(data)
        data_packed["steam_appid"] = steam_appid

        if selected_labels:
            data_packed = {
                label: data_packed[label]
                for label in self._filter_valid_labels(selected_labels)
                if label in data_packed
            }

        return SuccessResult(success=True, data=data_packed)

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "protondb_tier": data.get("tier"),
            "protondb_score": data.get("score"),
            "protondb_trending": data.get("trendingTier"),
            "protondb_confidence": data.get("confidence"),
            "protondb_total": data.get("total"),
        }
