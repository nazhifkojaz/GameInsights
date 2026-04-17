from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    steam_api_key: SecretStr | None = None
    region: str = "us"
    language: str = "english"
    rate_limit_calls: int = 60
    rate_limit_period: int = 60
    collector_pool_size: int = 3
    cache_max_size: int = 256
    cache_ttl_seconds: int = 600
    database_url: str | None = None
    # Allowed CORS origins. Accepts JSON array (e.g. '["http://localhost:3000"]')
    # or comma-separated string (e.g. 'http://localhost:3000,http://localhost:3001')
    # from the GAMEINSIGHTS_CORS_ORIGINS env var.
    cors_origins: list[str] = []
    api_title: str = "GameInsights API"
    api_version: str = "0.1.0"

    # Collector behavior settings
    collector_verbose: bool = False
    collector_raise_on_error: bool = True
    batch_size_limit: int = 10

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json

                return json.loads(v)
            if v:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
            return []
        return v

    model_config = SettingsConfigDict(
        env_prefix="GAMEINSIGHTS_", env_file=".env", extra="ignore"
    )
