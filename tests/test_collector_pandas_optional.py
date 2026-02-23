"""Tests for optional pandas dependency."""

import pytest

from gameinsights import DependencyNotInstalledError


class TestPandasOptional:
    """Tests for optional pandas dependency."""

    def test_get_user_data_dataframe_raises_dependency_not_installed_without_pandas(
        self, collector_with_mocks, without_pandas
    ):
        """Test that get_user_data with return_as='dataframe' raises DependencyNotInstalledError without pandas."""
        with pytest.raises(DependencyNotInstalledError) as exc_info:
            collector_with_mocks.get_user_data("12345", return_as="dataframe")

        assert exc_info.value.package == "pandas"
        assert exc_info.value.install_extra == "dataframe"

    def test_get_user_data_default_raises_dependency_not_installed_without_pandas(
        self, collector_with_mocks, without_pandas
    ):
        """Test that get_user_data with default return_as (dataframe) raises without pandas."""
        with pytest.raises(DependencyNotInstalledError) as exc_info:
            collector_with_mocks.get_user_data("12345")

        assert exc_info.value.package == "pandas"

    def test_get_user_data_list_works_without_pandas(self, collector_with_mocks, without_pandas):
        """Test that get_user_data with return_as='list' works without pandas."""
        result = collector_with_mocks.get_user_data("12345", return_as="list")
        assert isinstance(result, list)

    def test_get_games_active_player_data_list_works_without_pandas(
        self, collector_with_mocks, without_pandas
    ):
        """Test that get_games_active_player_data with default return_as='list' works without pandas."""
        result = collector_with_mocks.get_games_active_player_data("12345")
        assert isinstance(result, list)

    def test_get_games_active_player_data_empty_list_works_without_pandas(
        self, collector_with_mocks, without_pandas
    ):
        """Test that get_games_active_player_data with empty list works without pandas."""
        result = collector_with_mocks.get_games_active_player_data([])
        assert result == []

    def test_get_game_review_list_works_without_pandas(self, collector_with_mocks, without_pandas):
        """Test that get_game_review with default return_as='list' works without pandas."""
        result = collector_with_mocks.get_game_review("12345")
        assert isinstance(result, list)

    def test_get_games_active_player_data_dataframe_raises_dependency_not_installed_without_pandas(
        self, collector_with_mocks, without_pandas
    ):
        """Test that get_games_active_player_data with return_as='dataframe' raises DependencyNotInstalledError without pandas."""
        with pytest.raises(DependencyNotInstalledError) as exc_info:
            collector_with_mocks.get_games_active_player_data("12345", return_as="dataframe")

        assert exc_info.value.package == "pandas"
        assert exc_info.value.install_extra == "dataframe"

    def test_get_game_review_dataframe_raises_dependency_not_installed_without_pandas(
        self, collector_with_mocks, without_pandas
    ):
        """Test that get_game_review with return_as='dataframe' raises DependencyNotInstalledError without pandas."""
        with pytest.raises(DependencyNotInstalledError) as exc_info:
            collector_with_mocks.get_game_review("12345", return_as="dataframe")

        assert exc_info.value.package == "pandas"
        assert exc_info.value.install_extra == "dataframe"

    def test_get_games_data_never_imports_pandas(self, collector_with_mocks, without_pandas):
        """Test that get_games_data never imports pandas (returns list)."""
        result = collector_with_mocks.get_games_data("12345")
        assert isinstance(result, list)
