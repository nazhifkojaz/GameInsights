"""Tests for ProtonDB source."""

import pytest

from gameinsights.sources.protondb import ProtonDB


class TestProtonDB:

    def test_fetch_success(
        self,
        source_fetcher,
        protondb_success_response_data,
    ):
        """Test successful fetch with platinum tier."""
        result = source_fetcher(
            ProtonDB,
            mock_kwargs={"json_data": protondb_success_response_data},
            call_kwargs={"steam_appid": "570"},
        )

        assert result["success"] is True
        assert result["data"]["steam_appid"] == "570"
        assert result["data"]["protondb_tier"] == "platinum"
        assert result["data"]["protondb_score"] == 0.85
        assert result["data"]["protondb_trending"] == "platinum"
        assert result["data"]["protondb_confidence"] == "strong"
        assert result["data"]["protondb_total"] == 323

    def test_fetch_gold_tier(
        self,
        source_fetcher,
        protondb_gold_tier_response_data,
    ):
        """Test successful fetch with gold tier."""
        result = source_fetcher(
            ProtonDB,
            mock_kwargs={"json_data": protondb_gold_tier_response_data},
            call_kwargs={"steam_appid": "730"},
        )

        assert result["success"] is True
        assert result["data"]["steam_appid"] == "730"
        assert result["data"]["protondb_tier"] == "gold"
        assert result["data"]["protondb_score"] == 0.75
        assert result["data"]["protondb_trending"] == "silver"
        assert result["data"]["protondb_confidence"] == "good"
        assert result["data"]["protondb_total"] == 150

    def test_fetch_with_filtering(
        self,
        source_fetcher,
        protondb_success_response_data,
    ):
        """Test fetch with label filtering."""
        result = source_fetcher(
            ProtonDB,
            mock_kwargs={"json_data": protondb_success_response_data},
            call_kwargs={"steam_appid": "570", "selected_labels": ["protondb_tier"]},
        )

        assert result["success"] is True
        assert result["data"] == {"protondb_tier": "platinum"}

    @pytest.mark.parametrize(
        "selected_labels, expected_len",
        [
            (["protondb_tier", "protondb_score"], 2),  # Both labels
            (["protondb_tier"], 1),  # Single label
            ([], 6),  # All labels (includes steam_appid)
        ],
    )
    def test_fetch_with_various_filters(
        self,
        source_fetcher,
        protondb_success_response_data,
        selected_labels,
        expected_len,
    ):
        """Test fetch with various filter combinations."""
        result = source_fetcher(
            ProtonDB,
            mock_kwargs={"json_data": protondb_success_response_data},
            call_kwargs={
                "steam_appid": "570",
                "selected_labels": selected_labels,
            },
        )

        assert result["success"] is True
        assert len(result["data"]) == expected_len

    def test_fetch_not_found(
        self,
        source_fetcher,
        protondb_not_found_response_data,
    ):
        """Test fetch when game is not found (404)."""
        result = source_fetcher(
            ProtonDB,
            status_code=404,
            mock_kwargs={"text_data": protondb_not_found_response_data},
            call_kwargs={"steam_appid": "99999"},
        )

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_fetch_no_data(
        self,
        source_fetcher,
        protondb_no_data_response_data,
    ):
        """Test fetch when game exists but tier is null (no reports yet)."""
        result = source_fetcher(
            ProtonDB,
            mock_kwargs={"json_data": protondb_no_data_response_data},
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is True
        assert result["data"]["protondb_tier"] is None
        assert result["data"]["protondb_score"] == 0.0
        assert result["data"]["protondb_confidence"] == "inadequate"
        assert result["data"]["protondb_total"] == 0

    def test_fetch_server_error(
        self,
        source_fetcher,
        protondb_server_error_response_data,
    ):
        """Test fetch when ProtonDB returns 500 Internal Server Error."""
        result = source_fetcher(
            ProtonDB,
            status_code=500,
            mock_kwargs={"text_data": protondb_server_error_response_data},
            call_kwargs={"steam_appid": "570"},
        )

        assert result["success"] is False
        assert "error" in result
        assert "status code" in result["error"].lower()

    def test_fetch_malformed_json(
        self,
        source_fetcher,
        protondb_malformed_json_response_data,
    ):
        """Test fetch when response contains invalid JSON."""
        import json

        result = source_fetcher(
            ProtonDB,
            mock_kwargs={"json_raises": json.JSONDecodeError},
            call_kwargs={"steam_appid": "570"},
        )

        assert result["success"] is False
        assert "error" in result
        assert "parse" in result["error"].lower()

    def test_fetch_partial_data(
        self,
        source_fetcher,
        protondb_partial_response_data,
    ):
        """Test fetch when API returns partial data (missing optional fields)."""
        result = source_fetcher(
            ProtonDB,
            mock_kwargs={"json_data": protondb_partial_response_data},
            call_kwargs={"steam_appid": "570"},
        )

        assert result["success"] is True
        # Missing fields should be None
        assert result["data"]["protondb_score"] is None
        assert result["data"]["protondb_trending"] is None
        # Present fields should have values
        assert result["data"]["protondb_confidence"] == "inadequate"
        assert result["data"]["protondb_total"] == 0
