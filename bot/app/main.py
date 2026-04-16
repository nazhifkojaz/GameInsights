import discord

from app.bot import GameInsightsBot
from app.cogs.games import GamesCog
from app.cogs.reviews import ReviewsCog
from app.cogs.users import UsersCog
from app.config import BotSettings


def main() -> None:
    settings = BotSettings()
    bot = GameInsightsBot(
        settings=settings,
        intents=discord.Intents.default(),
    )

    @bot.event
    async def on_ready() -> None:
        print(f"Logged in as {bot.user}")

    bot.add_cog(GamesCog(bot))
    bot.add_cog(ReviewsCog(bot))
    bot.add_cog(UsersCog(bot))

    bot.run(settings.discord_token)


if __name__ == "__main__":
    main()
