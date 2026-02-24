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
