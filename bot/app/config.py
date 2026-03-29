from pydantic import field_validator
from pydantic_settings import BaseSettings


class BotSettings(BaseSettings):
    discord_token: str
    api_base_url: str = "http://localhost:8000"

    # Timeouts and limits
    api_timeout_seconds: float = 45.0
    reviews_display_count: int = 3

    model_config = {"env_prefix": "GAMEINSIGHTS_BOT_", "env_file": ".env"}

    @field_validator("discord_token")
    @classmethod
    def validate_discord_token(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError(
                "DISCORD_TOKEN is required. "
                "Set GAMEINSIGHTS_BOT_DISCORD_TOKEN environment variable."
            )
        return v.strip()
