from typing import Any

from gameinsights.sources.base import BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited

_GAMALYTICS_LABELS = (
    "steam_appid",
    "name",
    "price",
    "reviews",
    "reviews_steam",
    "followers",
    "average_playtime_h",
    "review_score",
    "tags",
    "genres",
    "features",
    "languages",
    "developers",
    "publishers",
    "release_date",
    "first_release_date",
    "unreleased",
    "early_access",
    # "countryData",
    "copies_sold",
    "estimated_revenue",
    # "total_revenue",
    "players",
    "owners",
)


class Gamalytic(BaseSource):
    """Gamalytic source for fetching game data from Gamalytic API."""

    _valid_labels: tuple[str, ...] = _GAMALYTICS_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_GAMALYTICS_LABELS)
    _base_url = "https://api.gamalytic.com/game"

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the Gamalytic with an optional API key.
        Args:
            api_key (str): Optional API key for Gamalytic API.
        """
        super().__init__()
        self._api_key = api_key

    @property
    def api_key(self) -> str | None:
        return self._api_key

    @api_key.setter
    def api_key(self, value: str) -> None:
        if self._api_key != value:
            self._api_key = value

    @logged_rate_limited(calls=500, period=24 * 60 * 60)  # 500 requests per day
    def fetch(
        self, steam_appid: str, verbose: bool = True, selected_labels: list[str] | None = None
    ) -> SourceResult:
        """Fetch game data from Gamalytic based on steam_appid.
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

        # Make the request to Gamalytic API
        response = self._make_request(endpoint=steam_appid)

        if response.status_code == 404:
            return self._build_error_result(
                f"Game with appid {steam_appid} is not found.", verbose=verbose
            )

        data = self._fetch_and_parse_json(response, verbose)
        if data is None:
            return self._build_error_result(
                f"Failed to connect to API. Status code: {response.status_code}", verbose=verbose
            )

        # Parse JSON response if everything is fine and pack/process the data as labels we want
        data_packed = self._transform_data(data=data)

        return SuccessResult(
            success=True, data=self._apply_label_filter(data_packed, selected_labels)
        )

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        # repack / process the data if needed
        return {  # default values are None
            "steam_appid": data.get("steamId", None),
            "name": data.get("name", None),
            "price": data.get("price", None),
            "reviews": data.get("reviews", None),
            "reviews_steam": data.get("reviewsSteam", None),
            "followers": data.get("followers", None),
            "average_playtime_h": data.get("avgPlaytime", None),
            "review_score": data.get("reviewScore", None),
            "tags": data.get("tags", None),
            "genres": data.get("genres", None),
            "features": data.get("features", None),
            "languages": data.get("languages", None),
            "developers": data.get("developers", None),
            "publishers": data.get("publishers", None),
            "release_date": data.get("releaseDate", None),
            "first_release_date": data.get("firstReleaseDate", None),
            "unreleased": data.get("unreleased", None),
            "early_access": data.get("earlyAccess", None),
            # "countryData": data.get("countryData", {}),
            "copies_sold": data.get("copiesSold", None),
            "estimated_revenue": data.get("revenue", None),
            # "total_revenue": data.get("totalRevenue", None),
            "players": data.get("players", None),
            "owners": data.get("owners", None),
        }
