import asyncio
from typing import Any, Literal

import aiohttp

from gameinsights.async_.base import AsyncBaseSource
from gameinsights.sources._parsers import transform_steamuser
from gameinsights.sources._schemas import _STEAMUSER_LABELS, CommunityVisibilityState
from gameinsights.sources.base import SourceResult, SuccessResult
from gameinsights.utils.async_ratelimit import async_rate_limited


class AsyncSteamUser(AsyncBaseSource):
    _valid_labels: tuple[str, ...] = _STEAMUSER_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMUSER_LABELS)
    _base_url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002"
    _owned_games_url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    _recently_played_url = (
        "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/"
    )

    def __init__(
        self, api_key: str | None = None, session: aiohttp.ClientSession | None = None
    ) -> None:
        super().__init__(session=session)
        self._api_key = api_key

    @async_rate_limited(calls=100000, period=24 * 60 * 60)
    async def fetch(
        self,
        steamid: str,
        include_free_games: bool = True,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        self.logger.log(
            f"Fetching user data for steamid {steamid}.", level="info", verbose=verbose
        )

        if not self._api_key:
            return self._build_error_result(
                "API Key is not assigned. Unable to fetch data.", verbose=verbose
            )

        steamid = str(steamid)
        summary_result = await self._fetch_summary(steamid=steamid, verbose=verbose)
        if not summary_result["success"]:
            return self._build_error_result(summary_result["error"], verbose=False)

        data_packed = {
            **summary_result["data"],
            "owned_games": {},
            "recently_played_games": {},
        }

        if data_packed["community_visibility_state"] == CommunityVisibilityState.PUBLIC:
            # Both sub-requests are independent once we have the summary — fire in parallel
            owned_result, recent_result = await asyncio.gather(
                self._fetch_owned_games(
                    steamid=steamid, verbose=verbose, include_free_games=include_free_games
                ),
                self._fetch_recently_played_games(steamid=steamid, verbose=verbose),
            )
            if owned_result["success"]:
                data_packed["owned_games"] = owned_result["data"]
            if recent_result["success"]:
                data_packed["recently_played_games"] = recent_result["data"]

        if selected_labels:
            data_packed = {
                label: data_packed[label]
                for label in self._filter_valid_labels(selected_labels=selected_labels)
            }

        return SuccessResult(success=True, data=data_packed)

    async def _fetch_summary(self, steamid: str, verbose: bool) -> SourceResult:
        params = {"key": self._api_key, "steamids": steamid}
        response = await self._make_request(params=params)

        if response.status_code == 403:
            return self._build_error_result(
                f"Permission denied, please assign correct API Key. (status code {response.status_code}).",
                verbose=verbose,
            )
        elif not response.ok:
            return self._build_error_result(
                f"API Request failed with status {response.status_code}.", verbose=verbose
            )

        data = response.json()
        players = data.get("response", {}).get("players", [])
        if not players:
            return self._build_error_result(f"steamid {steamid} not found.", verbose=verbose)

        return SuccessResult(
            success=True, data=self._transform_data(data=players[0], data_type="summary")
        )

    async def _fetch_owned_games(
        self, steamid: str, verbose: bool, include_free_games: bool
    ) -> SourceResult:
        params = {
            "steamid": steamid,
            "key": self._api_key,
            "include_played_free_games": 1 if include_free_games else 0,
            "include_appinfo": 1,
        }
        response = await self._make_request(url=self._owned_games_url, params=params)
        if response.status_code == 200:
            data = response.json().get("response", {})
            return SuccessResult(
                success=True, data=self._transform_data(data=data, data_type="games_owned")
            )
        return self._build_error_result(
            f"Failed to fetch owned games for steamid {steamid}.", verbose=verbose
        )

    async def _fetch_recently_played_games(self, steamid: str, verbose: bool) -> SourceResult:
        params = {"steamid": steamid, "key": self._api_key}
        response = await self._make_request(url=self._recently_played_url, params=params)
        if response.status_code == 200:
            data = response.json().get("response", {})
            return SuccessResult(
                success=True, data=self._transform_data(data=data, data_type="recent_games")
            )
        return self._build_error_result(
            f"Failed to fetch recently played games for steamid {steamid}.", verbose=verbose
        )

    def _transform_data(
        self,
        data: dict[str, Any],
        data_type: Literal["summary", "games_owned", "recent_games"] = "summary",
    ) -> dict[str, Any]:
        return transform_steamuser(data, data_type=data_type)
