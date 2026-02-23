"""Tests for Collector property setters and configuration."""

import pytest

from gameinsights import Collector


@pytest.fixture(autouse=True)
def _mock_hltb_token(monkeypatch):
    """Centralized mock for HowLongToBeat token to avoid repetition."""
    from gameinsights.sources import HowLongToBeat

    monkeypatch.setattr(HowLongToBeat, "_get_search_token", lambda *a, **kw: "mock_token")


class TestCollectorProperties:
    """Tests for Collector property setters."""

    def test_region_property_setter_updates_source(self):
        """Test that setting region updates both collector and SteamStore region."""
        collector = Collector()

        # Set region to a new value
        collector.region = "uk"

        # Verify both collector and source are updated
        assert collector.region == "uk"
        assert collector._region == "uk"
        assert collector.steamstore.region == "uk"

        # Setting to a different value updates both collector and source
        collector.region = "fr"
        assert collector._region == "fr"
        assert collector.steamstore.region == "fr"

    def test_language_property_setter_updates_source(self):
        """Test that setting language updates both collector and SteamStore language."""
        collector = Collector()

        # Set language to a new value
        collector.language = "french"

        # Verify both collector and source are updated
        assert collector.language == "french"
        assert collector._language == "french"
        assert collector.steamstore.language == "french"

    def test_steam_api_key_property_setter_updates_all_sources(self):
        """Test that setting steam_api_key updates all Steam API sources."""
        collector = Collector()

        # Set API key
        test_key = "TEST_API_KEY_12345"  # gitleaks:allow - test value only
        collector.steam_api_key = test_key

        # Verify all sources are updated
        assert collector._steam_api_key == test_key
        assert collector.steamstore.api_key == test_key
        # SteamAchievements and SteamUser may not be instantiated without the key
        # but the collector stores it for when they are created

    def test_gamalytic_api_key_property_setter_updates_source(self):
        """Test that setting gamalytic_api_key updates Gamalytic source."""
        collector = Collector()

        # Set API key
        test_key = "GAMALYTIC_KEY_67890"  # gitleaks:allow - test value only
        collector.gamalytic_api_key = test_key

        # Verify both collector and source are updated
        assert collector._gamalytic_api_key == test_key
        assert collector.gamalytic.api_key == test_key

    def test_property_setter_idempotent(self):
        """Test that setting property to same value doesn't trigger updates."""
        collector = Collector()

        # Set initial value
        collector.region = "de"
        assert collector.steamstore.region == "de"

        # Manually change source region
        collector.steamstore.region = "es"

        # Setting to same value should not update source
        collector.region = "de"
        # Source should remain at the manually set value
        assert collector.steamstore.region == "es"


class TestCollectorConfiguration:
    """Tests for Collector configuration and initialization."""

    def test_collector_initialization_with_api_keys(self):
        """Test Collector initialization with API keys."""
        steam_key = "STEAM_KEY"
        gamalytic_key = "GAMALYTIC_KEY"

        collector = Collector(steam_api_key=steam_key, gamalytic_api_key=gamalytic_key)

        assert collector._steam_api_key == steam_key
        assert collector._gamalytic_api_key == gamalytic_key

    def test_collector_initialization_with_region_language(self):
        """Test Collector initialization with region and language."""
        collector = Collector(region="jp", language="japanese")

        assert collector.region == "jp"
        assert collector.language == "japanese"
        assert collector.steamstore.region == "jp"
        assert collector.steamstore.language == "japanese"
