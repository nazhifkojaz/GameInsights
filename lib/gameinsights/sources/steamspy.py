from typing import Any

import requests

from gameinsights.sources._parsers import transform_steamspy
from gameinsights.sources._schemas import _STEAMSPY_LABELS
from gameinsights.sources.base import BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited


class SteamSpy(BaseSource):
    _valid_labels: tuple[str, ...] = _STEAMSPY_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMSPY_LABELS)
    _base_url = "https://steamspy.com/api.php"

    def __init__(self, session: requests.Session | None = None) -> None:
        """Initialize the SteamSpy source.

        Args:
            session: Optional requests.Session for connection pooling.
        """
        super().__init__(session=session)

    @logged_rate_limited(calls=60, period=60)  # 60 requests per minute.
    def fetch(
        self, steam_appid: str, verbose: bool = True, selected_labels: list[str] | None = None
    ) -> SourceResult:
        """Fetch game data from SteamSpy based on appid.
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

        params = {"request": "appdetails", "appid": steam_appid}
        response = self._make_request(params=params)

        data = self._fetch_and_parse_json(response, verbose)
        if data is None:
            return self._build_error_result(
                f"Failed to connect to API. Status code: {response.status_code}", verbose=verbose
            )

        if not data.get("name", None):
            return self._build_error_result(
                f"Game with appid {steam_appid} is not found.", verbose=verbose
            )

        data_packed = self._transform_data(data=data)

        return SuccessResult(
            success=True, data=self._apply_label_filter(data_packed, selected_labels)
        )

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        return transform_steamspy(data)
