import asyncio
from typing import Any

import aiohttp

from gameinsights.async_.base import AsyncBaseSource
from gameinsights.sources._parsers import transform_steamachievements
from gameinsights.sources._schemas import _STEAMACHIEVEMENT_LABELS
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.utils.async_ratelimit import async_rate_limited


class AsyncSteamAchievements(AsyncBaseSource):
    _valid_labels: tuple[str, ...] = _STEAMACHIEVEMENT_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMACHIEVEMENT_LABELS)
    _base_url = (
        "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002"
    )
    _schema_url = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2"

    def __init__(
        self, api_key: str | None = None, session: aiohttp.ClientSession | None = None
    ) -> None:
        super().__init__(session=session)
        self._api_key = api_key

    @async_rate_limited(calls=100000, period=24 * 60 * 60)
    async def fetch(
        self,
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        steam_appid = self._prepare_identifier(steam_appid, verbose)

        if not self._api_key:
            self.logger.log(
                "API Key is not assigned. Some details will not be included.",
                level="warning",
                verbose=verbose,
            )

        params = {"gameid": steam_appid}

        if self._api_key:
            # Fire both requests in parallel
            schema_params = {"appid": steam_appid, "key": self._api_key}
            pct_response, schema_response = await asyncio.gather(
                self._make_request(params=params),
                self._make_request(url=self._schema_url, params=schema_params),
            )

            if pct_response.status_code != 200:
                return self._build_error_result(
                    f"Failed to connect to API. Status code: {pct_response.status_code}.",
                    verbose=verbose,
                )

            if schema_response.status_code == 403:
                return self._build_error_result(
                    f"Access denied, verify your API Key. Status code: {schema_response.status_code}.",
                    verbose=verbose,
                )
            if not schema_response.ok:
                return self._build_error_result(
                    f"Failed to connect to API. Status code: {schema_response.status_code}.",
                    verbose=verbose,
                )

            percentage_data = pct_response.json()
            schema_data: dict[str, Any] = schema_response.json()
            data_packed = self._transform_data(
                data=percentage_data, schema_data=schema_data, verbose=verbose
            )
        else:
            pct_response = await self._make_request(params=params)
            if pct_response.status_code != 200:
                return self._build_error_result(
                    f"Failed to connect to API. Status code: {pct_response.status_code}.",
                    verbose=verbose,
                )
            percentage_data = pct_response.json()
            data_packed = self._transform_data(data=percentage_data, verbose=verbose)

        return SuccessResult(
            success=True, data=self._apply_label_filter(data_packed, selected_labels)
        )

    def _transform_data(
        self,
        data: dict[str, Any],
        schema_data: dict[str, Any] | None = None,
        *,
        verbose: bool = True,
    ) -> dict[str, Any]:
        return transform_steamachievements(
            data,
            schema_data=schema_data,
            log_fn=lambda msg: self.logger.log(msg, level="debug", verbose=verbose),
        )
