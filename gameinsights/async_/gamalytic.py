from typing import Any

import aiohttp

from gameinsights.async_.base import AsyncBaseSource
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.sources.gamalytic import _GAMALYTICS_LABELS
from gameinsights.utils.async_ratelimit import async_rate_limited


class AsyncGamalytic(AsyncBaseSource):
    _valid_labels: tuple[str, ...] = _GAMALYTICS_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_GAMALYTICS_LABELS)
    _base_url = "https://api.gamalytic.com/game"

    def __init__(
        self, api_key: str | None = None, session: aiohttp.ClientSession | None = None
    ) -> None:
        super().__init__(session=session)
        self._api_key = api_key

    @async_rate_limited(calls=500, period=24 * 60 * 60)
    async def fetch(
        self,
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        steam_appid = self._prepare_identifier(steam_appid, verbose)
        response = await self._make_request(endpoint=steam_appid)

        if response.status_code == 404:
            return self._build_error_result(
                f"Game with appid {steam_appid} is not found.", verbose=verbose
            )

        data = self._fetch_and_parse_json(response, verbose)
        if data is None:
            return self._build_error_result(
                f"Failed to connect to API. Status code: {response.status_code}", verbose=verbose
            )

        data_packed = self._transform_data(data=data)
        return SuccessResult(
            success=True, data=self._apply_label_filter(data_packed, selected_labels)
        )

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            "steam_appid": data.get("steamId"),
            "name": data.get("name"),
            "price": data.get("price"),
            "reviews": data.get("reviews"),
            "reviews_steam": data.get("reviewsSteam"),
            "followers": data.get("followers"),
            "average_playtime_h": data.get("avgPlaytime"),
            "review_score": data.get("reviewScore"),
            "tags": data.get("tags"),
            "genres": data.get("genres"),
            "features": data.get("features"),
            "languages": data.get("languages"),
            "developers": data.get("developers"),
            "publishers": data.get("publishers"),
            "release_date": data.get("releaseDate"),
            "first_release_date": data.get("firstReleaseDate"),
            "unreleased": data.get("unreleased"),
            "early_access": data.get("earlyAccess"),
            "copies_sold": data.get("copiesSold"),
            "estimated_revenue": data.get("revenue"),
            "players": data.get("players"),
            "owners": data.get("owners"),
        }
