from typing import Any, Literal

import requests

from gameinsights.sources._parsers import transform_steamuser
from gameinsights.sources._schemas import _STEAMUSER_LABELS, CommunityVisibilityState
from gameinsights.sources.base import BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited


class SteamUser(BaseSource):
    _valid_labels: tuple[str, ...] = _STEAMUSER_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMUSER_LABELS)
    _base_url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002"
    _owned_games_url = "https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/"
    _recently_played_url = (
        "https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v0001/"
    )

    def __init__(
        self, api_key: str | None = None, session: requests.Session | None = None
    ) -> None:
        """Initialize SteamUser source.

        Args:
            api_key: Optional API key for SteamWeb API.
            session: Optional requests.Session for connection pooling.
        """
        super().__init__(session=session)
        self._api_key = api_key

    @property
    def api_key(self) -> str | None:
        """Get the api_key for the SteamWeb API."""
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        """Set the api_key for the SteamWeb API.
        Args:
            value (str): API key fo SteamWeb API.
        """
        if self._api_key != value:
            self._api_key = value

    @logged_rate_limited(calls=100000, period=24 * 60 * 60)
    def fetch(
        self,
        steamid: str,
        include_free_games: bool = True,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        """Fetch game data from SteamWeb API based on appid.
        Args:
            steamid (str): 64bit SteamID of the user.
            include_free_games (bool): If True, will include free games when fetching users' owned games list
            verbose (bool): If True, will log the fetching process.
            selected_labels (list[str] | None): A list of labels to filter the data. If None, all labels will be used.

        Returns:
            SourceResult: A dictionary containing the status, data, or any error message if applicable.

        Behavior:
            - If successful, will return a SuccessResult with the data based on the selected_labels or _valid_labels.
            - If unsuccessful, will return an error message indicating the failure reason.
        """

        self.logger.log(
            f"Fetching user data for steamid {steamid}.",
            level="info",
            verbose=verbose,
        )

        if not self._api_key:
            return self._build_error_result(
                "API Key is not assigned. Unable to fetch data.",
                verbose=verbose,
            )

        # ensure steamid is string
        steamid = str(steamid)

        # fetch the summary data first
        summary_result = self._fetch_summary(steamid=steamid, verbose=verbose)

        if not summary_result["success"]:
            return self._build_error_result(
                summary_result["error"], verbose=False
            )  # because we already log the error in the fetching function

        # provide default result with summary data
        data_packed = {
            **summary_result["data"],
            "owned_games": {},
            "recently_played_games": {},
        }

        if data_packed["community_visibility_state"] == CommunityVisibilityState.PUBLIC:
            owned_games_result = self._fetch_owned_games(
                steamid=steamid, verbose=verbose, include_free_games=include_free_games
            )
            if owned_games_result["success"]:
                data_packed["owned_games"] = owned_games_result["data"]
            recently_played_games_result = self._fetch_recently_played_games(
                steamid=steamid, verbose=verbose
            )
            if recently_played_games_result["success"]:
                data_packed["recently_played_games"] = recently_played_games_result["data"]

        if selected_labels:
            data_packed = {
                label: data_packed[label]
                for label in self._filter_valid_labels(selected_labels=selected_labels)
            }

        return SuccessResult(success=True, data=data_packed)

    def _fetch_summary(self, steamid: str, verbose: bool) -> SourceResult:
        # prepare the params and make request
        params = {
            "key": self._api_key,
            "steamids": steamid,
        }
        response = self._make_request(params=params)

        if response.status_code == 403:
            return self._build_error_result(
                f"Permission denied, please assign correct API Key. (status code {response.status_code}).",
                verbose=verbose,
            )
        elif not response.ok:
            return self._build_error_result(
                f"API Request failed with status {response.status_code}.",
                verbose=verbose,
            )

        data = response.json()
        players = data.get("response", {}).get("players", [])

        if not players:
            return self._build_error_result(f"steamid {steamid} not found.", verbose=verbose)

        # transform and resume the first data (because we only fetching one id at a time)
        return SuccessResult(
            success=True, data=self._transform_data(data=players[0], data_type="summary")
        )

    def _fetch_owned_games(
        self, steamid: str, verbose: bool, include_free_games: bool
    ) -> SourceResult:
        # prepare params
        params = {
            "steamid": steamid,
            "key": self._api_key,
            "include_played_free_games": 1 if include_free_games else 0,
            "include_appinfo": 1,
        }
        response = self._make_request(url=self._owned_games_url, params=params)

        if response.status_code == 200:
            data = response.json().get("response", {})
            return SuccessResult(
                success=True, data=self._transform_data(data=data, data_type="games_owned")
            )
        return self._build_error_result(
            f"Failed to fetch owned games for steamid {steamid}.", verbose=verbose
        )

    def _fetch_recently_played_games(self, steamid: str, verbose: bool) -> SourceResult:
        # prepare params
        params = {
            "steamid": steamid,
            "key": self.api_key,
        }

        response = self._make_request(url=self._recently_played_url, params=params)

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
