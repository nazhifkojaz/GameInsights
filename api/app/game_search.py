from typing import Any

import requests

from gameinsights.utils.gamesearch import GameSearch as _BaseGameSearch

_STORE_APPLIST_URL = "https://api.steampowered.com/IStoreService/GetAppList/v1/"


class GameSearch(_BaseGameSearch):
    """GameSearch subclass using the current IStoreService/GetAppList endpoint.

    The original ISteamApps/GetAppList/v2/ endpoint was removed by Steam.
    IStoreService/GetAppList/v1/ requires an API key and uses pagination.
    """

    def __init__(self, steam_api_key: str) -> None:
        super().__init__()
        self._api_key = steam_api_key

    def get_game_list(self) -> list[dict[str, Any]]:
        apps: list[dict[str, Any]] = []
        last_appid = 0

        while True:
            response = requests.get(
                _STORE_APPLIST_URL,
                params={
                    "key": self._api_key,
                    "max_results": 50000,
                    "last_appid": last_appid,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()["response"]

            batch = data.get("apps", [])
            if not batch:
                break

            apps.extend(
                {"appid": app["appid"], "name": app["name"]} for app in batch
            )

            last_appid = data.get("last_appid", 0)
            if not data.get("have_more_results", False):
                break

        return apps
