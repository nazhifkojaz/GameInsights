import pytest

from gameinsights.sources import steamstore
from gameinsights.sources.steamstore import SteamStore


class TestSteamStore:
    def test_fetch_success(self, source_fetcher, steamstore_success_response_data):
        result = source_fetcher(
            SteamStore,
            instantiate_kwargs={"region": "us", "language": "english"},
            mock_kwargs={"json_data": steamstore_success_response_data},
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is True
        assert result["data"]["steam_appid"] == 12345
        assert result["data"]["is_free"] is True
        assert result["data"]["is_coming_soon"] is False
        assert result["data"]["recommendations"] == 1234
        assert result["data"]["type"] == "mock"
        assert len(result["data"]) == len(steamstore._STEAM_LABELS)

        # check if it successfully process the content_rating
        assert result["data"]["content_rating"][0]["rating_type"] == "pegi"
        assert result["data"]["content_rating"][0]["rating"] == "12"

    def test_fetch_success_unexpected_data(
        self,
        source_fetcher,
        steamstore_success_partial_unexpected_data,
    ):
        result = source_fetcher(
            SteamStore,
            instantiate_kwargs={"region": "us", "language": "english"},
            mock_kwargs={"json_data": steamstore_success_partial_unexpected_data},
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is True
        assert result["data"]["steam_appid"] == 12345
        assert result["data"]["type"] == "mock"
        assert len(result["data"]) == len(steamstore._STEAM_LABELS)

        # check if it successfully defaulted the unexpected data to None
        assert result["data"]["price_currency"] is None
        assert result["data"]["price_initial"] is None
        assert result["data"]["content_rating"] == []
        assert result["data"]["categories"] == [None]

    @pytest.mark.parametrize(
        "selected_labels, expected_labels",
        [
            (["name"], ["name"]),
            (["name", "invalid_label"], ["name"]),
            (["steam_appid", "name", "invalid_label"], ["name", "steam_appid"]),
            (["invalid_label"], []),
        ],
        ids=[
            "normal_filtering",
            "filtering_with_invalid_label",
            "filter_labels_unordered",
            "filtering_with_only_invalid_label",
        ],
    )
    def test_fetch_with_filtering(
        self,
        source_fetcher,
        steamstore_success_response_data,
        selected_labels,
        expected_labels,
    ):
        result = source_fetcher(
            SteamStore,
            instantiate_kwargs={"region": "us", "language": "english"},
            mock_kwargs={"json_data": steamstore_success_response_data},
            call_kwargs={"steam_appid": "12345", "selected_labels": selected_labels},
        )

        assert result["success"] is True

        result_keys = list(result["data"].keys())
        assert sorted(result_keys) == sorted(expected_labels)
        assert len(result["data"]) == len(expected_labels)

    def test_fetch_error_connection_fail(
        self,
        source_fetcher,
    ):
        result = source_fetcher(
            SteamStore,
            instantiate_kwargs={"region": "us", "language": "english"},
            status_code=400,
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "Failed to connect to API. Status code: 400."

    def test_fetch_error_game_not_found(self, source_fetcher, steamstore_not_found_response_data):
        result = source_fetcher(
            SteamStore,
            instantiate_kwargs={"region": "us", "language": "english"},
            mock_kwargs={"json_data": steamstore_not_found_response_data},
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is False
        assert "error" in result
        assert (
            result["error"]
            == "Failed to fetch data for appid 12345, or appid is not available in the specified region (us) or language (english)."
        )
