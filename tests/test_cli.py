from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterator

import pytest
from tests.fixtures.cli_fixtures import DummyCollector

from gameinsights import cli


@pytest.fixture(autouse=True)
def patched_collector(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setattr(cli, "Collector", DummyCollector)
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


def test_cli_collector_context_manager_called(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify that the Collector is properly used as a context manager.

    This test ensures that when the CLI uses ``with Collector(...) as collector:``,
    the ``__exit__`` method is actually invoked, which is critical for proper
    session cleanup in the real implementation.
    """
    exit_tracker = {"called": False}

    class ExitTrackingDummyCollector(DummyCollector):
        def __exit__(self, *args: object) -> None:
            exit_tracker["called"] = True
            super().__exit__(*args)

    monkeypatch.setattr(cli, "Collector", ExitTrackingDummyCollector)

    exit_code = cli.main(["collect", "--appid", "12345", "--format", "json"])
    assert exit_code == 0
    assert exit_tracker[
        "called"
    ], "Collector.__exit__ should be invoked when using context manager"


def test_cli_collector_context_manager_cleans_up_on_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify that the Collector.__exit__ is called even when an exception occurs.

    This test ensures that session cleanup happens even when the collection
    process encounters an error, which is critical for proper resource management.
    """
    exit_tracker = {"called": False}

    class FailingDummyCollector(DummyCollector):
        def get_games_data(self, steam_appids: list[str], **kwargs: Any) -> Any:
            raise RuntimeError("Simulated collection failure")

        def __exit__(self, *args: object) -> None:
            exit_tracker["called"] = True
            # Don't call super().__exit__ since it doesn't suppress exceptions anyway
            self.close()

    monkeypatch.setattr(cli, "Collector", FailingDummyCollector)

    # The CLI will propagate the RuntimeError, but __exit__ should still be called
    with pytest.raises(RuntimeError):
        cli.main(["collect", "--appid", "12345", "--format", "json"])

    assert exit_tracker[
        "called"
    ], "Collector.__exit__ should be invoked even when an exception occurs"
