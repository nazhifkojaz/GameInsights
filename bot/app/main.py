import discord
from discord.ext import commands
from app.config import BotSettings
from app.api_client import GameInsightsAPIClient
from app.cogs.games import GamesCog
from app.cogs.reviews import ReviewsCog
from app.cogs.users import UsersCog

settings = BotSettings()
bot = commands.Bot(intents=discord.Intents.default())
bot.api_client = GameInsightsAPIClient(settings)


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")


bot.add_cog(GamesCog(bot))
bot.add_cog(ReviewsCog(bot))
bot.add_cog(UsersCog(bot))

if __name__ == "__main__":
    try:
        bot.run(settings.discord_token)
    finally:
        import asyncio

        asyncio.get_event_loop().run_until_complete(bot.api_client.close())
