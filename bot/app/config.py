from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    discord_token: str
    api_base_url: str = "http://localhost:8000"

    model_config = {"env_prefix": "GAMEINSIGHTS_BOT_", "env_file": ".env"}
