from typing import Any

import requests

from gameinsights.sources.base import BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited

_STEAMACHIEVEMENT_LABELS = (
    "achievements_count",
    "achievements_percentage_average",
    "achievements_list",
)


class SteamAchievements(BaseSource):
    _valid_labels: tuple[str, ...] = _STEAMACHIEVEMENT_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMACHIEVEMENT_LABELS)
    _base_url = (
        "http://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002"
    )
    _schema_url = "http://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2"

    def __init__(
        self, api_key: str | None = None, session: requests.Session | None = None
    ) -> None:
        """Initialize SteamAchievement source.

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
        steam_appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        """Fetch game data from SteamWeb API based on appid.
        Args:
            steam_appid (str): The steam appid of the game to fetch data for.
            verbose (bool): If True, will log the fetching process.
            selected_labels (list[str] | None): A list of labels to filter the data. If None, all labels will be used.

        Returns:
            SourceResult: A dictionary containing the status, data, or any error message if applicable.

        Behavior:
            - If successful, will return a SuccessResult with the data based on the selected_labels or _valid_labels.
            - If unsuccessful, will return an error message indicating the failure reason.
        """

        steam_appid = self._prepare_identifier(steam_appid, verbose)

        if not self._api_key:
            self.logger.log(
                "API Key is not assigned. Some details will not be included.",
                level="warning",
                verbose=verbose,
            )

        # make request for achievement percentage data
        params = {
            "gameid": steam_appid,
        }
        response = self._make_request(params=params)

        if response.status_code != 200:
            return self._build_error_result(
                f"Failed to connect to API. Status code: {response.status_code}.",
                verbose=verbose,
            )

        percentage_data = response.json()

        # make request for scheme if api_key is provided
        if self._api_key:
            schema_data = self._fetch_schema_data(steam_appid=steam_appid, verbose=verbose)
            if not schema_data["success"]:
                return self._build_error_result(schema_data["error"], verbose=False)
            data_packed = self._transform_data(
                data=percentage_data, schema_data=schema_data["data"]
            )
        else:
            data_packed = self._transform_data(data=percentage_data)

        return SuccessResult(
            success=True, data=self._apply_label_filter(data_packed, selected_labels)
        )

    def _fetch_schema_data(self, steam_appid: str, verbose: bool = True) -> SourceResult:
        # prepare the params
        params = {
            "appid": steam_appid,
            "key": self._api_key,
        }
        response = self._make_request(url=self._schema_url, params=params)
        if response.status_code == 403:
            return self._build_error_result(
                f"Access denied, verify your API Key. Status code: {response.status_code}.",
                verbose=verbose,
            )
        elif not response.ok:
            return self._build_error_result(
                f"Failed to connect to API. Status code: {response.status_code}.",
                verbose=verbose,
            )

        data = response.json()

        return SuccessResult(success=True, data=data)

    def _transform_data(
        self, data: dict[str, Any], schema_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        percentage_data = data.get("achievementpercentages", {}).get("achievements", [])
        if not percentage_data:  # returns None if the data turns out to be empty
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

        # merge achievements
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
        """Process achievements data. (assuming achievements is not empty)
        Args:
            achievements (list of dictionaries): list of achievements.
        Returns:
            - list of achievements.
            - achievements count.
            - average achievements percentage.
        """
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
        """Merge base achievements (name, percentage) and schema data (name, displayName, etc).

        Args:
            base_achievements: List of achievements from GetGlobalAchievementPercentagesForApp.
            schema_data: List of schema entries from GetSchemaForGame.

        Returns:
            merged list where each base entry is merged with provided schema info.
        """
        # schema lookup by name
        schema_lookup = {}
        for entry in schema_data:
            name = entry.get("name")
            display_name = entry.get("displayName")

            # skip bad structure (if any)
            if not name or not display_name:
                continue

            schema_lookup[name] = {
                "display_name": display_name,
                "hidden": entry.get("hidden"),
                "description": entry.get("description"),
            }

        # Merge with base achievements
        merged = []
        for acv in base_achievements:
            name = acv["name"]
            percent = acv["percent"]

            schema_info = schema_lookup.get(name, {})

            merged.append(
                {
                    "name": name,
                    "percent": percent,
                    "display_name": schema_info.get("display_name", None),
                    "hidden": schema_info.get("hidden", None),
                    "description": schema_info.get("description", None),
                }
            )

        return merged
