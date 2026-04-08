"""gameinsights: Steam game data collector library."""

from .collector import Collector
from .exceptions import (
    DependencyNotInstalledError,
    GameInsightsError,
    GameNotFoundError,
    InvalidRequestError,
    SourceUnavailableError,
)
from .model.game_data import GameDataModel

__all__ = [
    "Collector",
    "DependencyNotInstalledError",
    "GameDataModel",
    "GameInsightsError",
    "GameNotFoundError",
    "InvalidRequestError",
    "SourceUnavailableError",
]

try:
    from .async_collector import AsyncCollector

    __all__ = [*__all__, "AsyncCollector"]
except ImportError:
    pass
