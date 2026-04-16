from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from app.cogs.utils import handle_api_errors
from app.embeds.game_embed import build_game_embed, build_players_graph

if TYPE_CHECKING:
    from app.bot import GameInsightsBot


class GamesCog(commands.Cog):
    """Cog for game-related Discord slash commands.

    Provides commands to fetch and display Steam game information,
    including full game data, recap summaries, and player history.

    Attributes:
        bot: The GameInsightsBot instance.
        api: The API client for making GameInsights API calls.
    """

    def __init__(self, bot: "GameInsightsBot") -> None:
        """Initialize the GamesCog.

        Args:
            bot: The GameInsightsBot instance.
        """
        self.bot = bot
        self.api = bot.api_client

    @discord.slash_command(name="game", description="Get full game data")
    @handle_api_errors
    async def game(self, ctx: discord.ApplicationContext, appid: str) -> None:
        """Fetch and display full game information.

        Args:
            ctx: Discord application context.
            appid: Steam application ID to look up.
        """
        await ctx.defer()
        data = await self.api.get_game(appid)
        embed = build_game_embed(data)
        await ctx.followup.send(embed=embed)

    @discord.slash_command(name="game-recap", description="Get game recap")
    @handle_api_errors
    async def game_recap(self, ctx: discord.ApplicationContext, appid: str) -> None:
        """Fetch and display game recap information.

        Args:
            ctx: Discord application context.
            appid: Steam application ID to look up.
        """
        await ctx.defer()
        data = await self.api.get_game_recap(appid)
        embed = build_game_embed(data)
        await ctx.followup.send(embed=embed)

    @discord.slash_command(name="players", description="Active player history")
    @handle_api_errors
    async def players(self, ctx: discord.ApplicationContext, appid: str) -> None:
        """Fetch and display active player count history as a graph.

        Args:
            ctx: Discord application context.
            appid: Steam application ID to look up.
        """
        await ctx.defer()
        data = await self.api.get_active_players(appid)
        graph_file = build_players_graph(data, appid=appid)
        await ctx.followup.send(file=graph_file)


def setup(bot: "GameInsightsBot") -> None:
    """Add the GamesCog to the bot.

    Args:
        bot: The GameInsightsBot instance.
    """
    bot.add_cog(GamesCog(bot))
