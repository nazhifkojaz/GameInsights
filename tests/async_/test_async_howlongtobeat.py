"""Tests for AsyncHowLongToBeat (three sequential async steps)."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from gameinsights.async_.base import _AsyncResponse
from gameinsights.async_.howlongtobeat import AsyncHowLongToBeat
from gameinsights.sources.howlongtobeat import _SearchAuth

_MOCK_AUTH = _SearchAuth(
    token="mock_token",
    hp_key="hpKey",
    hp_val="mock_val",
    user_agent="mock_ua",
    extras={},
)

_SEARCH_RESPONSE_BODY = json.dumps(
    {"count": 1, "data": [{"game_id": 1234, "game_name": "Mock Game: The Adventure"}]}
).encode()

_GAME_PAGE_DATA = {
    "game_id": 1234,
    "game_name": "Mock Game: The Adventure",
    "game_type": "game",
    "comp_main_avg": 12000,  # 200 mins after conversion
    "comp_plus_avg": 0,
    "comp_100_avg": 0,
    "comp_all_avg": 0,
}


class TestAsyncHowLongToBeat:
    async def test_async_hltb_fetch_success(self, stub_async_ratelimit) -> None:
        search_response = _AsyncResponse(status_code=200, _body=_SEARCH_RESPONSE_BODY)

        with (
            patch.object(
                AsyncHowLongToBeat, "_get_search_auth", AsyncMock(return_value=_MOCK_AUTH)
            ),
            patch.object(
                AsyncHowLongToBeat,
                "_fetch_search_results",
                AsyncMock(return_value=search_response),
            ),
            patch.object(
                AsyncHowLongToBeat, "_fetch_game_page", AsyncMock(return_value=_GAME_PAGE_DATA)
            ),
        ):
            src = AsyncHowLongToBeat()
            result = await src.fetch("Mock Game", verbose=False)

        assert result["success"] is True
        assert result["data"]["game_id"] == 1234
        assert result["data"]["game_name"] == "Mock Game: The Adventure"
        assert result["data"]["comp_main"] == 200  # 12000s → 200min

    async def test_async_hltb_fetch_auth_failure(self, stub_async_ratelimit) -> None:
        with patch.object(AsyncHowLongToBeat, "_get_search_auth", AsyncMock(return_value=None)):
            src = AsyncHowLongToBeat()
            result = await src.fetch("Mock Game", verbose=False)

        assert result["success"] is False
        assert result["error"] == "Failed to obtain search token."

    async def test_async_hltb_fetch_search_failure(self, stub_async_ratelimit) -> None:
        with (
            patch.object(
                AsyncHowLongToBeat, "_get_search_auth", AsyncMock(return_value=_MOCK_AUTH)
            ),
            patch.object(
                AsyncHowLongToBeat, "_fetch_search_results", AsyncMock(return_value=None)
            ),
        ):
            src = AsyncHowLongToBeat()
            result = await src.fetch("Mock Game", verbose=False)

        assert result["success"] is False
        assert result["error"] == "Failed to fetch data."

    async def test_async_hltb_fetch_game_not_found(self, stub_async_ratelimit) -> None:
        not_found_body = json.dumps({"count": 0, "data": []}).encode()
        search_response = _AsyncResponse(status_code=200, _body=not_found_body)

        with (
            patch.object(
                AsyncHowLongToBeat, "_get_search_auth", AsyncMock(return_value=_MOCK_AUTH)
            ),
            patch.object(
                AsyncHowLongToBeat,
                "_fetch_search_results",
                AsyncMock(return_value=search_response),
            ),
        ):
            src = AsyncHowLongToBeat()
            result = await src.fetch("Unknown Game", verbose=False)

        assert result["success"] is False
        assert result["error"] == "Game is not found."

    async def test_async_hltb_falls_back_to_search_data_on_page_failure(
        self, stub_async_ratelimit
    ) -> None:
        """When _fetch_game_page returns None, fetch() falls back to search result data."""
        search_response = _AsyncResponse(status_code=200, _body=_SEARCH_RESPONSE_BODY)

        with (
            patch.object(
                AsyncHowLongToBeat, "_get_search_auth", AsyncMock(return_value=_MOCK_AUTH)
            ),
            patch.object(
                AsyncHowLongToBeat,
                "_fetch_search_results",
                AsyncMock(return_value=search_response),
            ),
            patch.object(AsyncHowLongToBeat, "_fetch_game_page", AsyncMock(return_value=None)),
        ):
            src = AsyncHowLongToBeat()
            result = await src.fetch("Mock Game", verbose=False)

        assert result["success"] is True
        assert result["data"]["game_id"] == 1234
        assert result["data"]["game_name"] == "Mock Game: The Adventure"

    async def test_async_hltb_label_filtering(self, stub_async_ratelimit) -> None:
        search_response = _AsyncResponse(status_code=200, _body=_SEARCH_RESPONSE_BODY)

        with (
            patch.object(
                AsyncHowLongToBeat, "_get_search_auth", AsyncMock(return_value=_MOCK_AUTH)
            ),
            patch.object(
                AsyncHowLongToBeat,
                "_fetch_search_results",
                AsyncMock(return_value=search_response),
            ),
            patch.object(
                AsyncHowLongToBeat, "_fetch_game_page", AsyncMock(return_value=_GAME_PAGE_DATA)
            ),
        ):
            src = AsyncHowLongToBeat()
            result = await src.fetch(
                "Mock Game", verbose=False, selected_labels=["game_name", "invalid_label"]
            )

        assert result["success"] is True
        assert list(result["data"].keys()) == ["game_name"]
