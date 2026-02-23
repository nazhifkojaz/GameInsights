"""Shared CLI test helpers."""

from __future__ import annotations

from typing import Any, Literal

from gameinsights.collector import FetchResult, SourceConfig


class DummySource:
    def __init__(self, name: str) -> None:
        self.__class__ = type(name, (), {})


class DummyCollector:
    """Minimal Collector stand-in for CLI tests.

    Supports the public surface used by ``cli.main``:
    ``get_games_data``, ``get_games_active_player_data``,
    ``id_based_sources``, ``name_based_sources``, context-manager
    protocol, and ``close``.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        steamstore = DummySource("SteamStore")
        gamalytic = DummySource("Gamalytic")
        self._id_based_sources = [
            SourceConfig(steamstore, ["steam_appid", "name", "price_final"]),
            SourceConfig(gamalytic, ["copies_sold"]),
        ]
        self._name_based_sources: list[SourceConfig] = []
        self._records = [
            {
                "steam_appid": "12345",
                "name": "Mock Game",
                "price_final": 12.34,
                "copies_sold": 1000,
            }
        ]
        self._closed = False

    @property
    def id_based_sources(self) -> list[SourceConfig]:
        return self._id_based_sources

    @property
    def name_based_sources(self) -> list[SourceConfig]:
        return self._name_based_sources

    def get_games_data(
        self, steam_appids: list[str], recap: bool = False, verbose: bool = False
    ) -> list[dict[str, Any]]:
        if recap:
            return [
                {
                    "steam_appid": r["steam_appid"],
                    "name": r["name"],
                    "price_final": r["price_final"],
                }
                for r in self._records
            ]
        return self._records

    def get_games_active_player_data(
        self,
        steam_appids: list[str],
        fill_na_as: int = -1,
        verbose: bool = False,
        include_failures: bool = False,
        *,
        return_as: Literal["list", "dataframe"] = "list",
    ) -> list[dict[str, Any]] | tuple[list[dict[str, Any]], list[FetchResult]]:
        data = [
            {
                "steam_appid": "12345",
                "active_player_24h": 111,
            }
        ]
        return data

    def close(self) -> None:
        if not self._closed:
            self._closed = True

    def __enter__(self) -> "DummyCollector":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
