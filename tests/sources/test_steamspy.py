import pytest

from gameinsights.sources.steamspy import SteamSpy


class TestSteamSpy:
    def test_fetch_success(self, source_fetcher, steamspy_success_response_data):
        result = source_fetcher(
            SteamSpy,
            mock_kwargs={"json_data": steamspy_success_response_data},
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is True
        assert result["data"]["steam_appid"] == 12345
        assert result["data"]["name"] == "Mock Game: The Adventure"
        assert result["data"]["discount"] == 25.5
        assert len(result["data"]) == 18

    def test_fetch_success_unexpected_data(
        self,
        source_fetcher,
        steamspy_success_unexpected_data,
    ):
        result = source_fetcher(
            SteamSpy,
            mock_kwargs={"json_data": steamspy_success_unexpected_data},
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is True
        assert result["data"]["positive_reviews"] == [1234]  # will take whatever thrown by the api
        assert result["data"]["tags"] == []  # defaulted to empty list

    @pytest.mark.parametrize(
        "selected_labels, expected_labels",
        [
            (["name"], ["name"]),
            (["name", "invalid_label"], ["name"]),
        ],
    )
    def test_fetch_success_with_filtering(
        self,
        source_fetcher,
        steamspy_success_response_data,
        selected_labels,
        expected_labels,
    ):
        result = source_fetcher(
            SteamSpy,
            mock_kwargs={"json_data": steamspy_success_response_data},
            call_kwargs={"steam_appid": "12345", "selected_labels": selected_labels},
        )

        assert result["success"] is True

        result_keys = list(result["data"].keys())
        assert sorted(result_keys) == sorted(expected_labels)
        assert len(result["data"]) == len(expected_labels)

    def test_fetch_error_game_not_found(self, source_fetcher, steamspy_not_found_response_data):
        result = source_fetcher(
            SteamSpy,
            mock_kwargs={"json_data": steamspy_not_found_response_data},
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Game with appid 12345 is not found."
