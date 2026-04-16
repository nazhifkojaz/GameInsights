import pytest
from unittest.mock import AsyncMock, MagicMock
from app.api_client import GameInsightsAPIClient
from app.config import BotSettings


@pytest.fixture
def mock_settings():
    return BotSettings(discord_token="test_token")


@pytest.fixture
def mock_api():
    api = AsyncMock(spec=GameInsightsAPIClient)
    return api


@pytest.fixture
def mock_bot(mock_api):
    bot = MagicMock()
    bot.api_client = mock_api
    return bot


@pytest.fixture
def mock_ctx():
    ctx = AsyncMock()
    ctx.defer = AsyncMock()
    ctx.followup.send = AsyncMock()
    return ctx
