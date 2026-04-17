# ---------------------------
# HowLongToBeat Source
# Fetches game completion time data from howlongtobeat.com
#
# NOTE: This source scrapes data from HowLongToBeat (howlongtobeat.com).
# This implementation is for educational/personal use only.
# Please respect their service and consider using official APIs if available.
#
# API Strategy:
# 1. GET /api/find/init - Obtain session token and auth params
# 2. POST /api/find with x-auth-token + x-hp-key/x-hp-val headers - Search for games
# 3. GET /game/{id} and parse __NEXT_DATA__ - Get full data
#
# Data Attribution: Completion times are sourced from howlongtobeat.com
# ---------------------------

import json
from typing import Any, cast

import requests

from gameinsights.sources._parsers import (
    extract_hltb_game_data,
    generate_search_payload,
    transform_howlongtobeat,
)
from gameinsights.sources._schemas import _HOWLONGTOBEAT_LABELS, _SearchAuth
from gameinsights.sources.base import SYNTHETIC_ERROR_CODE, BaseSource, SourceResult, SuccessResult
from gameinsights.utils.ratelimit import logged_rate_limited


class HowLongToBeat(BaseSource):
    """HowLongToBeat source for fetching game completion times.

    The source uses a three-step approach:
    1. Fetch session token and auth params from /api/find/init
    2. Search for games using /api/find with auth headers
    3. Fetch full game data from /game/{id} and parse __NEXT_DATA__
    """

    BASE_URL = "https://www.howlongtobeat.com/"
    REFERER_HEADER = BASE_URL
    _valid_labels: tuple[str, ...] = _HOWLONGTOBEAT_LABELS
    _valid_labels_set: frozenset[str] = frozenset(_HOWLONGTOBEAT_LABELS)

    def __init__(self, session: requests.Session | None = None) -> None:
        """Initialize HowLongToBeat source.

        Args:
            session: Optional requests.Session for connection pooling.
        """
        super().__init__(session=session)

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

        # Step 1: Get session auth (token + dynamic params)
        auth = self._get_search_auth()
        if not auth:
            return self._build_error_result("Failed to obtain search token.", verbose=verbose)

        # Step 2: Search for the game
        search_response = self._fetch_search_results(game_name, auth)
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
        search_data = search_result.get("data")
        if not isinstance(search_data, list) or len(search_data) == 0:
            return self._build_error_result("No search data returned.", verbose=verbose)

        first_result = search_data[0]
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

    def _get_search_auth(self) -> _SearchAuth | None:
        """Fetch auth data from the init endpoint.

        Returns:
            _SearchAuth with token and auth params, or None if fetching failed.
        """
        ua = self._ua.random
        headers = {
            "Accept": "*/*",
            "Referer": self.REFERER_HEADER,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": ua,
        }

        response = self._make_request(self.BASE_URL + "api/find/init", headers=headers)

        if response and response.status_code == 200:
            try:
                data: dict[str, Any] = response.json()
                token = data.get("token")
                if token is None:
                    self.logger.log(
                        "HLTB init response missing token",
                        level="error",
                        verbose=True,
                    )
                    return None

                hp_key = data.get("hpKey")
                hp_val = data.get("hpVal")
                if hp_key is None or hp_val is None:
                    self.logger.log(
                        "HLTB init response missing hpKey or hpVal",
                        level="error",
                        verbose=True,
                    )
                    return None

                # Collect any additional string fields for forward compatibility
                known_keys = {"token", "hpKey", "hpVal"}
                extras = {
                    k: v for k, v in data.items() if k not in known_keys and isinstance(v, str)
                }

                return _SearchAuth(
                    token=cast(str, token),
                    hp_key=cast(str, hp_key),
                    hp_val=cast(str, hp_val),
                    user_agent=ua,
                    extras=extras,
                )
            except (json.JSONDecodeError, KeyError) as e:
                self.logger.log(
                    f"HLTB auth parsing failed: {e}",
                    level="error",
                    verbose=True,
                )
        else:
            self.logger.log(
                f"HLTB auth request failed with status {response.status_code if response else 'no response'}",
                level="error",
                verbose=True,
            )

        return None

    def _fetch_search_results(self, game_name: str, auth: _SearchAuth) -> requests.Response | None:
        """Send a search request to HowLongToBeat.

        Args:
            game_name: The name of the game to search for.
            auth: The auth data from init endpoint.

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
            "User-Agent": auth.user_agent,
            "x-auth-token": auth.token,
            "x-hp-key": auth.hp_key,
            "x-hp-val": auth.hp_val,
        }
        # Forward any unknown future fields as headers
        headers.update({f"x-{k.lower()}": v for k, v in auth.extras.items()})

        payload = self._generate_search_payload(game_name)
        # Inject hp fields and any extras into the body
        payload[auth.hp_key] = auth.hp_val
        payload.update(auth.extras)

        response = self._make_request(
            url=self.BASE_URL + "api/find",
            method="POST",
            headers=headers,
            json=payload,
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

        if response.status_code != 200:
            return None

        return extract_hltb_game_data(
            response.text,
            game_id,
            log_fn=lambda msg: self.logger.log(msg, level="debug", verbose=True),
        )

    @staticmethod
    def _generate_search_payload(game_name: str) -> dict[str, Any]:
        return generate_search_payload(game_name)

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        return transform_howlongtobeat(data)
