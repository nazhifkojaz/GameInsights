from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from app.cogs.utils import handle_api_errors
from app.constants import STEAM_STATUS_MAP

if TYPE_CHECKING:
    from app.bot import GameInsightsBot


class UsersCog(commands.Cog):
    """Cog for user-related Discord slash commands.

    Provides commands to fetch and display Steam user profiles.

    Attributes:
        bot: The GameInsightsBot instance.
        api: The API client for making GameInsights API calls.
    """

    def __init__(self, bot: "GameInsightsBot") -> None:
        """Initialize the UsersCog.

        Args:
            bot: The GameInsightsBot instance.
        """
        self.bot = bot
        self.api = bot.api_client

    @discord.slash_command(name="user", description="Get Steam user profile")
    @handle_api_errors
    async def user(self, ctx: discord.ApplicationContext, steamid: str) -> None:
        """Fetch and display Steam user profile information.

        Args:
            ctx: Discord application context.
            steamid: Steam user ID to look up.
        """
        await ctx.defer()
        data_list = await self.api.get_user(steamid)
        if not data_list:
            await ctx.followup.send("No user data found.")
            return

        data = data_list[0]
        title = data.get("personaname", "Unknown User")
        url = data.get("profileurl")
        avatar = data.get("avatarfull")

        embed = discord.Embed(
            title=f"User: {title}", url=url, color=discord.Color.purple()
        )
        if avatar:
            embed.set_thumbnail(url=avatar)

        loc = data.get("loccountrycode", "Unknown")
        status = data.get("personastate", 0)

        embed.add_field(
            name="Status", value=STEAM_STATUS_MAP.get(status, "Unknown"), inline=True
        )
        embed.add_field(name="Country", value=loc, inline=True)

        # Additional games library info if available
        games_count = data.get("games_count")
        if games_count is not None:
            embed.add_field(name="Games Owned", value=str(games_count), inline=True)

        await ctx.followup.send(embed=embed)


def setup(bot: "GameInsightsBot") -> None:
    bot.add_cog(UsersCog(bot))
