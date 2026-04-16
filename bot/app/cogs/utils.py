"""Utilities for bot cogs."""

import functools
from typing import Any, Callable

import httpx
from discord import ApplicationContext

from app.embeds.error_embed import build_error_embed


def _safe_error_detail(e: httpx.HTTPStatusError) -> dict[str, Any]:
    """Extract error detail from an HTTPStatusError, falling back gracefully."""
    try:
        return e.response.json()
    except Exception:
        return {"detail": e.response.text or f"HTTP {e.response.status_code}"}


def handle_api_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to handle API errors consistently across all cog commands.

    Wraps cog command methods to catch HTTPStatusError exceptions and
    send formatted error embeds to the user.

    Args:
        func: The cog command method to wrap.

    Returns:
        Wrapped function that handles API errors.

    Example:
        >>> class GamesCog(commands.Cog):
        ...     @discord.slash_command(name="game")
        ...     @handle_api_errors
        ...     async def game(self, ctx, appid: str) -> None:
        ...         data = await self.api.get_game(appid)
        ...         await ctx.followup.send(embed=build_game_embed(data))
    """

    @functools.wraps(func)
    async def wrapper(
        self: Any, ctx: ApplicationContext, *args: Any, **kwargs: Any
    ) -> Any:
        try:
            return await func(self, ctx, *args, **kwargs)
        except httpx.HTTPStatusError as e:
            embed = build_error_embed(_safe_error_detail(e))
            await ctx.followup.send(embed=embed)
        except httpx.RequestError as e:
            embed = build_error_embed({"detail": f"Request failed: {type(e).__name__}"})
            await ctx.followup.send(embed=embed)

    return wrapper
