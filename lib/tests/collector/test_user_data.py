"""Tests for Collector.get_user_data method."""

from unittest.mock import patch

import pytest

from gameinsights import Collector
from gameinsights.sources.howlongtobeat import _SearchAuth


class TestGetUserData:
    """Tests for get_user_data method."""

    def test_get_user_data_returns_list(self, monkeypatch):
        """Test that get_user_data returns a list."""
        from gameinsights.sources import HowLongToBeat, SteamUser

        def mock_get_token(*args, **kwargs):
            return _SearchAuth(
                token="mock_token",
                hp_key="hpKey",
                hp_val="mock_val",
                user_agent="mock_ua",
                extras={},
            )

        monkeypatch.setattr(HowLongToBeat, "_get_search_auth", mock_get_token)

        # Mock successful SteamUser response
        mock_response = {
            "success": True,
            "data": {"steamid": "76561198000000000", "nickname": "TestUser"},
        }

        with patch.object(SteamUser, "fetch", return_value=mock_response):
            with patch("time.sleep"):  # Skip the sleep
                collector = Collector()
                result = collector.get_user_data("76561198000000000", return_as="list")

        # Result should be a list containing user data dicts
        assert isinstance(result, list)

    def test_get_user_data_with_integer_steamid(self, monkeypatch):
        """Test that integer steamid is converted to string."""
        from gameinsights.sources import HowLongToBeat, SteamUser

        def mock_get_token(*args, **kwargs):
            return _SearchAuth(
                token="mock_token",
                hp_key="hpKey",
                hp_val="mock_val",
                user_agent="mock_ua",
                extras={},
            )

        monkeypatch.setattr(HowLongToBeat, "_get_search_auth", mock_get_token)

        mock_response = {
            "success": True,
            "data": {"steamid": "76561198000000000", "nickname": "TestUser"},
        }

        with patch.object(SteamUser, "fetch", return_value=mock_response):
            with patch("time.sleep"):
                collector = Collector()
                result = collector.get_user_data(76561198000000000, return_as="list")

        assert isinstance(result, list)

    def test_get_user_data_empty_list(self, monkeypatch):
        """Test get_user_data with empty steamids list."""
        from gameinsights.sources import HowLongToBeat

        def mock_get_token(*args, **kwargs):
            return _SearchAuth(
                token="mock_token",
                hp_key="hpKey",
                hp_val="mock_val",
                user_agent="mock_ua",
                extras={},
            )

        monkeypatch.setattr(HowLongToBeat, "_get_search_auth", mock_get_token)

        collector = Collector()
        result = collector.get_user_data([], return_as="list")

        assert result == []

    def test_get_user_data_handles_fetch_failure(self, monkeypatch):
        """Test that ErrorResult from SteamUser.fetch is handled gracefully."""
        from gameinsights.sources import HowLongToBeat, SteamUser

        def mock_get_token(*args, **kwargs):
            return _SearchAuth(
                token="mock_token",
                hp_key="hpKey",
                hp_val="mock_val",
                user_agent="mock_ua",
                extras={},
            )

        monkeypatch.setattr(HowLongToBeat, "_get_search_auth", mock_get_token)

        # Mock SteamUser to return an error (fetch contractually never raises)
        mock_response = {
            "success": False,
            "error": "Network error",
        }
        with patch.object(SteamUser, "fetch", return_value=mock_response):
            with patch("time.sleep"):
                collector = Collector()
                result = collector.get_user_data("76561198000000000", return_as="list")

        # Should fall back to steamid-only record
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0] == {"steamid": "76561198000000000"}

    def test_get_user_data_default_is_dataframe(self, monkeypatch):
        """Test that default return_as is 'dataframe'."""
        pd = pytest.importorskip("pandas")
        from gameinsights.sources import HowLongToBeat, SteamUser

        def mock_get_token(*args, **kwargs):
            return _SearchAuth(
                token="mock_token",
                hp_key="hpKey",
                hp_val="mock_val",
                user_agent="mock_ua",
                extras={},
            )

        monkeypatch.setattr(HowLongToBeat, "_get_search_auth", mock_get_token)

        mock_response = {
            "success": True,
            "data": {"steamid": "76561198000000000", "nickname": "TestUser"},
        }

        with patch.object(SteamUser, "fetch", return_value=mock_response):
            with patch("time.sleep"):
                collector = Collector()

                df = collector.get_user_data("76561198000000000")

        assert isinstance(df, pd.DataFrame)

    def test_get_user_data_return_as_list(self, monkeypatch):
        """Test get_user_data with return_as='list'."""
        pytest.importorskip("pandas")
        from gameinsights.sources import HowLongToBeat, SteamUser

        def mock_get_token(*args, **kwargs):
            return _SearchAuth(
                token="mock_token",
                hp_key="hpKey",
                hp_val="mock_val",
                user_agent="mock_ua",
                extras={},
            )

        monkeypatch.setattr(HowLongToBeat, "_get_search_auth", mock_get_token)

        mock_response = {
            "success": True,
            "data": {"steamid": "76561198000000000", "nickname": "TestUser"},
        }

        with patch.object(SteamUser, "fetch", return_value=mock_response):
            with patch("time.sleep"):
                collector = Collector()
                result = collector.get_user_data("76561198000000000", return_as="list")

        assert isinstance(result, list)
        import pandas as pd

        assert not isinstance(result, pd.DataFrame)
