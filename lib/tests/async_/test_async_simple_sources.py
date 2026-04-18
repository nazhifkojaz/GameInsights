"""Tests for simple single-call async sources: SteamStore, SteamSpy, ProtonDB."""

from __future__ import annotations

from gameinsights.async_.protondb import AsyncProtonDB
from gameinsights.async_.steamspy import AsyncSteamSpy
from gameinsights.async_.steamstore import AsyncSteamStore

# ---------------------------------------------------------------------------
# AsyncSteamStore
# ---------------------------------------------------------------------------


class TestAsyncSteamStore:
    async def test_async_steamstore_fetch_success(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        json_data = {
            "570": {
                "success": True,
                "data": {
                    "steam_appid": 570,
                    "name": "Dota 2",
                    "type": "game",
                    "is_free": True,
                    "developers": ["Valve"],
                    "publishers": ["Valve"],
                    "release_date": {"coming_soon": False, "date": "Jul 9, 2013"},
                    "recommendations": {"total": 1000000},
                    "platforms": {"windows": True, "mac": True, "linux": True},
                    "categories": [{"description": "Multi-player"}],
                    "genres": [{"description": "Action"}],
                    "ratings": {},
                },
            }
        }
        mock_async_request(AsyncSteamStore, json_data=json_data)
        src = AsyncSteamStore()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is True
        assert result["data"]["name"] == "Dota 2"
        assert result["data"]["is_free"] is True

    async def test_async_steamstore_fetch_not_found(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncSteamStore, json_data={"570": {"success": False}})
        src = AsyncSteamStore()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is False
        assert "not available" in result["error"]

    async def test_async_steamstore_fetch_api_failure(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncSteamStore, status_code=503)
        src = AsyncSteamStore()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is False

    async def test_async_steamstore_selected_labels(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        json_data = {
            "570": {
                "success": True,
                "data": {
                    "steam_appid": 570,
                    "name": "Dota 2",
                    "type": "game",
                    "is_free": True,
                    "release_date": {"coming_soon": False, "date": "Jul 9, 2013"},
                    "ratings": {},
                },
            }
        }
        mock_async_request(AsyncSteamStore, json_data=json_data)
        src = AsyncSteamStore()
        result = await src.fetch("570", verbose=False, selected_labels=["name"])
        assert result["success"] is True
        assert set(result["data"].keys()) == {"name"}


# ---------------------------------------------------------------------------
# AsyncSteamSpy
# ---------------------------------------------------------------------------


class TestAsyncSteamSpy:
    async def test_async_steamspy_fetch_success(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        json_data = {
            "appid": 570,
            "name": "Dota 2",
            "positive": 1000000,
            "negative": 100000,
            "owners": "10,000,000 .. 20,000,000",
            "average_forever": 12000,
            "average_2weeks": 800,
            "median_forever": 600,
            "median_2weeks": 400,
            "ccu": 400000,
            "tags": {"MOBA": 1000, "Strategy": 800},
            "languages": "English, French, German",
        }
        mock_async_request(AsyncSteamSpy, json_data=json_data)
        src = AsyncSteamSpy()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is True
        assert result["data"]["name"] == "Dota 2"
        assert result["data"]["ccu"] == 400000
        assert isinstance(result["data"]["languages"], list)

    async def test_async_steamspy_fetch_not_found(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncSteamSpy, json_data={"appid": 570})
        src = AsyncSteamSpy()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_async_steamspy_fetch_api_failure(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncSteamSpy, status_code=500)
        src = AsyncSteamSpy()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# AsyncProtonDB
# ---------------------------------------------------------------------------


class TestAsyncProtonDB:
    async def test_async_protondb_fetch_success(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        json_data = {
            "tier": "platinum",
            "score": 0.96,
            "trendingTier": "platinum",
            "confidence": "strong",
            "total": 323,
        }
        mock_async_request(AsyncProtonDB, json_data=json_data)
        src = AsyncProtonDB()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is True
        assert result["data"]["protondb_tier"] == "platinum"
        assert result["data"]["protondb_total"] == 323

    async def test_async_protondb_fetch_not_found(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncProtonDB, status_code=404)
        src = AsyncProtonDB()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is False
        assert "not found" in result["error"]

    async def test_async_protondb_fetch_api_failure(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncProtonDB, status_code=503)
        src = AsyncProtonDB()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is False
