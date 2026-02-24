import pytest

from gameinsights.sources.steamachievements import SteamAchievements


class Test_SteamAchievements:

    @pytest.mark.parametrize(
        "api_key, selected_labels, expected_result",
        [
            (
                None,
                None,
                {
                    "achievements_count": 2,
                    "achievements_percentage_average": 12.3,
                    "achievements_list": [
                        {"name": "Mock_1", "percent": 12.3},
                        {"name": "Mock_2", "percent": 12.3},
                    ],
                },
            ),
            (None, ["achievements_count"], {"achievements_count": 2}),
            (None, ["achievements_count", "invalid_label"], {"achievements_count": 2}),
            (
                "mockapikey",
                None,
                {
                    "achievements_count": 2,
                    "achievements_percentage_average": 12.3,
                    "achievements_list": [
                        {
                            "name": "Mock_1",
                            "percent": 12.3,
                            "display_name": "Mock One",
                            "hidden": 0,
                            "description": "Clear Mock One",
                        },
                        {
                            "name": "Mock_2",
                            "percent": 12.3,
                            "display_name": "Mock Two",
                            "hidden": 1,
                            "description": None,
                        },
                    ],
                },
            ),
            ("mockapikey", ["achievements_count"], {"achievements_count": 2}),
            ("mockapikey", ["achievements_count", "invalid_label"], {"achievements_count": 2}),
        ],
    )
    def test_fetch_success(
        self,
        source_fetcher,
        achievements_success_response_data,
        scheme_success_response_data,
        api_key,
        selected_labels,
        expected_result,
    ):
        mock_kwargs = (
            {
                "side_effect": [
                    {"json_data": achievements_success_response_data},
                    {"json_data": scheme_success_response_data},
                ]
            }
            if api_key
            else {"json_data": achievements_success_response_data}
        )

        call_kwargs = {"steam_appid": "12345"}
        if selected_labels is not None:
            call_kwargs["selected_labels"] = selected_labels

        result = source_fetcher(
            SteamAchievements,
            instantiate_kwargs={"api_key": api_key} if api_key else None,
            mock_kwargs=mock_kwargs,
            call_kwargs=call_kwargs,
        )

        assert result["success"] is True
        assert len(result["data"]) == len(expected_result)
        assert result["data"] == expected_result

    def test_fetch_unexpected_data(
        self, source_fetcher, achievements_success_with_unexpected_data
    ):
        result = source_fetcher(
            SteamAchievements,
            mock_kwargs={"json_data": achievements_success_with_unexpected_data},
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is True
        assert result["data"]["achievements_count"] == 1
        assert result["data"]["achievements_percentage_average"] == 12.3
        assert result["data"]["achievements_list"] == [{"name": "Mock_3", "percent": 12.3}]

    @pytest.mark.parametrize(
        "api_key, achievements_status_code, schema_status_code , expected_result",
        [
            (None, 400, None, "Failed to connect to API. Status code: 400."),
            ("mockapikey", 200, 403, "Access denied, verify your API Key. Status code: 403."),
            ("mockapikey", 200, 400, "Failed to connect to API. Status code: 400."),
        ],
    )
    def test_fetch_error(
        self,
        source_fetcher,
        api_key,
        achievements_status_code,
        schema_status_code,
        expected_result,
    ):
        mock_kwargs = (
            {
                "side_effect": [
                    {"status_code": achievements_status_code},
                    {"status_code": schema_status_code},
                ]
            }
            if api_key
            else {"status_code": achievements_status_code}
        )

        result = source_fetcher(
            SteamAchievements,
            instantiate_kwargs={"api_key": api_key} if api_key else None,
            mock_kwargs=mock_kwargs,
            call_kwargs={"steam_appid": "12345"},
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == expected_result

    @pytest.mark.parametrize(
        "percentages_data, schema_data, expected_result",
        [
            (
                {
                    "achievementpercentages": {
                        "achievements": [{"name": "Mock_1", "percent": "12.3"}]
                    }
                },
                {},
                {
                    "achievements_count": 1,
                    "achievements_percentage_average": 12.3,
                    "achievements_list": [{"name": "Mock_1", "percent": 12.3}],
                },
            ),
            (
                {
                    "achievementpercentages": {
                        "achievements": [{"name": "Mock_1", "percent": "12.3"}]
                    }
                },
                {
                    "game": {
                        "availableGameStats": {
                            "achievements": [
                                {"name": "Mock_1", "displayName": "Mock One", "hidden": 1}
                            ]
                        }
                    }
                },
                {
                    "achievements_count": 1,
                    "achievements_percentage_average": 12.3,
                    "achievements_list": [
                        {
                            "name": "Mock_1",
                            "percent": 12.3,
                            "display_name": "Mock One",
                            "hidden": 1,
                            "description": None,
                        }
                    ],
                },
            ),
        ],
        ids=[
            "percentages_data_with_empty_schema_data",
            "percentages_data_with_correct_schema_data",
        ],
    )
    def test_transform_data_success(self, percentages_data, schema_data, expected_result):
        source = SteamAchievements()
        result = source._transform_data(data=percentages_data, schema_data=schema_data)

        assert len(result) == len(expected_result)
        assert result == expected_result

    @pytest.mark.parametrize(
        "percentages_data, schema_data, expected_result",
        [
            (
                {},
                {},
                {
                    "achievements_count": None,
                    "achievements_percentage_average": None,
                    "achievements_list": None,
                },
            ),
            (
                {"achievementpercentages": {"notachievements": [{"key_text": 1234}]}},
                {},
                {
                    "achievements_count": None,
                    "achievements_percentage_average": None,
                    "achievements_list": None,
                },
            ),
            (
                {"achievementpercentages": {"achievements": [{"key_text": 1234}]}},
                {},
                {
                    "achievements_count": 0,
                    "achievements_percentage_average": 0.0,
                    "achievements_list": [],
                },
            ),
            (
                {
                    "achievementpercentages": {
                        "achievements": [{"name": "Mock_1", "percent": "12.3"}]
                    }
                },
                {"game": {"availableGameStats": {"achievements": [{"wrong_key": "wrong_value"}]}}},
                {
                    "achievements_count": 1,
                    "achievements_percentage_average": 12.3,
                    "achievements_list": [
                        {
                            "name": "Mock_1",
                            "percent": 12.3,
                            "display_name": None,
                            "hidden": None,
                            "description": None,
                        }
                    ],
                },
            ),
            (
                {
                    "achievementpercentages": {
                        "achievements": [
                            {"name": "Mock_1", "percent": "12.3"},
                            {"name": "Mock_2", "percent": "12.3"},
                        ]
                    }
                },
                {
                    "game": {
                        "availableGameStats": {
                            "achievements": [
                                {"name": "Mock_1", "displayName": "Mock One", "hidden": 1},
                                {"wrong_key": "wrong_value"},
                            ]
                        }
                    }
                },
                {
                    "achievements_count": 2,
                    "achievements_percentage_average": 12.3,
                    "achievements_list": [
                        {
                            "name": "Mock_1",
                            "percent": 12.3,
                            "display_name": "Mock One",
                            "hidden": 1,
                            "description": None,
                        },
                        {
                            "name": "Mock_2",
                            "percent": 12.3,
                            "display_name": None,
                            "hidden": None,
                            "description": None,
                        },
                    ],
                },
            ),
        ],
        ids=[
            "no_percentages_data_no_schema_data",
            "incorrect_percentage_data_no_schema_data",
            "percentages_data_with_incorrect_achievements_structure_no_schema_data",
            "percentages_data_incorrect_schema_data_structure",
            "percentages_data_schema_data_with_incorrect_entry",
        ],
    )
    def test_transform_data_fail_cases(
        self,
        percentages_data,
        schema_data,
        expected_result,
    ):
        source = SteamAchievements()
        result = source._transform_data(data=percentages_data, schema_data=schema_data)

        assert len(result) == len(expected_result)
        assert result == expected_result
