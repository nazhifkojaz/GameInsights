"""Tests for AsyncCollector."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from gameinsights.async_collector import AsyncCollector
from gameinsights.exceptions import GameNotFoundError, InvalidRequestError

# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

_BASE_GAME_DATA: dict[str, Any] = {
    "steam_appid": "570",
    "name": "Dota 2",
    "type": "game",
    "developers": ["Valve"],
    "publishers": ["Valve"],
    "release_date": "2013-07-09",
    "price_currency": "USD",
    "price_initial": 0,
    "price_final": 0,
    "is_free": True,
    "is_coming_soon": False,
    "genres": ["Strategy", "Action"],
    "categories": [],
    "platforms": ["windows"],
    "metacritic_score": None,
    "content_rating": None,
    "recommendations": None,
    "total_reviews": 1000000,
    "total_positive": 900000,
    "total_negative": 100000,
    "review_score": 9,
    "review_score_desc": "Overwhelmingly Positive",
    "ccu": 400000,
    "tags": [],
    "discount": 0,
    "average_playtime_min": 120,
    "languages": ["English"],
    "active_player_24h": 400000,
    "peak_active_player_all_time": 1000000,
    "monthly_active_player": [
        {
            "month": "2025-01",
            "average_players": 400000.0,
            "gain": None,
            "percentage_gain": 0,
            "peak_players": 500000.0,
        }
    ],
    "achievements_count": 10,
    "achievements_percentage_average": 50.0,
    "achievements_list": None,
    "protondb_tier": "platinum",
    "protondb_score": 0.9,
    "protondb_trending": None,
    "protondb_confidence": "good",
    "protondb_total": 5000,
}

_STEAMCHARTS_DATA = {
    "steam_appid": "570",
    "name": "Dota 2",
    "active_player_24h": 400000,
    "peak_active_player_all_time": 1000000,
    "monthly_active_player": [
        {
            "month": "2025-01",
            "average_players": 400000.0,
            "gain": None,
            "percentage_gain": 0,
            "peak_players": 500000.0,
        }
    ],
}

_REVIEW_DATA = {
    "review_score": 9,
    "review_score_desc": "Overwhelmingly Positive",
    "total_positive": 900000,
    "total_negative": 100000,
    "total_reviews": 1000000,
    "reviews": [
        {
            "recommendation_id": "abc",
            "author_steamid": "123",
            "review": "Great game!",
            "voted_up": True,
        }
    ],
}

_USER_DATA = {
    "steamid": "76561198000000000",
    "community_visibility_state": 3,
    "persona_name": "TestUser",
    "profile_url": "https://steamcommunity.com/id/test/",
    "owned_games": {},
    "recently_played_games": {},
}


def _make_success(data: dict[str, Any]) -> dict[str, Any]:
    return {"success": True, "data": data}


def _make_error(msg: str) -> dict[str, Any]:
    return {"success": False, "error": msg}


@pytest.fixture
def mock_all_sources(monkeypatch):
    """Patch every async source fetch on AsyncCollector's instances after init."""

    async def patch_sources(collector: AsyncCollector) -> None:
        await collector._ensure_initialized()
        monkeypatch.setattr(
            collector.steamstore, "fetch", AsyncMock(return_value=_make_success(_BASE_GAME_DATA))
        )
        monkeypatch.setattr(
            collector.steamspy, "fetch", AsyncMock(return_value=_make_success(_BASE_GAME_DATA))
        )
        monkeypatch.setattr(
            collector.steamcharts,
            "fetch",
            AsyncMock(return_value=_make_success(_STEAMCHARTS_DATA)),
        )
        monkeypatch.setattr(
            collector.steamreview,
            "fetch",
            AsyncMock(return_value=_make_success(_REVIEW_DATA)),
        )
        monkeypatch.setattr(
            collector.steamachievements,
            "fetch",
            AsyncMock(return_value=_make_success(_BASE_GAME_DATA)),
        )
        monkeypatch.setattr(
            collector.protondb, "fetch", AsyncMock(return_value=_make_success(_BASE_GAME_DATA))
        )
        _hltb_data = {
            "game_id": 1234,
            "game_name": "Dota 2",
            "game_type": "game",
            "comp_main": 200,
            "comp_plus": None,
            "comp_100": None,
            "comp_all": None,
            "comp_main_count": None,
            "comp_plus_count": None,
            "comp_100_count": None,
            "comp_all_count": None,
            "invested_co": None,
            "invested_mp": None,
            "invested_co_count": None,
            "invested_mp_count": None,
            "count_comp": None,
            "count_speed_run": None,
            "count_backlog": None,
            "count_review": None,
            "review_score": None,
            "count_playing": None,
            "count_retired": None,
        }
        monkeypatch.setattr(
            collector.howlongtobeat,
            "fetch",
            AsyncMock(return_value=_make_success(_hltb_data)),
        )
        monkeypatch.setattr(
            collector.steamuser, "fetch", AsyncMock(return_value=_make_success(_USER_DATA))
        )

    return patch_sources


# ---------------------------------------------------------------------------
# Initialisation and context manager
# ---------------------------------------------------------------------------


class TestAsyncCollectorInit:
    async def test_context_manager_initializes_and_closes(self) -> None:
        async with AsyncCollector() as col:
            assert col._initialized is True
            assert col._session is not None
        assert col._session is None
        assert col._initialized is False

    async def test_ensure_initialized_idempotent(self) -> None:
        col = AsyncCollector()
        await col._ensure_initialized()
        session_id = id(col._session)
        await col._ensure_initialized()
        assert id(col._session) == session_id
        await col.close()


# ---------------------------------------------------------------------------
# get_games_data
# ---------------------------------------------------------------------------


class TestAsyncCollectorGetGamesData:
    async def test_single_appid_returns_game_dict(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        result = await col.get_games_data("570", verbose=False)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["steam_appid"] == "570"
        await col.close()

    async def test_multiple_appids_returns_list(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        result = await col.get_games_data(["570", "570"], verbose=False)
        assert len(result) == 2
        await col.close()

    async def test_empty_appids_returns_empty_list(self) -> None:
        col = AsyncCollector()
        result = await col.get_games_data([], verbose=False)
        assert result == []
        await col.close()

    async def test_include_failures_returns_tuple(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        result = await col.get_games_data("570", verbose=False, include_failures=True)
        assert isinstance(result, tuple)
        data, fetch_results = result
        assert len(data) == 1
        assert fetch_results[0].success is True
        await col.close()

    async def test_primary_source_failure_with_raise_on_error(self, monkeypatch) -> None:
        col = AsyncCollector()
        await col._ensure_initialized()
        monkeypatch.setattr(
            col.steamstore,
            "fetch",
            AsyncMock(
                return_value=_make_error("appid 570 is not available in the specified region.")
            ),
        )
        # Patch remaining sources with no-op success
        for attr in ("steamspy", "steamcharts", "steamreview", "steamachievements", "protondb"):
            monkeypatch.setattr(
                getattr(col, attr), "fetch", AsyncMock(return_value=_make_success({}))
            )
        with pytest.raises(GameNotFoundError):
            await col.get_games_data("570", verbose=False, raise_on_error=True)
        await col.close()

    async def test_raise_on_error_with_empty_appids(self) -> None:
        col = AsyncCollector()
        with pytest.raises(InvalidRequestError):
            await col.get_games_data([], verbose=False, raise_on_error=True)
        await col.close()

    async def test_recap_mode_returns_subset(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        result = await col.get_games_data("570", recap=True, verbose=False)
        assert isinstance(result, list)
        assert len(result) == 1
        # Recap returns a smaller subset of fields
        full_result_raw = await col.get_games_data("570", verbose=False)
        assert len(result[0]) <= len(full_result_raw[0])
        await col.close()


# ---------------------------------------------------------------------------
# get_games_active_player_data
# ---------------------------------------------------------------------------


class TestAsyncCollectorActivePlayerData:
    async def test_active_player_data_single_appid(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        result = await col.get_games_active_player_data("570", verbose=False)
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["steam_appid"] == "570"
        await col.close()

    async def test_active_player_data_empty_returns_empty(self) -> None:
        col = AsyncCollector()
        result = await col.get_games_active_player_data([], verbose=False)
        assert result == []
        await col.close()

    async def test_active_player_data_include_failures(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        result = await col.get_games_active_player_data(
            "570", verbose=False, include_failures=True
        )
        assert isinstance(result, tuple)
        data, fetch_results = result
        assert fetch_results[0].success is True
        await col.close()


# ---------------------------------------------------------------------------
# get_game_review
# ---------------------------------------------------------------------------


class TestAsyncCollectorGetGameReview:
    async def test_get_game_review_returns_list(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        # Override steamreview.fetch to return review mode data
        col.steamreview.fetch = AsyncMock(return_value=_make_success(_REVIEW_DATA))  # type: ignore[method-assign]
        result = await col.get_game_review("570", verbose=False)
        assert isinstance(result, list)
        assert len(result) == 1
        await col.close()

    async def test_get_game_review_review_only_false(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        col.steamreview.fetch = AsyncMock(return_value=_make_success(_REVIEW_DATA))  # type: ignore[method-assign]
        result = await col.get_game_review("570", verbose=False, review_only=False)
        assert isinstance(result, list)
        assert "reviews" in result[0]
        await col.close()

    async def test_get_game_review_raises_on_empty_appid(self) -> None:
        col = AsyncCollector()
        with pytest.raises(InvalidRequestError):
            await col.get_game_review("", verbose=False)
        await col.close()


# ---------------------------------------------------------------------------
# get_user_data
# ---------------------------------------------------------------------------


class TestAsyncCollectorGetUserData:
    async def test_get_user_data_single_id(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await col.get_user_data("76561198000000000", verbose=False, return_as="list")
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["persona_name"] == "TestUser"
        await col.close()

    async def test_get_user_data_multiple_ids(self, mock_all_sources) -> None:
        col = AsyncCollector()
        await mock_all_sources(col)
        with patch("asyncio.sleep", new_callable=AsyncMock):
            result = await col.get_user_data(
                ["76561198000000000", "76561198000000001"], verbose=False, return_as="list"
            )
        assert len(result) == 2
        await col.close()
