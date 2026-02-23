"""Tests for CLI pandas optional dependency."""

import csv
import io
import sys

import pytest


@pytest.fixture
def cli_reimport(monkeypatch):
    """Evict and reimport cli module to test without pandas."""
    monkeypatch.delitem(sys.modules, "gameinsights.cli", raising=False)
    # Force fresh import after eviction
    import gameinsights.cli

    return gameinsights.cli


class TestCLIPandasOptional:
    """Tests for CLI pandas optional dependency."""

    def test_csv_output_with_list_data_works_without_pandas(
        self, capsys, without_pandas, cli_reimport
    ):
        """Test that CSV output works without pandas when input is list of dicts."""
        _output_data = cli_reimport._output_data
        test_data = [{"steam_appid": "12345", "name": "Test Game"}]

        _output_data(test_data, "csv", None)

        captured = capsys.readouterr()
        output = io.StringIO(captured.out)
        reader = csv.DictReader(output)
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["steam_appid"] == "12345"
        assert rows[0]["name"] == "Test Game"

    def test_csv_output_with_multiple_records_works_without_pandas(
        self, capsys, without_pandas, cli_reimport
    ):
        """Test that CSV output works without pandas with multiple records."""
        _output_data = cli_reimport._output_data
        test_data = [
            {"steam_appid": "12345", "name": "Test Game 1"},
            {"steam_appid": "67890", "name": "Test Game 2"},
        ]

        _output_data(test_data, "csv", None)

        captured = capsys.readouterr()
        output = io.StringIO(captured.out)
        reader = csv.DictReader(output)
        rows = list(reader)

        assert len(rows) == 2
        assert rows[0]["steam_appid"] == "12345"
        assert rows[1]["steam_appid"] == "67890"

    def test_csv_output_with_empty_list_works_without_pandas(
        self, capsys, without_pandas, cli_reimport
    ):
        """Test that CSV output works without pandas when input is empty list."""
        _output_data = cli_reimport._output_data
        test_data: list[dict] = []

        _output_data(test_data, "csv", None)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_json_output_works_without_pandas(
        self, capsys, without_pandas, cli_reimport
    ):
        """Test that JSON output works without pandas."""
        _output_data = cli_reimport._output_data
        test_data = [{"steam_appid": "12345", "name": "Test Game"}]

        _output_data(test_data, "json", None)

        captured = capsys.readouterr()
        assert '"steam_appid": "12345"' in captured.out
        assert '"name": "Test Game"' in captured.out
