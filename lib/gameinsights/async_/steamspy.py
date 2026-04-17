from typing import Any

import aiohttp

from gameinsights.async_.base import AsyncBaseSource
from gameinsights.sources._parsers import transform_steamspy
from gameinsights.sources._schemas import _STEAMSPY_LABELS
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.utils.async_ratelimit import async_rate_limited


class AsyncSteamSpy(AsyncBaseSource):
    _valid_labels: tuple[str, ...] = _STEAMSPY_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMSPY_LABELS)
    _base_url = "https://steamspy.com/api.php"

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        super().__init__(session=session)

    @async_rate_limited(calls=60, period=60)
    async def fetch(
        self,
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        steam_appid = self._prepare_identifier(steam_appid, verbose)
        params = {"request": "appdetails", "appid": steam_appid}
        response = await self._make_request(params=params)

        data = self._fetch_and_parse_json(response, verbose)
        if data is None:
            return self._build_error_result(
                f"Failed to connect to API. Status code: {response.status_code}", verbose=verbose
            )

        if not data.get("name"):
            return self._build_error_result(
                f"Game with appid {steam_appid} is not found.", verbose=verbose
            )

        data_packed = self._transform_data(data=data)
        return SuccessResult(
            success=True, data=self._apply_label_filter(data_packed, selected_labels)
        )

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        return transform_steamspy(data)
