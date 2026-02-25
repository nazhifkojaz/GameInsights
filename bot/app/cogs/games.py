import discord
from discord.ext import commands
import httpx
from app.embeds.game_embed import build_game_embed, build_players_embed
from app.embeds.error_embed import build_error_embed


class GamesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.api = bot.api_client

    @discord.slash_command(name="game", description="Get full game data")
    async def game(self, ctx: discord.ApplicationContext, appid: str) -> None:
        await ctx.defer()
        try:
            data = await self.api.get_game(appid)
            embed = build_game_embed(data)
            await ctx.followup.send(embed=embed)
        except httpx.HTTPStatusError as e:
            embed = build_error_embed(e.response.json())
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="game-recap", description="Get game recap")
    async def game_recap(self, ctx: discord.ApplicationContext, appid: str) -> None:
        await ctx.defer()
        try:
            data = await self.api.get_game_recap(appid)
            embed = build_game_embed(data)
            await ctx.followup.send(embed=embed)
        except httpx.HTTPStatusError as e:
            embed = build_error_embed(e.response.json())
            await ctx.followup.send(embed=embed)

    @discord.slash_command(name="players", description="Active player history")
    async def players(self, ctx: discord.ApplicationContext, appid: str) -> None:
        await ctx.defer()
        try:
            data = await self.api.get_active_players(appid)
            embed = build_players_embed(data, appid=appid)
            await ctx.followup.send(embed=embed)
        except httpx.HTTPStatusError as e:
            embed = build_error_embed(e.response.json())
            await ctx.followup.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(GamesCog(bot))
