import pytest
from pydantic import ValidationError

from app.config import BotSettings


class TestBotSettings:
    def test_valid_discord_token(self):
        """Test that a valid token is accepted."""
        settings = BotSettings(discord_token="test_token_123")
        assert settings.discord_token == "test_token_123"

    def test_defaults(self, monkeypatch):
        """Test that defaults are correct when no env vars or overrides are set."""
        for key in [
            "GAMEINSIGHTS_BOT_DISCORD_TOKEN",
            "GAMEINSIGHTS_BOT_API_BASE_URL",
            "GAMEINSIGHTS_BOT_API_TIMEOUT_SECONDS",
            "GAMEINSIGHTS_BOT_REVIEWS_DISPLAY_COUNT",
        ]:
            monkeypatch.delenv(key, raising=False)
        settings = BotSettings(discord_token="test_token")
        assert settings.api_base_url == "http://localhost:8000"
        assert settings.api_timeout_seconds == 45.0
        assert settings.reviews_display_count == 3

    def test_empty_discord_token_raises_error(self):
        """Test that empty token raises validation error with helpful message."""
        with pytest.raises(ValidationError) as exc_info:
            BotSettings(discord_token="")

        error_message = str(exc_info.value)
        assert "DISCORD_TOKEN is required" in error_message
        assert "GAMEINSIGHTS_BOT_DISCORD_TOKEN" in error_message

    def test_whitespace_only_discord_token_raises_error(self):
        """Test that whitespace-only token raises validation error."""
        with pytest.raises(ValidationError) as exc_info:
            BotSettings(discord_token="   ")

        error_message = str(exc_info.value)
        assert "DISCORD_TOKEN is required" in error_message

    def test_token_whitespace_is_stripped(self):
        """Test that leading/trailing whitespace is stripped from token."""
        settings = BotSettings(discord_token="  test_token  ")
        assert settings.discord_token == "test_token"

    def test_custom_api_base_url(self):
        """Test custom API base URL."""
        settings = BotSettings(
            discord_token="test_token",
            api_base_url="https://api.example.com",
        )
        assert settings.api_base_url == "https://api.example.com"

    def test_custom_timeouts_and_limits(self):
        """Test custom timeout and review count settings."""
        settings = BotSettings(
            discord_token="test_token",
            api_timeout_seconds=60.0,
            reviews_display_count=5,
        )
        assert settings.api_timeout_seconds == 60.0
        assert settings.reviews_display_count == 5

    def test_env_prefix_loading(self, monkeypatch):
        """Test that settings load from environment variables with prefix."""
        monkeypatch.setenv("GAMEINSIGHTS_BOT_DISCORD_TOKEN", "env_token")
        monkeypatch.setenv("GAMEINSIGHTS_BOT_API_BASE_URL", "https://env.example.com")
        monkeypatch.setenv("GAMEINSIGHTS_BOT_API_TIMEOUT_SECONDS", "30.0")
        monkeypatch.setenv("GAMEINSIGHTS_BOT_REVIEWS_DISPLAY_COUNT", "10")

        settings = BotSettings()
        assert settings.discord_token == "env_token"
        assert settings.api_base_url == "https://env.example.com"
        assert settings.api_timeout_seconds == 30.0
        assert settings.reviews_display_count == 10
