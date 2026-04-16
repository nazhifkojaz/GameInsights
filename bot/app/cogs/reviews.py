from typing import TYPE_CHECKING

import discord
from discord.ext import commands

from app.cogs.utils import handle_api_errors

if TYPE_CHECKING:
    from app.bot import GameInsightsBot


class ReviewsCog(commands.Cog):
    """Cog for review-related Discord slash commands.

    Provides commands to fetch and display Steam game reviews.

    Attributes:
        bot: The GameInsightsBot instance.
        api: The API client for making GameInsights API calls.
    """

    def __init__(self, bot: "GameInsightsBot") -> None:
        """Initialize the ReviewsCog.

        Args:
            bot: The GameInsightsBot instance.
        """
        self.bot = bot
        self.api = bot.api_client

    @discord.slash_command(name="reviews", description="Get recent reviews for a game")
    @handle_api_errors
    async def reviews(self, ctx: discord.ApplicationContext, appid: str) -> None:
        """Fetch and display recent reviews for a game.

        Args:
            ctx: Discord application context.
            appid: Steam application ID to look up.
        """
        await ctx.defer()
        data = await self.api.get_reviews(appid)
        if not data:
            await ctx.followup.send("No reviews found for this game.")
            return

        # Simple format, grab top N reviews
        reviews = data[: self.bot.settings.reviews_display_count]
        embed = discord.Embed(
            title=f"Recent Reviews for {appid}", color=discord.Color.blue()
        )

        for review in reviews:
            author = review.get("author", {}).get("steamid", "Unknown")
            content = review.get("review", "No content")
            voted_up = review.get("voted_up")
            score = "👍 Recommended" if voted_up else "👎 Not Recommended"

            # Truncate content if too long
            if len(content) > 300:
                content = content[:300] + "..."

            embed.add_field(
                name=f"User {author} - {score}", value=content, inline=False
            )

        await ctx.followup.send(embed=embed)


def setup(bot: "GameInsightsBot") -> None:
    bot.add_cog(ReviewsCog(bot))
