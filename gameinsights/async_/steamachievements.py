import asyncio
from typing import Any

import aiohttp

from gameinsights.async_.base import AsyncBaseSource
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.sources.steamachievements import _STEAMACHIEVEMENT_LABELS
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
            data_packed = self._transform_data(data=percentage_data, schema_data=schema_data)
        else:
            pct_response = await self._make_request(params=params)
            if pct_response.status_code != 200:
                return self._build_error_result(
                    f"Failed to connect to API. Status code: {pct_response.status_code}.",
                    verbose=verbose,
                )
            percentage_data = pct_response.json()
            data_packed = self._transform_data(data=percentage_data)

        return SuccessResult(
            success=True, data=self._apply_label_filter(data_packed, selected_labels)
        )

    def _transform_data(
        self, data: dict[str, Any], schema_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        percentage_data = data.get("achievementpercentages", {}).get("achievements", [])
        if not percentage_data:
            return {
                "achievements_count": None,
                "achievements_percentage_average": None,
                "achievements_list": None,
            }

        base_achievements, achievements_count, achievements_percentage_average = (
            self._calculate_average_percentage(percentage_data)
        )

        schema_achievements = (
            schema_data.get("game", {}).get("availableGameStats", {}).get("achievements", [])
            if schema_data
            else None
        )

        achievements_list = (
            self._merge_achievements(
                base_achievements=base_achievements, schema_data=schema_achievements
            )
            if schema_achievements
            else base_achievements
        )

        return {
            "achievements_count": achievements_count,
            "achievements_percentage_average": achievements_percentage_average,
            "achievements_list": achievements_list,
        }

    def _calculate_average_percentage(
        self, achievements: list[dict[str, Any]]
    ) -> tuple[list[dict[str, Any]], int, float]:
        transformed = []
        total = 0.0
        for entry in achievements:
            try:
                percentage = float(entry["percent"])
                transformed.append({"name": entry["name"], "percent": percentage})
                total += percentage
            except (KeyError, ValueError):
                continue
        count = len(transformed)
        average = round(total / count, 2) if count > 0 else 0.0
        return transformed, count, average

    def _merge_achievements(
        self,
        base_achievements: list[dict[str, Any]],
        schema_data: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        schema_lookup = {}
        for entry in schema_data:
            name = entry.get("name")
            display_name = entry.get("displayName")
            if not name or not display_name:
                continue
            schema_lookup[name] = {
                "display_name": display_name,
                "hidden": entry.get("hidden"),
                "description": entry.get("description"),
            }

        merged = []
        for acv in base_achievements:
            name = acv["name"]
            percent = acv["percent"]
            schema_info = schema_lookup.get(name, {})
            merged.append(
                {
                    "name": name,
                    "percent": percent,
                    "display_name": schema_info.get("display_name"),
                    "hidden": schema_info.get("hidden"),
                    "description": schema_info.get("description"),
                }
            )
        return merged
