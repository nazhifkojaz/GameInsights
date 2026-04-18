from typing import Any

import requests

from gameinsights.sources._parsers import transform_steamstore
from gameinsights.sources._schemas import _STEAM_LABELS
from gameinsights.sources.base import BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited


class SteamStore(BaseSource):
    _valid_labels: tuple[str, ...] = _STEAM_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAM_LABELS)
    _base_url = "https://store.steampowered.com/api/appdetails"

    def __init__(
        self,
        region: str = "us",
        language: str = "english",
        api_key: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """Initialize the Steam with an optional API key.

        Args:
            region: Region for the game data. Default is "us".
            language: Language for the API request. Default is "english".
            api_key: Optional API key for Steam API.
            session: Optional requests.Session for connection pooling.
        """
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

    @property
    def api_key(self) -> str | None:
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        if self._api_key != value:
            self._api_key = value

    @logged_rate_limited(
        calls=60, period=60
    )  # no official rate limit, but 60 requests per minute is a good practice.
    def fetch(
        self, steam_appid: str, verbose: bool = True, selected_labels: list[str] | None = None
    ) -> SourceResult:
        """Fetch game data from steam store based on appid.
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

        params = {"appids": steam_appid, "cc": self.region, "l": self.language}
        response = self._make_request(params=params)

        data = self._fetch_and_parse_json(response)
        if data is None:
            return self._build_error_result(
                f"Failed to connect to API. Status code: {response.status_code}.",
                verbose=verbose,
            )

        if steam_appid not in data or not data[steam_appid]["success"]:
            return self._build_error_result(
                f"Failed to fetch data for appid {steam_appid}, or appid is not available in the specified region ({self.region}) or language ({self.language}).",
                verbose=verbose,
            )

        data_packed = self._transform_data(data[steam_appid]["data"])

        return SuccessResult(
            success=True, data=self._apply_label_filter(data_packed, selected_labels)
        )

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        return transform_steamstore(data)
