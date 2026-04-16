from typing import Any

import aiohttp

from gameinsights.async_.base import AsyncBaseSource
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.sources.steamstore import _STEAM_LABELS
from gameinsights.utils.async_ratelimit import async_rate_limited


class AsyncSteamStore(AsyncBaseSource):
    _valid_labels: tuple[str, ...] = _STEAM_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAM_LABELS)
    _base_url = "https://store.steampowered.com/api/appdetails"

    def __init__(
        self,
        region: str = "us",
        language: str = "english",
        api_key: str | None = None,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        super().__init__(session=session)
        self._region = region
        self._language = language
        self._api_key = api_key

    @property
    def region(self) -> str:
        return self._region

    @region.setter
    def region(self, value: str) -> None:
        if self._region != value:
            self._region = value

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        if self._language != value:
            self._language = value

    @async_rate_limited(calls=60, period=60)
    async def fetch(
        self,
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        steam_appid = self._prepare_identifier(steam_appid, verbose)
        params = {"appids": steam_appid, "cc": self._region, "l": self._language}
        response = await self._make_request(params=params)

        data = self._fetch_and_parse_json(response, verbose)
        if data is None:
            return self._build_error_result(
                f"Failed to connect to API. Status code: {response.status_code}.",
                verbose=verbose,
            )

        if steam_appid not in data or not data[steam_appid]["success"]:
            return self._build_error_result(
                f"Failed to fetch data for appid {steam_appid}, or appid is not available in the specified region ({self._region}) or language ({self._language}).",
                verbose=verbose,
            )

        data_packed = self._transform_data(data[steam_appid]["data"])
        return SuccessResult(
            success=True, data=self._apply_label_filter(data_packed, selected_labels)
        )

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        price_overview = data.get("price_overview") or {}
        release_date = data.get("release_date") or {}
        platforms = data.get("platforms") or {}
        genres = data.get("genres") or []
        categories = data.get("categories") or []
        ratings = data.get("ratings") or {}

        return {
            "steam_appid": data.get("steam_appid"),
            "name": data.get("name"),
            "type": data.get("type"),
            "is_coming_soon": release_date.get("coming_soon"),
            "release_date": release_date.get("date"),
            "is_free": data.get("is_free"),
            "price_currency": price_overview.get("currency"),
            "price_initial": (
                price_overview.get("initial") / 100  # type: ignore[operator]
                if isinstance(price_overview, dict) and price_overview.get("initial") is not None
                else None
            ),
            "price_final": (
                price_overview.get("final") / 100  # type: ignore[operator]
                if isinstance(price_overview, dict) and price_overview.get("final") is not None
                else None
            ),
            "developers": data.get("developers"),
            "publishers": data.get("publishers"),
            "platforms": [
                platform
                for platform, is_supported in platforms.items()
                if isinstance(platforms, dict) and is_supported
            ],
            "categories": [category.get("description") for category in categories],
            "genres": [genre.get("description") for genre in genres],
            "metacritic_score": data.get("metacritic", {}).get("score"),
            "recommendations": (
                data.get("recommendations", {}).get("total")
                if isinstance(data.get("recommendations"), dict)
                else data.get("recommendations")
            ),
            "achievements": data.get("achievements", {}).get("total"),
            "content_rating": (
                [
                    {"rating_type": rating_type, "rating": rating.get("rating")}
                    for rating_type, rating in ratings.items()
                    if isinstance(ratings, dict) and isinstance(rating, dict)
                ]
                if ratings
                else []
            ),
        }
