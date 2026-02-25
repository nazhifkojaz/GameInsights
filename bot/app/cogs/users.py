import discord
from discord.ext import commands
import httpx
from app.embeds.error_embed import build_error_embed


class UsersCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api = bot.api_client

    @discord.slash_command(name="user", description="Get Steam user profile")
    async def user(self, ctx: discord.ApplicationContext, steamid: str) -> None:
        await ctx.defer()
        try:
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
            status_map = {
                0: "Offline",
                1: "Online",
                2: "Busy",
                3: "Away",
                4: "Snooze",
                5: "Looking to Trade",
                6: "Looking to Play",
            }

            embed.add_field(
                name="Status", value=status_map.get(status, "Unknown"), inline=True
            )
            embed.add_field(name="Country", value=loc, inline=True)

            # Additional games library info if available
            games_count = data.get("games_count")
            if games_count is not None:
                embed.add_field(name="Games Owned", value=str(games_count), inline=True)

            await ctx.followup.send(embed=embed)
        except httpx.HTTPStatusError as e:
            embed = build_error_embed(e.response.json())
            await ctx.followup.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(UsersCog(bot))
