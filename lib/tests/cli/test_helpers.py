"""Tests for CLI helper functions."""

import pytest

from gameinsights import cli
from gameinsights.collector import SourceConfig


class TestReadAppids:
    """Tests for _read_appids helper function."""

    def test_read_appids_from_file(self, tmp_path):
        """Test reading appids from a file."""
        appid_file = tmp_path / "appids.txt"
        appid_file.write_text("12345\n67890\n\n42\n")

        appids = cli._read_appids([], str(appid_file))

        assert appids == ["12345", "67890", "42"]

    def test_read_appids_removes_duplicates(self, tmp_path):
        """Test that duplicate appids are removed."""
        appid_file = tmp_path / "appids.txt"
        appid_file.write_text("12345\n67890\n12345\n42\n67890\n")

        appids = cli._read_appids([], str(appid_file))

        assert appids == ["12345", "67890", "42"]
        # Check no duplicates
        assert len(appids) == len(set(appids))

    def test_read_appids_empty_file(self, tmp_path):
        """Test reading from an empty file."""
        appid_file = tmp_path / "empty.txt"
        appid_file.write_text("\n\n   \n")

        appids = cli._read_appids([], str(appid_file))

        assert appids == []

    def test_read_appids_whitespace_handling(self, tmp_path):
        """Test that whitespace is properly handled."""
        appid_file = tmp_path / "whitespace.txt"
        appid_file.write_text("  12345  \n\t67890\t\n  42  \n")

        appids = cli._read_appids([], str(appid_file))

        assert appids == ["12345", "67890", "42"]

    def test_read_appids_comma_separated(self, tmp_path):
        """Test handling comma-separated values."""
        appid_file = tmp_path / "commas.txt"
        appid_file.write_text("12345,67890,42")

        appids = cli._read_appids([], str(appid_file))

        assert appids == ["12345", "67890", "42"]

    def test_read_appids_mixed_format(self, tmp_path):
        """Test handling mixed newlines and commas."""
        appid_file = tmp_path / "mixed.txt"
        appid_file.write_text("12345,67890\n42,100\n200")

        appids = cli._read_appids([], str(appid_file))

        assert appids == ["12345", "67890", "42", "100", "200"]

    def test_read_appids_file_not_found(self, tmp_path):
        """Test handling when appid file doesn't exist."""
        non_existent = tmp_path / "does_not_exist.txt"

        with pytest.raises(FileNotFoundError):
            cli._read_appids([], str(non_existent))

    def test_read_appids_from_cli_args(self):
        """Test reading appids from CLI arguments."""
        appids = cli._read_appids(["12345", "67890"], None)

        assert appids == ["12345", "67890"]


class TestBuildSourceIndex:
    """Tests for _build_source_index helper function."""

    def test_build_source_index(self):
        """Test building source field index."""
        from gameinsights.sources import SteamStore

        # Create SourceConfig objects
        configs = [SourceConfig(SteamStore(session=None, region="us"), ["steam_appid", "name"])]

        index = cli._build_source_index(configs)

        # Check that index contains source names as keys
        assert "steamstore" in index

        # Check that values are sets of field names
        for source_name, fields in index.items():
            assert isinstance(fields, set)
            assert all(isinstance(f, str) for f in fields)

    def test_build_source_index_empty_sources(self):
        """Test building index with empty sources list."""
        index = cli._build_source_index([])

        assert index == {}

    def test_build_source_index_includes_expected_fields(self):
        """Test that index includes expected fields."""
        from gameinsights.sources import SteamStore

        configs = [
            SourceConfig(SteamStore(session=None, region="us"), ["steam_appid", "name", "type"])
        ]

        index = cli._build_source_index(configs)

        steamstore_fields = index.get("steamstore")

        assert steamstore_fields is not None
        assert "steam_appid" in steamstore_fields
        assert "name" in steamstore_fields
        assert "type" in steamstore_fields


class TestFilterRecords:
    """Tests for _filter_records helper function."""

    def test_filter_records_with_allowed_fields(self):
        """Test filtering records to only include allowed fields."""
        records = [
            {"steam_appid": "12345", "name": "Game 1", "price": 10.0, "secret": "value"},
            {"steam_appid": "67890", "name": "Game 2", "price": 20.0, "secret": "value2"},
        ]

        allowed_fields = {"steam_appid", "name"}

        filtered = cli._filter_records(records, allowed_fields)

        assert len(filtered) == 2
        for record in filtered:
            assert "steam_appid" in record
            assert "name" in record
            assert "price" not in record
            assert "secret" not in record

    def test_filter_records_with_empty_allowed_fields_returns_same(self):
        """Test that empty allowed_fields returns records unchanged."""
        records = [
            {"steam_appid": "12345", "name": "Game 1"},
        ]

        # Empty allowed fields returns records as-is
        filtered = cli._filter_records(records, set())

        assert filtered == records

    def test_filter_records_all_fields_allowed(self):
        """Test that allowing all fields returns unchanged records."""
        records = [
            {"steam_appid": "12345", "name": "Game 1", "price": 10.0},
        ]

        allowed_fields = {"steam_appid", "name", "price"}

        filtered = cli._filter_records(records, allowed_fields)

        assert filtered == records

    def test_filter_records_missing_fields(self):
        """Test filtering when some records don't have all allowed fields."""
        records = [
            {"steam_appid": "12345", "name": "Game 1"},
            {"steam_appid": "67890"},  # Missing 'name'
        ]

        allowed_fields = {"steam_appid", "name"}

        filtered = cli._filter_records(records, allowed_fields)

        assert len(filtered) == 2
        assert filtered[0] == {"steam_appid": "12345", "name": "Game 1"}
        # Second record should only have steam_appid (name is missing from data)
        assert "steam_appid" in filtered[1]
        assert "name" not in filtered[1]

    def test_filter_records_empty_list(self):
        """Test filtering empty records list."""
        filtered = cli._filter_records([], {"steam_appid"})

        assert filtered == []
