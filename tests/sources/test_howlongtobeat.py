import pytest

from gameinsights.sources.howlongtobeat import HowLongToBeat


class TestHowLongToBeat:

    @pytest.fixture(autouse=True)
    def mock_search_methods(self, monkeypatch):
        """Mock the search methods for testing."""

        def mock_get_token(*args, **kwargs):
            return "mock_token"

        def mock_fetch_search(*args, **kwargs):
            # Return mock response for search
            class MockResponse:
                text = '{"count": 1, "data": [{"game_id": 1234, "game_name": "Mock Game: The Adventure"}]}'
                status_code = 200

            return MockResponse()

        def mock_fetch_page(*args, **kwargs):
            # Return mock game data
            return {
                "game_id": 1234,
                "game_name": "Mock Game: The Adventure",
                "comp_main_avg": 12000,  # Will be converted to 200 mins
            }

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)
        monkeypatch.setattr(HowLongToBeat, "_fetch_search_results", mock_fetch_search)
        monkeypatch.setattr(HowLongToBeat, "_fetch_game_page", mock_fetch_page)

    def test_fetch_success(self, source_fetcher, hltb_success_response_data):
        result = source_fetcher(
            HowLongToBeat,
            mock_kwargs={"text_data": hltb_success_response_data},
            call_kwargs={"game_name": "mock_name"},
        )

        assert result["success"] is True
        assert result["data"]["game_id"] == 1234
        assert result["data"]["game_name"] == "Mock Game: The Adventure"

        # comp_main is now converted from seconds to minutes (12000s = 200m)
        assert result["data"]["comp_main"] == 200

        # check if there number of labels are correct (no stray or missing labels)
        assert len(result["data"]) == 22

    @pytest.mark.parametrize(
        "selected_labels, expected_labels, expected_len",
        [
            (["game_name"], ["game_name"], 1),
            (["game_name", "invalid_label"], ["game_name"], 1),
            (["invalid_label"], [], 0),
        ],
    )
    def test_fetch_success_with_filtering(
        self,
        source_fetcher,
        hltb_success_response_data,
        selected_labels,
        expected_labels,
        expected_len,
    ):
        result = source_fetcher(
            HowLongToBeat,
            mock_kwargs={"text_data": hltb_success_response_data},
            call_kwargs={"game_name": "mock_name", "selected_labels": selected_labels},
        )

        assert result["success"] is True

        result_keys = list(result["data"].keys())
        assert sorted(result_keys) == sorted(expected_labels)

        assert len(result["data"]) == expected_len

    def test_fetch_success_but_empty_game_not_found(
        self,
        source_fetcher,
        hltb_success_but_not_found_data,
    ):
        result = source_fetcher(
            HowLongToBeat,
            mock_kwargs={"text_data": hltb_success_but_not_found_data},
            call_kwargs={"game_name": "mock_name"},
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Game is not found."

    def test_fetch_error_on_token_failure(self, monkeypatch):

        def mock_method(*args, **kwargs):
            return None

        monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_method)

        source = HowLongToBeat()
        result = source.fetch(game_name="mock_data")

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Failed to obtain search token."
