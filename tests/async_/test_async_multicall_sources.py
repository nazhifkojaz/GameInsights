"""Tests for multi-call async sources: SteamCharts, SteamReview, SteamAchievements, SteamUser."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from gameinsights.async_.steamachievements import AsyncSteamAchievements
from gameinsights.async_.steamcharts import AsyncSteamCharts
from gameinsights.async_.steamreview import AsyncSteamReview
from gameinsights.async_.steamuser import AsyncSteamUser

# ---------------------------------------------------------------------------
# AsyncSteamCharts  (HTML scraping)
# ---------------------------------------------------------------------------

_STEAMCHARTS_HTML = """
<html><body>
<h1 id="app-title">Dota 2</h1>
<div class="app-stat"><span>400,000</span></div>
<div class="app-stat"><span>400000</span></div>
<div class="app-stat"><span>1000000</span></div>
<table class="common-table">
  <tr></tr><tr></tr>
  <tr><td>January 2025</td><td>400,000</td><td>5,000</td><td>1.26%</td><td>500,000</td></tr>
</table>
</body></html>
"""


class TestAsyncSteamCharts:
    async def test_async_steamcharts_fetch_success(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncSteamCharts, text_data=_STEAMCHARTS_HTML)
        src = AsyncSteamCharts()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is True
        assert result["data"]["name"] == "Dota 2"
        assert len(result["data"]["monthly_active_player"]) == 1

    async def test_async_steamcharts_fetch_http_failure(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncSteamCharts, status_code=403)
        src = AsyncSteamCharts()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is False

    async def test_async_steamcharts_fetch_parse_failure(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncSteamCharts, text_data="<html><body></body></html>")
        src = AsyncSteamCharts()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is False
        assert "Failed to parse" in result["error"]


# ---------------------------------------------------------------------------
# AsyncSteamReview
# ---------------------------------------------------------------------------

_REVIEW_PAGE_SINGLE = {
    "success": 1,
    "cursor": "done",
    "query_summary": {
        "review_score": 9,
        "review_score_desc": "Overwhelmingly Positive",
        "total_positive": 900000,
        "total_negative": 50000,
        "total_reviews": 950000,
    },
    "reviews": [],
}


class TestAsyncSteamReview:
    async def test_async_steamreview_summary_mode(self, stub_async_ratelimit) -> None:
        mock = AsyncMock(return_value=_REVIEW_PAGE_SINGLE)
        with patch.object(AsyncSteamReview, "_fetch_page", mock):
            src = AsyncSteamReview()
            result = await src.fetch("570", verbose=False, mode="summary")
        assert result["success"] is True
        assert result["data"]["total_positive"] == 900000

    async def test_async_steamreview_api_failure(self, stub_async_ratelimit) -> None:
        mock = AsyncMock(
            return_value={"success": 0, "cursor": None, "query_summary": {}, "reviews": []}
        )
        with patch.object(AsyncSteamReview, "_fetch_page", mock):
            src = AsyncSteamReview()
            result = await src.fetch("570", verbose=False)
        assert result["success"] is False

    async def test_async_steamreview_review_mode_single_page(self, stub_async_ratelimit) -> None:
        page = {
            "success": 1,
            "cursor": "done",
            "query_summary": {
                "review_score": 9,
                "review_score_desc": "Overwhelmingly Positive",
                "total_positive": 5,
                "total_negative": 1,
                "total_reviews": 6,
            },
            "reviews": [
                {
                    "recommendationid": "abc",
                    "author": {"steamid": "123"},
                    "review": "Great game!",
                    "voted_up": True,
                }
            ],
        }
        # Second call returns same cursor + empty reviews — signals end-of-pages
        terminator = {**page, "reviews": []}
        mock = AsyncMock(side_effect=[page, terminator])
        with patch.object(AsyncSteamReview, "_fetch_page", mock):
            src = AsyncSteamReview()
            result = await src.fetch("570", verbose=False, mode="review")
        assert result["success"] is True
        assert len(result["data"]["reviews"]) == 1


# ---------------------------------------------------------------------------
# AsyncSteamAchievements
# ---------------------------------------------------------------------------

_PCT_DATA = {
    "achievementpercentages": {
        "achievements": [
            {"name": "ACH_1", "percent": 80.0},
            {"name": "ACH_2", "percent": 20.0},
        ]
    }
}


class TestAsyncSteamAchievements:
    async def test_async_achievements_fetch_without_api_key(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncSteamAchievements, json_data=_PCT_DATA)
        src = AsyncSteamAchievements()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is True
        assert result["data"]["achievements_count"] == 2
        assert result["data"]["achievements_percentage_average"] == 50.0

    async def test_async_achievements_fetch_with_api_key_parallel(
        self, stub_async_ratelimit
    ) -> None:
        schema_data = {
            "game": {
                "availableGameStats": {
                    "achievements": [
                        {"name": "ACH_1", "displayName": "First!"},
                        {"name": "ACH_2", "displayName": "Second!"},
                    ]
                }
            }
        }
        import json

        from gameinsights.async_.base import _AsyncResponse

        async def fake_make_request(*args, **kwargs):  # type: ignore[no-untyped-def]
            url = kwargs.get("url", "")
            if "SchemaForGame" in (url or ""):
                return _AsyncResponse(200, json.dumps(schema_data).encode())
            return _AsyncResponse(200, json.dumps(_PCT_DATA).encode())

        src = AsyncSteamAchievements(api_key="test_key")
        with patch.object(src, "_make_request", fake_make_request):
            result = await src.fetch("570", verbose=False)

        assert result["success"] is True
        assert result["data"]["achievements_list"][0]["display_name"] == "First!"

    async def test_async_achievements_fetch_api_failure(
        self, mock_async_request, stub_async_ratelimit
    ) -> None:
        mock_async_request(AsyncSteamAchievements, status_code=500)
        src = AsyncSteamAchievements()
        result = await src.fetch("570", verbose=False)
        assert result["success"] is False


# ---------------------------------------------------------------------------
# AsyncSteamUser
# ---------------------------------------------------------------------------

_SUMMARY_RESPONSE = {
    "response": {
        "players": [
            {
                "steamid": "76561198000000000",
                "communityvisibilitystate": 3,
                "personaname": "TestUser",
                "profileurl": "https://steamcommunity.com/id/test/",
            }
        ]
    }
}

_OWNED_GAMES_RESPONSE = {
    "response": {"game_count": 2, "games": [{"appid": 570, "name": "Dota 2"}]}
}

_RECENTLY_PLAYED_RESPONSE = {
    "response": {
        "total_count": 1,
        "games": [
            {"appid": 570, "name": "Dota 2", "playtime_2weeks": 120, "playtime_forever": 5000}
        ],
    }
}


class TestAsyncSteamUser:
    async def test_async_steamuser_no_api_key_returns_error(self, stub_async_ratelimit) -> None:
        src = AsyncSteamUser()
        result = await src.fetch("76561198000000000", verbose=False)
        assert result["success"] is False
        assert "API Key" in result["error"]

    async def test_async_steamuser_fetch_public_profile(self, stub_async_ratelimit) -> None:
        import json

        from gameinsights.async_.base import _AsyncResponse

        call_urls = []

        async def fake_make_request(*args, **kwargs):  # type: ignore[no-untyped-def]
            url = kwargs.get("url") or ""
            call_urls.append(url)
            if "GetOwnedGames" in url:
                return _AsyncResponse(200, json.dumps(_OWNED_GAMES_RESPONSE).encode())
            if "GetRecentlyPlayedGames" in url:
                return _AsyncResponse(200, json.dumps(_RECENTLY_PLAYED_RESPONSE).encode())
            return _AsyncResponse(200, json.dumps(_SUMMARY_RESPONSE).encode())

        src = AsyncSteamUser(api_key="test_key")
        with patch.object(src, "_make_request", fake_make_request):
            result = await src.fetch("76561198000000000", verbose=False)

        assert result["success"] is True
        assert result["data"]["persona_name"] == "TestUser"
        assert result["data"]["owned_games"]["game_count"] == 2

    async def test_async_steamuser_fetch_private_profile_skips_games(
        self, stub_async_ratelimit
    ) -> None:
        private_response = {
            "response": {
                "players": [
                    {
                        "steamid": "76561198000000000",
                        "communityvisibilitystate": 1,  # PRIVATE
                        "personaname": "PrivateUser",
                    }
                ]
            }
        }
        import json

        from gameinsights.async_.base import _AsyncResponse

        async def fake_make_request(*args, **kwargs):  # type: ignore[no-untyped-def]
            return _AsyncResponse(200, json.dumps(private_response).encode())

        src = AsyncSteamUser(api_key="test_key")
        with patch.object(src, "_make_request", fake_make_request):
            result = await src.fetch("76561198000000000", verbose=False)

        assert result["success"] is True
        assert result["data"]["owned_games"] == {}
        assert result["data"]["recently_played_games"] == {}
