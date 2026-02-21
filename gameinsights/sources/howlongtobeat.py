# ---------------------------
# HowLongToBeat Source
# Fetches game completion time data from howlongtobeat.com
#
# NOTE: This source scrapes data from HowLongToBeat (howlongtobeat.com).
# This implementation is for educational/personal use only.
# Please respect their service and consider using official APIs if available.
#
# API Strategy:
# 1. GET /api/search/init - Obtain session token
# 2. POST /api/search with x-auth-token header - Search for games
# 3. GET /game/{id} and parse __NEXT_DATA__ - Get full data
#
# Data Attribution: Completion times are sourced from howlongtobeat.com
# ---------------------------

import json
import re
from typing import Any, cast

import requests

from gameinsights.sources.base import SYNTHETIC_ERROR_CODE, BaseSource, SourceResult, SuccessResult
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


class HowLongToBeat(BaseSource):
    """HowLongToBeat source for fetching game completion times.

    The source uses a three-step approach:
    1. Fetch a session token from /api/search/init
    2. Search for games using /api/search with x-auth-token header
    3. Fetch full game data from /game/{id} and parse __NEXT_DATA__
    """

    BASE_URL = "https://www.howlongtobeat.com/"
    REFERER_HEADER = BASE_URL
    _valid_labels: tuple[str, ...] = _HOWLONGTOBEAT_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_HOWLONGTOBEAT_LABELS)

    @logged_rate_limited(calls=60, period=60)  # web scrape -> 60 requests per minute to be polite
    def fetch(
        self,
        game_name: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SourceResult:
        """Fetch game completion data from HowLongToBeat based on game name.

        Args:
            game_name: The name of the game to search for.
            verbose: If True, will log the fetching process.
            selected_labels: A list of labels to filter the data.

        Returns:
            SourceResult: A dictionary containing the status, completion time data,
                and any error message if applicable.
        """
        self.logger.log(
            f"Fetching data for game '{game_name}'",
            level="info",
            verbose=verbose,
        )

        # Step 1: Get session token
        token = self._get_search_token()
        if not token:
            return self._build_error_result("Failed to obtain search token.", verbose=verbose)

        # Step 2: Search for the game
        search_response = self._fetch_search_results(game_name, token)
        if not search_response:
            return self._build_error_result("Failed to fetch data.", verbose=verbose)

        try:
            search_result = cast(dict[str, Any], json.loads(search_response.text))
        except json.JSONDecodeError:
            return self._build_error_result("Failed to parse search response.", verbose=verbose)

        if not isinstance(search_result, dict):
            return self._build_error_result("Unexpected search response format.", verbose=verbose)

        if search_result.get("count") == 0:
            return self._build_error_result("Game is not found.", verbose=verbose)

        # Step 3: Get the first search result and fetch full data
        first_result = search_result["data"][0]
        game_id = first_result.get("game_id")

        if not game_id:
            return self._build_error_result("No game ID in search result.", verbose=verbose)

        # Step 4: Fetch full game data from the game page
        full_data = self._fetch_game_page(game_id)
        if not full_data:
            # Fall back to search result data if page fetch fails
            full_data = first_result

        # Transform and filter data
        data_packed = self._transform_data(data=full_data)

        if selected_labels:
            data_packed = {
                label: data_packed[label]
                for label in self._filter_valid_labels(selected_labels)
                if label in data_packed
            }

        return SuccessResult(success=True, data=data_packed)

    def _get_search_token(self) -> str | None:
        """Fetch a search token from the init endpoint.

        Returns:
            The session token string, or None if fetching failed.
        """
        headers = {
            "Accept": "*/*",
            "Referer": self.REFERER_HEADER,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
        }

        response = self._make_request(self.BASE_URL + "api/finder/init", headers=headers)

        if response and response.status_code == 200:
            try:
                data: dict[str, Any] = response.json()
                token = data.get("token")
                return cast(str, token) if token is not None else None
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.log(
                    f"HLTB token parsing failed: {e}",
                    level="error",
                    verbose=True,
                )
        else:
            self.logger.log(
                f"HLTB token request failed with status {response.status_code if response else 'no response'}",
                level="error",
                verbose=True,
            )

        return None

    def _fetch_search_results(self, game_name: str, token: str) -> requests.Response | None:
        """Send a search request to HowLongToBeat.

        Args:
            game_name: The name of the game to search for.
            token: The session token from init endpoint.

        Returns:
            The response object if successful, None otherwise.
        """
        headers = {
            "Content-Type": "application/json",
            "Accept": "*/*",
            "Referer": self.REFERER_HEADER,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "Origin": self.BASE_URL.rstrip("/"),
            "x-auth-token": token,
        }

        response = self._make_request(
            url=self.BASE_URL + "api/finder",
            method="POST",
            headers=headers,
            json=self._generate_search_payload(game_name),
        )

        # Return None on synthetic errors (connection/timeout failures)
        if response.status_code == SYNTHETIC_ERROR_CODE:
            return None
        return response

    def _fetch_game_page(self, game_id: int) -> dict[str, Any] | None:
        """Fetch full game data from the game page.

        Args:
            game_id: The HowLongToBeat game ID.

        Returns:
            The game data dict, or None if fetching failed.
        """
        headers = {
            "Referer": self.REFERER_HEADER,
        }

        response = self._make_request(url=f"{self.BASE_URL}game/{game_id}", headers=headers)

        # Return None on synthetic errors or non-200 responses
        if response.status_code != 200:
            return None

        # Extract __NEXT_DATA__ from the HTML
        match = re.search(
            r'<script id="__NEXT_DATA__".*?>(.*?)</script>',
            response.text,
            re.DOTALL,
        )
        if match:
            try:
                next_data = json.loads(match.group(1))
                # Navigate the nested structure safely
                game_data = (
                    next_data.get("props", {}).get("pageProps", {}).get("game", {}).get("data", {})
                )
                game_list = game_data.get("game")
                if isinstance(game_list, list) and len(game_list) > 0:
                    return cast(dict[str, Any], game_list[0])
            except (json.JSONDecodeError, KeyError, IndexError):
                pass

        return None

    @staticmethod
    def _generate_search_payload(game_name: str) -> dict[str, Any]:
        """Generate the search payload.

        Args:
            game_name: The game name to search for.

        Returns:
            The payload dict for the search request.
        """
        return {
            "searchType": "games",
            "searchTerms": game_name.split(),
            "searchPage": 1,
            "size": 1,
            "searchOptions": {
                "games": {
                    "userId": 0,
                    "platform": "",
                    "sortCategory": "popular",
                    "rangeCategory": "main",
                    "rangeTime": {"min": 0, "max": 0},
                    "gameplay": {
                        "perspective": "",
                        "flow": "",
                        "genre": "",
                        "difficulty": "",
                    },
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

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Transform raw data into the expected format.

        The HLTB API returns time values in seconds. We convert them to minutes
        for consistency with other sources. Also, we map the base time labels
        to their '_avg' counterparts which represent the average completion time
        as shown on the website.

        Args:
            data: The raw game data from HLTB.

        Returns:
            Dict with only the valid labels, with time values converted to minutes.
        """
        result: dict[str, Any] = {}
        for label in self._valid_labels:
            raw_value: Any = None

            # Map time labels to their '_avg' counterparts (average completion time)
            if label in ('comp_main', 'comp_plus', 'comp_100', 'comp_all'):
                avg_label = f"{label}_avg"
                raw_value = data.get(avg_label)
            elif label in ('invested_co', 'invested_mp'):
                avg_label = f"{label}_avg"
                raw_value = data.get(avg_label)
            else:
                raw_value = data.get(label, None)

            # Convert time fields from seconds to minutes
            if raw_value is not None and label.startswith(('comp_', 'invested_')):
                result[label] = cast(int, raw_value) // 60
            else:
                result[label] = raw_value
        return result
