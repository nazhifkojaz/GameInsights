from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import pandas as pd
import pytest

from gameinsights import cli
from gameinsights.collector import SourceConfig


class _DummySource:
    def __init__(self, name: str) -> None:
        self.__class__ = type(name, (), {})


class _DummyCollector:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        steamstore = _DummySource("SteamStore")
        gamalytic = _DummySource("Gamalytic")
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

    @property
    def id_based_sources(self) -> list[SourceConfig]:
        return self._id_based_sources

    @property
    def name_based_sources(self) -> list[SourceConfig]:
        return self._name_based_sources

    def get_games_data(
        self, steam_appids: list[str], recap: bool = False, verbose: bool = False
    ) -> list[dict[str, Any]]:
        return self._records

    def get_games_active_player_data(
        self, steam_appids: list[str], verbose: bool = False
    ) -> pd.DataFrame:
        data = {
            "steam_appid": ["12345"],
            "active_player_24h": [111],
        }
        return pd.DataFrame(data)

    def __enter__(self) -> "_DummyCollector":
        return self

    def __exit__(self, *args: object) -> None:
        pass


@pytest.fixture(autouse=True)
def patched_collector(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(cli, "Collector", _DummyCollector)
    yield
    monkeypatch.undo()


def test_cli_collect_games_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["collect", "--appid", "12345", "--format", "json"])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Collecting data for 1 appid(s)..." in captured.err
    payload = json.loads(captured.out)
    assert payload[0]["steam_appid"] == "12345"
    assert payload[0]["name"] == "Mock Game"


def test_cli_collect_games_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    output_path = tmp_path / "output.csv"
    exit_code = cli.main(
        ["collect", "--appid", "12345", "--format", "csv", "--output", str(output_path)]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert output_path.read_text(encoding="utf-8").startswith("steam_appid")
    assert "Collecting data for 1 appid(s)..." in captured.err
    assert captured.out == ""


def test_cli_collect_games_with_source_filter(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(
        ["collect", "--appid", "12345", "--format", "json", "--source", "steamstore"]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Collecting data for 1 appid(s)..." in captured.err
    payload = json.loads(captured.out)
    record = payload[0]
    assert "price_final" in record
    assert "copies_sold" not in record


def test_cli_collect_active_player(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(
        ["collect", "--appid", "12345", "--mode", "active-player", "--format", "csv"]
    )
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Collecting data for 1 appid(s)..." in captured.err
    assert "active_player_24h" in captured.out


def test_cli_missing_appids(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = cli.main(["collect"])
    assert exit_code == 1
    stderr = capsys.readouterr().err
    assert "No appids supplied" in stderr
