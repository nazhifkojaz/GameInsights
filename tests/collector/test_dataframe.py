"""Tests for Collector DataFrame conversion functionality."""

import pytest

# Skip all tests in this module if pandas is not installed
pd = pytest.importorskip("pandas")

# Import helper functions from conftest
from tests.conftest import assert_fetch_result, assert_list_not_tuple


class TestCollectorDataFrame:
    """Tests for DataFrame return_as parameter functionality."""

    def test_get_games_active_player_data_as_dataframe(self, collector_with_mocks):
        """Test that return_as='dataframe' returns DataFrame with correct column order."""
        df = collector_with_mocks.get_games_active_player_data(
            steam_appids=["12345"], return_as="dataframe"
        )

        assert isinstance(df, pd.DataFrame)
        assert not isinstance(df, tuple)

        # Verify column order: fixed columns first, then sorted months
        columns = list(df.columns)
        assert columns[0] == "steam_appid"
        assert columns[1] == "name"
        assert columns[2] == "peak_active_player_all_time"

        # Remaining columns should be month columns in sorted order
        month_columns = columns[3:]
        assert month_columns == sorted(
            month_columns
        ), f"Month columns should be sorted: {month_columns}"

    def test_get_game_review_as_dataframe(self, collector_with_mocks):
        """Test that return_as='dataframe' returns DataFrame."""
        df = collector_with_mocks.get_game_review(steam_appid="12345", return_as="dataframe")

        assert isinstance(df, pd.DataFrame)

    def test_get_games_active_player_data_list_default(self, collector_with_mocks):
        """Test that default behavior returns list."""
        data = collector_with_mocks.get_games_active_player_data(steam_appids=["12345"])
        assert_list_not_tuple(data)

    def test_get_game_review_list_default(self, collector_with_mocks):
        """Test that default behavior returns list."""
        data = collector_with_mocks.get_game_review(steam_appid="12345")

        assert isinstance(data, list)

    def test_get_games_active_player_data_fill_na_as_parameter(self, collector_with_mocks):
        """Test that fill_na_as parameter correctly fills missing month values."""
        df = collector_with_mocks.get_games_active_player_data(
            steam_appids=["12345"], return_as="dataframe", fill_na_as=-999
        )

        assert isinstance(df, pd.DataFrame)
        # Verify no NaN values remain — fill_na_as should replace all missing data
        month_cols = [
            c
            for c in df.columns
            if c not in ["steam_appid", "name", "peak_active_player_all_time"]
        ]
        for col in month_cols:
            assert not df[col].isna().any(), f"Column '{col}' still contains NaN after fill_na_as"

    def test_get_games_active_player_data_empty_with_return_as_dataframe(
        self, collector_with_mocks
    ):
        """Test that empty input with return_as='dataframe' returns empty DataFrame."""
        df = collector_with_mocks.get_games_active_player_data(
            steam_appids=[], return_as="dataframe"
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 0

    def test_get_games_active_player_data_empty_with_return_as_list(self, collector_with_mocks):
        """Test that empty input with return_as='list' returns empty list."""
        data = collector_with_mocks.get_games_active_player_data(steam_appids=[], return_as="list")

        assert isinstance(data, list)
        assert len(data) == 0

    def test_get_games_active_player_data_dataframe_with_include_failures(
        self, collector_with_mocks
    ):
        """Test that return_as='dataframe' with include_failures=True returns (DataFrame, results)."""
        df, results = collector_with_mocks.get_games_active_player_data(
            steam_appids=["12345"], return_as="dataframe", include_failures=True
        )

        assert isinstance(df, pd.DataFrame)
        assert len(df) == 1
        assert isinstance(results, list)
        assert len(results) == 1
        assert_fetch_result(results[0], "12345")
