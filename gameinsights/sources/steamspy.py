from typing import Any

from gameinsights.sources.base import BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited

_STEAMSPY_LABELS = (
    "steam_appid",
    "name",
    "developers",
    "publishers",
    "positive_reviews",
    "negative_reviews",
    "owners",
    "average_forever",
    "average_2weeks",
    "median_forever",
    "median_2weeks",
    "price",
    "initial_price",
    "discount",
    "ccu",
    "languages",
    "genres",
    "tags",
)


class SteamSpy(BaseSource):
    _valid_labels: tuple[str, ...] = _STEAMSPY_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_STEAMSPY_LABELS)
    _base_url = "https://steamspy.com/api.php"

    def __init__(self) -> None:
        """Initialize the SteamSpy with the base URL."""
        super().__init__()

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

        # Prepare the params and make request
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
        # repack / process the data if needed
        tags = data.get("tags", [])
        tags = [tag for tag, count in tags.items()] if isinstance(tags, dict) else []
        return {
            "steam_appid": data.get("appid", None),
            "name": data.get("name", None),
            "developers": data.get("developer", None),
            "publishers": data.get("publisher", None),
            "positive_reviews": data.get("positive", None),
            "negative_reviews": data.get("negative", None),
            "owners": data.get("owners", None),
            "average_forever": data.get("average_forever", None),
            "average_2weeks": data.get("average_2weeks", None),
            "median_forever": data.get("median_forever", None),
            "median_2weeks": data.get("median_2weeks", None),
            "price": data.get("price", None),
            "initial_price": data.get("initialprice", None),
            "discount": data.get("discount", None),
            "ccu": data.get("ccu", None),
            "languages": data.get("languages", None),
            "genres": data.get("genre", None),
            "tags": tags,
        }
