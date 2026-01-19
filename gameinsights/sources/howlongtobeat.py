# ---------------------------
# This code is based on the original code from HowLongToBeatAPI (https://github.com/ScrappyCocco/HowLongToBeat-PythonAPI/)
# But modified to fit this project, all credit goes to the original author
# ---------------------------

import json
import re
from typing import Any, cast

import requests
from bs4 import BeautifulSoup
from bs4.element import Tag
from fake_useragent import UserAgent

from gameinsights.sources.base import BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited

_HOWLONGTOBEAT_LABELS = (
    "game_id",
    "game_name",
    "game_type",
    "comp_main",
    "comp_plus",
    "comp_100",
    "comp_all",
    "comp_main_count",
    "comp_plus_count",
    "comp_100_count",
    "comp_all_count",
    "invested_co",
    "invested_mp",
    "invested_co_count",
    "invested_mp_count",
    "count_comp",
    "count_speed_run",
    "count_backlog",
    "count_review",
    "review_score",
    "count_playing",
    "count_retired",
)


class SearchInformation:
    """Class to hold search information extracted from the HLTB script."""

    def __init__(self, title_headers: dict[str, Any]) -> None:
        self.api_key: str | None = None
        self.search_url: str | None = None
        self._get_search_informations(title_headers=title_headers)
        if self.search_url:
            self.search_url = self.search_url.lstrip("/")

    def _extract_api_from_script(self, script_content: str) -> str | None:
        """Extract the API key from the script content.
        Args:
            script_content (str): The content of the script to search for the API key.
        Returns:
            str | None: The extracted API key if found, otherwise None.
        """

        api_key_pattern = r'users\s*:\s*{\s*id\s*:\s*"([^"]+)"'
        matches = re.findall(api_key_pattern, script_content)

        if matches:
            key = "".join(matches)
            return key

        concat_api_key_pattern = r'\/api\/\w+\/"(?:\.concat\("[^"]*"\))*'
        matches = re.findall(concat_api_key_pattern, script_content)

        if matches:
            matches = str(matches).split(".concat")
            matches = [re.sub(r'["\(\)\[\]\']', "", match) for match in matches[1:]]
            key = "".join(matches)
            return key

        return None

    def _extract_search_url_script(self, script_content: str) -> str | None:
        """Extract the search URL from the script content.
        Args:
            script_content (str): The content of the script to search for the search URL.
        Returns:
            str | None: The extracted search URL if found, otherwise None.
        """
        pattern = re.compile(
            r'fetch\(\s*["\'](\/api\/[^"\']*)["\']'  # Matches the endpoint
            r'((?:\s*\.concat\(\s*["\']([^"\']*)["\']\s*\))+)'  # Captures concatenated strings
            r"\s*,",  # Matches up to the comma
            re.DOTALL,
        )
        matches = pattern.finditer(script_content)
        for match in matches:
            endpoint = match.group(1)
            concat_calls = match.group(2)
            # Extract all concatenated strings
            concat_strings = re.findall(r'\.concat\(\s*["\']([^"\']*)["\']\s*\)', concat_calls)
            concatenated_str = "".join(concat_strings)
            # Check if the concatenated string matches the known string
            if concatenated_str == self.api_key:
                return endpoint
        # Unable to find :(
        return None

    def _get_search_informations(self, title_headers: dict[str, Any]) -> None:
        response = requests.get(HowLongToBeat.BASE_URL, headers=title_headers, timeout=60)

        if response.status_code == 200 and response.text:
            soup = BeautifulSoup(response.text, "html.parser")
            scripts = soup.find_all("script", src=True)

            matching_scripts: list[str] = []
            non_matching_scripts: list[str] = []

            for script in scripts:
                if not isinstance(script, Tag):
                    continue

                src_attr = script.get("src")
                if isinstance(src_attr, str):
                    if "_app-" in src_attr:
                        matching_scripts.append(src_attr)
                    else:
                        non_matching_scripts.append(src_attr)

            # look for scripts that provide the api key
            self._process_script(matching_scripts, title_headers=title_headers)

            # if we still don't have the api key, try to get it from the other scripts
            if self.api_key is None:
                self._process_script(non_matching_scripts, title_headers=title_headers)

    def _process_script(self, script_urls: list[str], title_headers: dict[str, Any]) -> None:
        """Process the script content to extract API key and search URL.
        Args:
            script_urls (list[str]): List of script URLs to process.
        """
        for script_url in script_urls:
            script_url = HowLongToBeat.BASE_URL + script_url
            script_response = requests.get(script_url, headers=title_headers, timeout=60)
            if script_response.status_code == 200 and script_response.text:
                self.api_key = self._extract_api_from_script(script_response.text)
                self.search_url = self._extract_search_url_script(script_response.text)
                if self.api_key:
                    break


class HowLongToBeat(BaseSource):
    """HowLongToBeat source for fetching game completion times."""

    BASE_URL = "https://howlongtobeat.com/"
    REFERER_HEADER = BASE_URL
    _valid_labels: tuple[str, ...] = _HOWLONGTOBEAT_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_HOWLONGTOBEAT_LABELS)

    def __init__(self) -> None:
        """Initialize the HowLongToBeat source."""
        super().__init__()
        title_headers = HowLongToBeat._get_title_request_headers()
        self._search_info_data: SearchInformation = SearchInformation(title_headers=title_headers)

    @logged_rate_limited(calls=60, period=60)  # web scrape -> 60 requests per minute to be polite
    def fetch(
        self, game_name: str, verbose: bool = True, selected_labels: list[str] | None = None
    ) -> SourceResult:
        """Fetch game completion data from HowLongToBeat based on game name.
        Args:
            game_name (str): The name of the game to search for.
            verbose (bool): If True, will log the fetching process.
            selected_labels (list[str] | None): A list of labels to filter the data.

        Returns:
            SourceResult: A dictionary containing the status, completion time data, and any error message if applicable.

        Behavior:
            - If successful, will return a SuccessResult with the data based on the selected_labels or _valid_labels.
            - If unsuccessful, will return an error message indicating the failure reason.
        """

        self.logger.log(
            f"Fetching data for game '{game_name}'",
            level="info",
            verbose=verbose,
        )

        # Make the request
        search_response = self._fetch_search_results(game_name)
        if not search_response or not search_response.text:
            return self._build_error_result("Failed to fetch data.", verbose=verbose)

        try:
            search_result_raw = json.loads(search_response.text)
        except json.JSONDecodeError:
            return self._build_error_result("Failed to parse search response.", verbose=verbose)

        if not isinstance(search_result_raw, dict):
            return self._build_error_result("Unexpected search response format.", verbose=verbose)

        search_result = cast(dict[str, Any], search_result_raw)

        # if the search result count is 0, then the game is not found
        if search_result["count"] == 0:
            return self._build_error_result("Game is not found.", verbose=verbose)

        # if not, then get the first data in the search result
        data_packed = self._transform_data(data=search_result["data"][0])

        if selected_labels:
            data_packed = {
                label: data_packed[label] for label in self._filter_valid_labels(selected_labels)
            }

        return SuccessResult(success=True, data=data_packed)

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        # repack / process the data if needed
        return {label: data.get(label, None) for label in self._valid_labels}

    def _fetch_search_results(self, game_name: str, page: int = 1) -> requests.Response:
        """Send a web request to HowLongToBeat to fetch game data.
        Args:
            game_name (str): The name of the game to search for.
            page (int): The page number to fetch results from. (default is 1).

        Returns:
            str: HTML response text if the request is successful.
        """
        if not hasattr(self, "_search_info_data") or self._search_info_data is None:
            title_headers = HowLongToBeat._get_title_request_headers()
            self._search_info_data = SearchInformation(title_headers=title_headers)

        search_headers = HowLongToBeat._get_search_request_headers()

        # if the api key is not found, then we cannot proceed
        if not self._search_info_data.api_key:
            return self._create_synthetic_response(
                url=HowLongToBeat.BASE_URL,
                reason="Missing HowLongToBeat API key.",
            )

        search_url = HowLongToBeat.BASE_URL + "api/s/"
        if self._search_info_data.search_url:
            search_url = HowLongToBeat.BASE_URL + self._search_info_data.search_url

        search_url_with_key = search_url + self._search_info_data.api_key
        payload = HowLongToBeat._generate_data_payload(game_name, page, None)
        response_with_key = requests.post(
            search_url_with_key, headers=search_headers, data=payload, timeout=60
        )

        if response_with_key.status_code == 200:
            return response_with_key

        # if the request failed, try to use the search URL with API key in the payload
        payload = HowLongToBeat._generate_data_payload(game_name, page, self._search_info_data)
        response_with_payload = requests.post(
            search_url, headers=search_headers, data=payload, timeout=60
        )

        if response_with_payload.status_code == 200:
            return response_with_payload

        return self._create_synthetic_response(
            url=search_url,
            reason=(
                "Failed to fetch HowLongToBeat data: "
                f"status {response_with_key.status_code} with key, "
                f"status {response_with_payload.status_code} with payload."
            ),
        )

    @staticmethod
    def _get_title_request_headers() -> dict[str, Any]:
        """Get headers for the title request."""
        ua = UserAgent()
        headers = {"User-Agent": ua.random, "referer": HowLongToBeat.REFERER_HEADER}
        return headers

    @staticmethod
    def _get_search_request_headers() -> dict[str, Any]:
        ua = UserAgent()
        headers = {
            "content-type": "application/json",
            "accept": "*/*",
            "User-Agent": ua.random.strip(),
            "Referer": HowLongToBeat.REFERER_HEADER,
        }

        return headers

    @staticmethod
    def _generate_data_payload(
        game_name: str, page: int, search_info: SearchInformation | None = None
    ) -> str:
        """Generate data payload
        Args:
            game_name (str): The game name to fetch data for.
            page: The page to search
            search_info (SearchInformation): Search information containing API key and search URL of the HLTB.

        Returns:
            str: JSON string of the payload to be sent in the request.

        """
        payload: dict[str, Any] = {
            "searchType": "games",
            "searchTerms": game_name.split(),
            "searchPage": page,
            "size": 20,
            "searchOptions": {
                "games": {
                    "userId": 0,
                    "platform": "",
                    "sortCategory": "popular",
                    "rangeCategory": "main",
                    "rangeTime": {"min": 0, "max": 0},
                    "gameplay": {"perspective": "", "flow": "", "genre": "", "difficulty": ""},
                    "rangeYear": {"max": "", "min": ""},
                    "modifier": "",
                },
                "users": {"sortCategory": "postcount"},
                "lists": {"sortCategory": "follows"},
                "filter": "",
                "sort": 0,
                "randomizer": 0,
            },
            "useCache": True,
        }

        # If api_key is passed add it to the dict
        if search_info and search_info.api_key:
            search_options = cast(dict[str, Any], payload["searchOptions"])
            users_options = cast(dict[str, Any], search_options["users"])
            users_options["id"] = search_info.api_key

        return json.dumps(payload)
