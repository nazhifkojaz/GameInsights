from typing import Any

import aiohttp

from gameinsights.async_.base import AsyncBaseSource
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.sources.steamspy import _STEAMSPY_LABELS
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
        tags = data.get("tags", [])
        tags = [tag for tag in tags] if isinstance(tags, dict) else []

        raw_languages = data.get("languages")
        if isinstance(raw_languages, str):
            languages = [lang.strip() for lang in raw_languages.split(",") if lang.strip()]
        elif isinstance(raw_languages, list):
            languages = raw_languages
        else:
            languages = []

        return {
            "steam_appid": data.get("appid"),
            "name": data.get("name"),
            "developers": data.get("developer"),
            "publishers": data.get("publisher"),
            "positive_reviews": data.get("positive"),
            "negative_reviews": data.get("negative"),
            "owners": data.get("owners"),
            "average_forever": data.get("average_forever"),
            "average_playtime_min": data.get("average_forever"),
            "average_2weeks": data.get("average_2weeks"),
            "median_forever": data.get("median_forever"),
            "median_2weeks": data.get("median_2weeks"),
            "price": data.get("price"),
            "initial_price": data.get("initialprice"),
            "discount": data.get("discount"),
            "ccu": data.get("ccu"),
            "languages": languages,
            "genres": data.get("genre"),
            "tags": tags,
        }
