from typing import Any

import requests

_STORE_APPLIST_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"


class GameSearch:
    """Game search using the IStoreService/GetAppList endpoint.

    The original ISteamApps/GetAppList/v2/ endpoint was removed by Steam.
    IStoreService/GetAppList/v1/ requires an API key and uses pagination.
    """

    def __init__(self, steam_api_key: str) -> None:
        self._api_key = steam_api_key
        self._cached_games: list[dict[str, Any]] = []
        self._cached_names: list[str] = []

    def get_game_list(self) -> list[dict[str, Any]]:
        apps: list[dict[str, Any]] = []
        last_appid = 0

        while True:
            response = requests.get(
                _STORE_APPLIST_URL,
                params={
                    "key": self._api_key,
                    "max_results": "50000",
                    "last_appid": str(last_appid),
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()["response"]

            batch = data.get("apps", [])
            if not batch:
                break

            apps.extend({"appid": app["appid"], "name": app["name"]} for app in batch)

            last_appid = data.get("last_appid", 0)
            if not data.get("have_more_results", False):
                break

        return apps

    def _refresh(self, force: bool = False) -> None:
        if force or not self._cached_games:
            self._cached_games = self.get_game_list()
            self._cached_names = [game["name"].lower() for game in self._cached_games]

    def search_by_name(self, game_name: str, top_n: int = 5) -> list[dict[str, Any]]:
        self._refresh()
        query = game_name.lower()
        results = [
            {
                "appid": str(game["appid"]),
                "name": game["name"],
                "search_score": round(
                    len([c for c in query if c in game["name"].lower()])
                    / max(len(query), 1)
                    * 100,
                    2,
                ),
            }
            for game in self._cached_games
            if query in game["name"].lower()
        ][:top_n]
        return results
