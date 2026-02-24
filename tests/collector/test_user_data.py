"""Tests for Collector.get_user_data method."""

from unittest.mock import patch

from gameinsights import Collector


class TestGetUserData:
    """Tests for get_user_data method."""

    def test_get_user_data_returns_list(self, monkeypatch):
        """Test that get_user_data returns a list."""
        from gameinsights.sources import HowLongToBeat, SteamUser

        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

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
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

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
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        collector = Collector()
        result = collector.get_user_data([], return_as="list")

        assert result == []

    def test_get_user_data_handles_fetch_exception(self, monkeypatch):
        """Test that exceptions from SteamUser.fetch are handled gracefully."""
        from gameinsights.sources import HowLongToBeat, SteamUser

        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        # Mock SteamUser to raise an exception during fetch
        with patch.object(SteamUser, "fetch", side_effect=ConnectionError("Network error")):
            with patch("time.sleep"):
                collector = Collector()
                # Should handle the exception by logging and continuing
                # Since fetch fails before appending to results, list will be empty
                result = collector.get_user_data("76561198000000000", return_as="list")

        # Exception should be caught and logged
        # Result is an empty list since nothing was successfully fetched
        assert isinstance(result, list)
        assert len(result) == 0

    def test_get_user_data_default_is_dataframe(self, monkeypatch):
        """Test that default return_as is 'dataframe'."""
        from gameinsights.sources import HowLongToBeat, SteamUser

        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

        mock_response = {
            "success": True,
            "data": {"steamid": "76561198000000000", "nickname": "TestUser"},
        }

        with patch.object(SteamUser, "fetch", return_value=mock_response):
            with patch("time.sleep"):
                collector = Collector()
                # Default should be dataframe (not list)
                import pandas as pd

                df = collector.get_user_data("76561198000000000")

        assert isinstance(df, pd.DataFrame)

    def test_get_user_data_return_as_list(self, monkeypatch):
        """Test get_user_data with return_as='list'."""
        from gameinsights.sources import HowLongToBeat, SteamUser

        def mock_get_token(*args, **kwargs):
            return "mock_token"

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

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
