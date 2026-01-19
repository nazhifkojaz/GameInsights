import pandas as pd
import pytest

from gameinsights.model import GameDataModel


class TestCollector:
    def test_fetch_raw_data(self, collector_with_mocks):
        raw_data = collector_with_mocks._fetch_raw_data(steam_appid="12345")

        assert isinstance(raw_data, GameDataModel)

    @pytest.mark.parametrize(
        "appids, expected_len",
        [("12345", 1), (["12345", "12345"], 2), ([], 0)],
        ids=["single_appid", "multiple_appids", "empty_appids"],
    )
    def test_get_games_data(self, collector_with_mocks, appids, expected_len):
        games_data = collector_with_mocks.get_games_data(steam_appids=appids)

        assert isinstance(games_data, list)
        assert len(games_data) == expected_len

        if expected_len > 0:
            assert isinstance(games_data[0], dict)
            assert games_data[0]["steam_appid"] == "12345"

    @pytest.mark.parametrize(
        "appids, expected_len",
        [("12345", 1), (["12345", "12345"], 2), ([], 0)],
        ids=["single_appid", "multiple_appids", "empty_appids"],
    )
    def test_get_games_active_player_data(self, collector_with_mocks, appids, expected_len):
        active_player_data = collector_with_mocks.get_games_active_player_data(steam_appids=appids)

        assert isinstance(active_player_data, pd.DataFrame)
        assert len(active_player_data) == expected_len

        if expected_len > 0:
            assert "steam_appid" in active_player_data.columns
            assert active_player_data["steam_appid"].iloc[0] == "12345"

    @pytest.mark.parametrize(
        "review_only, has_reviews_labels",
        [(True, False), (False, True)],
        ids=["review_only_true", "review_only_false"],
    )
    def test_get_game_review(self, collector_with_mocks, review_only, has_reviews_labels):
        review_data = collector_with_mocks.get_game_review(
            steam_appid="12345", review_only=review_only
        )

        assert isinstance(review_data, pd.DataFrame)

        if has_reviews_labels:
            assert "reviews" in review_data.columns
            assert len(review_data["reviews"]) > 0
        else:
            assert "reviews" not in review_data.columns

    def test_all_collector_fields_exist_in_model(self, collector_with_mocks):
        """Verify all collector field names exist in GameDataModel."""
        model_fields = set(GameDataModel.model_fields.keys())

        all_configs = (
            collector_with_mocks.id_based_sources + collector_with_mocks.name_based_sources
        )
        for config in all_configs:
            for field in config.fields:
                assert (
                    field in model_fields
                ), f"Field '{field}' from {config.source.__class__.__name__} not in GameDataModel"
