from discord.ext import commands

from app.api_client import GameInsightsAPIClient
from app.config import BotSettings


class GameInsightsBot(commands.Bot):
    """Discord bot for GameInsights with typed API client.

    This bot extends commands.Bot to provide a typed api_client attribute
    for making API calls to the GameInsights backend.

    Attributes:
        settings: Bot configuration settings.
        api_client: HTTP client for GameInsights API calls.
    """

    def __init__(self, settings: BotSettings, *args, **kwargs) -> None:
        """Initialize the bot with settings.

        Args:
            settings: Bot configuration including Discord token and API URL.
            *args: Additional arguments passed to commands.Bot.
            **kwargs: Additional keyword arguments passed to commands.Bot.
        """
        super().__init__(*args, **kwargs)
        self.settings = settings
        self.api_client = GameInsightsAPIClient(settings)
