import pytest

from gameinsights.sources.gamalytic import Gamalytic


class TestGamalytic:
    def test_fetch_success(self, source_fetcher, gamalytic_success_response_data):
        result = source_fetcher(
            Gamalytic,
            mock_kwargs={"json_data": gamalytic_success_response_data},
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is True
        assert result["data"]["steam_appid"] == "12345"
        assert result["data"]["name"] == "Mock Game: The Adventure"
        assert result["data"]["followers"] == 1234
        assert result["data"]["early_access"] is False

        # should be none because in the mock data, I didn't provide the developers
        assert result["data"]["developers"] is None

        # All 22 Gamalytic labels are returned (followers and early_access were already in _GAMALYTICS_LABELS)
        assert len(result["data"]) == 22

    def test_fetch_success_numeric_appid(self, source_fetcher, gamalytic_success_response_data):
        result = source_fetcher(
            Gamalytic,
            mock_kwargs={"json_data": gamalytic_success_response_data},
            call_kwargs={"steam_appid": 12345},
        )

        assert result["success"] is True
        assert result["data"]["steam_appid"] == "12345"
        assert result["data"]["name"] == "Mock Game: The Adventure"
        assert result["data"]["followers"] == 1234
        assert result["data"]["early_access"] is False
        assert result["data"]["developers"] is None
        # All 22 Gamalytic labels are returned
        assert len(result["data"]) == 22

    @pytest.mark.parametrize(
        "selected_labels, expected_labels, expected_len",
        [
            (["name"], ["name"], 1),
            (["name", "followers"], ["name", "followers"], 2),
            (["early_access"], ["early_access"], 1),
            (["name", "invalid_label"], ["name"], 1),
            (["invalid_label"], [], 0),
        ],
    )
    def test_fetch_success_with_filtering(
        self,
        source_fetcher,
        gamalytic_success_response_data,
        selected_labels,
        expected_labels,
        expected_len,
    ):
        result = source_fetcher(
            Gamalytic,
            mock_kwargs={"json_data": gamalytic_success_response_data},
            call_kwargs={"steam_appid": "12345", "selected_labels": selected_labels},
        )

        assert result["success"] is True

        result_keys = list(result["data"].keys())
        assert sorted(result_keys) == sorted(expected_labels)

        assert len(result["data"]) == expected_len

    @pytest.mark.parametrize(
        "status_code, expected_error",
        [
            (404, {"success": False, "error": "Game with appid 12345 is not found."}),
            (500, {"success": False, "error": "Failed to connect to API. Status code: 500"}),
            (403, {"success": False, "error": "Failed to connect to API. Status code: 403"}),
        ],
    )
    def test_fetch_error(self, source_fetcher, status_code, expected_error):
        result = source_fetcher(
            Gamalytic,
            status_code=status_code,
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] == expected_error["success"]
        assert "error" in result
        assert result["error"] == expected_error["error"]
