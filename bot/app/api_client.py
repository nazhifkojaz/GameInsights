import httpx

from app.config import BotSettings
from app.constants import API_ENDPOINTS


class GameInsightsAPIClient:
    """HTTP client for the GameInsights API.

    This client provides methods to fetch game data, reviews, player counts,
    and user profiles from the GameInsights backend API.

    Args:
        settings: Bot configuration containing API base URL and timeout.

    Example:
        >>> settings = BotSettings()
        >>> client = GameInsightsAPIClient(settings)
        >>> game_data = await client.get_game("570")
        >>> await client.close()
    """

    def __init__(self, settings: BotSettings) -> None:
        """Initialize the API client with settings.

        Args:
            settings: Bot configuration including API base URL and timeout.
        """
        self._client = httpx.AsyncClient(
            base_url=settings.api_base_url.rstrip("/"),
            timeout=httpx.Timeout(settings.api_timeout_seconds),
        )

    async def close(self) -> None:
        """Close the HTTP client and release resources.

        This should be called when the bot is shutting down.
        """
        await self._client.aclose()

    async def get_game(self, appid: str) -> dict:
        """Fetch full game data by Steam AppID.

        Args:
            appid: Steam application ID.

        Returns:
            Dictionary containing game information.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status.
        """
        resp = await self._client.get(API_ENDPOINTS["game"].format(appid=appid))
        resp.raise_for_status()
        return resp.json()

    async def get_game_recap(self, appid: str) -> dict:
        """Fetch game recap data by Steam AppID.

        Args:
            appid: Steam application ID.

        Returns:
            Dictionary containing game recap information.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status.
        """
        resp = await self._client.get(API_ENDPOINTS["game_recap"].format(appid=appid))
        resp.raise_for_status()
        return resp.json()

    async def get_reviews(self, appid: str) -> list[dict]:
        """Fetch game reviews by Steam AppID.

        Args:
            appid: Steam application ID.

        Returns:
            List of review dictionaries.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status.
        """
        resp = await self._client.get(API_ENDPOINTS["reviews"].format(appid=appid))
        resp.raise_for_status()
        return resp.json()

    async def get_active_players(self, appid: str) -> list[dict]:
        """Fetch active player count history by Steam AppID.

        Args:
            appid: Steam application ID.

        Returns:
            List of player count data dictionaries.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status.
        """
        resp = await self._client.get(
            API_ENDPOINTS["active_players"].format(appid=appid)
        )
        resp.raise_for_status()
        return resp.json()

    async def get_user(self, steamid: str) -> list[dict]:
        """Fetch Steam user profile by SteamID.

        Args:
            steamid: Steam user ID.

        Returns:
            List containing user profile dictionary.

        Raises:
            httpx.HTTPStatusError: If the API returns an error status.
        """
        resp = await self._client.get(API_ENDPOINTS["user"].format(steamid=steamid))
        resp.raise_for_status()
        return resp.json()
