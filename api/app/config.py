from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    steam_api_key: str | None = None
    gamalytic_api_key: str | None = None
    region: str = "us"
    language: str = "english"
    rate_limit_calls: int = 60
    rate_limit_period: int = 60
    collector_pool_size: int = 3
    cache_max_size: int = 256
    cache_ttl_seconds: int = 600
    database_url: str | None = None
    cors_origins: list[str] = ["*"]
    api_title: str = "GameInsights API"
    api_version: str = "0.1.0"

    # Collector behavior settings
    collector_verbose: bool = False
    collector_raise_on_error: bool = True
    batch_size_limit: int = 10

    model_config = {"env_prefix": "GAMEINSIGHTS_", "env_file": ".env"}
