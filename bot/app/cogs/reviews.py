import discord
from discord.ext import commands
import httpx
from app.embeds.error_embed import build_error_embed


class ReviewsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api = bot.api_client

    @discord.slash_command(name="reviews", description="Get recent reviews for a game")
    async def reviews(self, ctx: discord.ApplicationContext, appid: str) -> None:
        await ctx.defer()
        try:
            data = await self.api.get_reviews(appid)
            if not data:
                await ctx.followup.send("No reviews found for this game.")
                return

            # Simple format, grab top 3 reviews
            reviews = data[:3]
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
        except httpx.HTTPStatusError as e:
            embed = build_error_embed(e.response.json())
            await ctx.followup.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(ReviewsCog(bot))
