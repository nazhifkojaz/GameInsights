"""Tests for CLI pandas optional dependency."""

import builtins
import csv
import io
import sys


class TestCLIPandasOptional:
    """Tests for CLI pandas optional dependency."""

    def test_csv_output_with_list_data_works_without_pandas(self, capsys, monkeypatch):
        """Test that CSV output works without pandas when input is list of dicts."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        # Force reimport of cli module without pandas
        monkeypatch.delitem(sys.modules, "gameinsights.cli", raising=False)

        from gameinsights.cli import _output_data

        test_data = [{"steam_appid": "12345", "name": "Test Game"}]

        _output_data(test_data, "csv", None)

        captured = capsys.readouterr()
        output = io.StringIO(captured.out)
        reader = csv.DictReader(output)
        rows = list(reader)

        assert len(rows) == 1
        assert rows[0]["steam_appid"] == "12345"
        assert rows[0]["name"] == "Test Game"

    def test_csv_output_with_multiple_records_works_without_pandas(self, capsys, monkeypatch):
        """Test that CSV output works without pandas with multiple records."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        monkeypatch.delitem(sys.modules, "gameinsights.cli", raising=False)

        from gameinsights.cli import _output_data

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

    def test_csv_output_with_empty_list_works_without_pandas(self, capsys, monkeypatch):
        """Test that CSV output works without pandas when input is empty list."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        monkeypatch.delitem(sys.modules, "gameinsights.cli", raising=False)

        from gameinsights.cli import _output_data

        test_data: list[dict] = []

        _output_data(test_data, "csv", None)

        captured = capsys.readouterr()
        assert captured.out == ""

    def test_json_output_works_without_pandas(self, capsys, monkeypatch):
        """Test that JSON output works without pandas."""
        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "pandas":
                raise ImportError("No module named 'pandas'")
            return original_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", mock_import)

        monkeypatch.delitem(sys.modules, "gameinsights.cli", raising=False)

        from gameinsights.cli import _output_data

        test_data = [{"steam_appid": "12345", "name": "Test Game"}]

        _output_data(test_data, "json", None)

        captured = capsys.readouterr()
        assert '"steam_appid": "12345"' in captured.out
        assert '"name": "Test Game"' in captured.out
