import httpx
from app.config import BotSettings


class GameInsightsAPIClient:
    def __init__(self, settings: BotSettings) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.api_base_url.rstrip("/"),
            timeout=httpx.Timeout(45.0),  # 45s for 5-30s fetch + overhead
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_game(self, appid: str) -> dict:
        resp = await self._client.get(f"/games/{appid}")
        resp.raise_for_status()
        return resp.json()

    async def get_game_recap(self, appid: str) -> dict:
        resp = await self._client.get(f"/games/{appid}/recap")
        resp.raise_for_status()
        return resp.json()

    async def get_reviews(self, appid: str) -> list[dict]:
        resp = await self._client.get(f"/games/{appid}/reviews")
        resp.raise_for_status()
        return resp.json()

    async def get_active_players(self, appid: str) -> list[dict]:
        resp = await self._client.get(f"/games/{appid}/active-players")
        resp.raise_for_status()
        return resp.json()

    async def get_user(self, steamid: str) -> list[dict]:
        resp = await self._client.get(f"/users/{steamid}")
        resp.raise_for_status()
        return resp.json()
