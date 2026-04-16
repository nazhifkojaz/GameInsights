import pytest

from gameinsights.sources.steamuser import SteamUser


class TestSteamUser:

    @pytest.mark.parametrize(
        "steamresponse_data, expected_result",
        [
            (
                "usersummary_success_response_open_profile",
                {"steamid": "12345", "community_visibility_state": 3, "time_created": 123456789},
            ),
            (
                "usersummary_success_response_closed_profile",
                {"steamid": "12345", "community_visibility_state": 1, "time_created": None},
            ),
        ],
    )
    def test_fetch_summary_success(
        self, source_fetcher, request, steamresponse_data, expected_result
    ):
        response_data = request.getfixturevalue(steamresponse_data)
        result = source_fetcher(
            SteamUser,
            method="_fetch_summary",
            instantiate_kwargs={"api_key": "mockapikey"},
            mock_kwargs={"json_data": response_data},
            call_kwargs={"steamid": "12345", "verbose": False},
        )

        assert result["success"] is True
        assert result["data"]["steamid"] == expected_result["steamid"]
        assert (
            result["data"]["community_visibility_state"]
            == expected_result["community_visibility_state"]
        )
        assert result["data"]["time_created"] == expected_result["time_created"]
        assert len(result["data"]) == 11

    def test_fetch_summary_steamid_not_found(
        self, source_fetcher, usersummary_not_found_response_data
    ):
        result = source_fetcher(
            SteamUser,
            method="_fetch_summary",
            instantiate_kwargs={"api_key": "mockapikey"},
            mock_kwargs={"json_data": usersummary_not_found_response_data},
            call_kwargs={"steamid": "54321", "verbose": False},
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "steamid 54321 not found."

    @pytest.mark.parametrize(
        "status_code, expected_error",
        [
            (403, "Permission denied, please assign correct API Key. (status code 403)."),
            (408, "API Request failed with status 408."),
        ],
        ids=["Wrong_API_Key", "Timed_Out"],
    )
    def test_fetch_summary_error(self, source_fetcher, status_code, expected_error):
        result = source_fetcher(
            SteamUser,
            method="_fetch_summary",
            instantiate_kwargs={"api_key": "invalidapikey"},
            status_code=status_code,
            call_kwargs={"steamid": "12345", "verbose": False},
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == expected_error

    @pytest.mark.parametrize(
        "steamresponse_data, include_free, expected_result",
        [
            (
                "owned_games_exclude_free_response",
                False,
                {"success": True, "game_count": 2, "data_len": 2, "is_free_game_exist": False},
            ),
            (
                "owned_games_include_free_response",
                True,
                {"success": True, "game_count": 3, "data_len": 2, "is_free_game_exist": True},
            ),
            (
                "owned_games_no_games_owned",
                True,
                {"success": True, "game_count": 0, "data_len": 2, "is_free_game_exist": False},
            ),
            (
                "owned_games_only_own_free_games",
                True,
                {"success": True, "game_count": 1, "data_len": 2, "is_free_game_exist": True},
            ),
        ],
    )
    def test_fetch_owned_games_success(
        self, source_fetcher, request, steamresponse_data, include_free, expected_result
    ):
        response_data = request.getfixturevalue(steamresponse_data)
        result = source_fetcher(
            SteamUser,
            method="_fetch_owned_games",
            instantiate_kwargs={"api_key": "mockapikey"},
            mock_kwargs={"json_data": response_data},
            call_kwargs={
                "steamid": "12345",
                "verbose": False,
                "include_free_games": include_free,
            },
        )

        assert result["success"] is expected_result["success"]
        assert result["data"]["game_count"] == expected_result["game_count"]
        assert len(result["data"]) == expected_result["data_len"]
        assert (
            any(game["appid"] == 570 for game in result["data"]["games"])
            is expected_result["is_free_game_exist"]
        )

    @pytest.mark.parametrize(
        "status_code, api_key, expected_error",
        [
            (401, "invalidapikey", "Failed to fetch owned games for steamid 12345."),
            (408, "mockapikey", "Failed to fetch owned games for steamid 12345."),
        ],
    )
    def test_fetch_owned_games_error(
        self,
        source_fetcher,
        status_code,
        api_key,
        expected_error,
    ):
        result = source_fetcher(
            SteamUser,
            method="_fetch_owned_games",
            instantiate_kwargs={"api_key": api_key},
            status_code=status_code,
            call_kwargs={
                "steamid": "12345",
                "verbose": False,
                "include_free_games": True,
            },
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == expected_error

    @pytest.mark.parametrize(
        "steamresponse_data, expected_result",
        [
            (
                "recently_played_games_active_player_response_data",
                {"success": True, "games_count": 2, "total_playtime_2weeks": 13},
            ),
            (
                "recently_played_games_inactive_player_response_data",
                {"success": True, "games_count": 0, "total_playtime_2weeks": 0},
            ),
        ],
    )
    def test_fetch_recently_played_games_success(
        self, source_fetcher, request, steamresponse_data, expected_result
    ):
        response_data = request.getfixturevalue(steamresponse_data)
        result = source_fetcher(
            SteamUser,
            method="_fetch_recently_played_games",
            instantiate_kwargs={"api_key": "mockapikey"},
            mock_kwargs={"json_data": response_data},
            call_kwargs={"steamid": "12345", "verbose": False},
        )

        assert result["success"] is expected_result["success"]
        assert result["data"]["games_count"] == expected_result["games_count"]
        assert result["data"]["total_playtime_2weeks"] == expected_result["total_playtime_2weeks"]

    @pytest.mark.parametrize(
        "status_code, api_key, expected_error",
        [
            (401, "invalidapikey", "Failed to fetch recently played games for steamid 12345."),
            (408, "mockapikey", "Failed to fetch recently played games for steamid 12345."),
        ],
    )
    def test_fetch_recently_played_games_error(
        self,
        source_fetcher,
        status_code,
        api_key,
        expected_error,
    ):
        result = source_fetcher(
            SteamUser,
            method="_fetch_recently_played_games",
            instantiate_kwargs={"api_key": api_key},
            status_code=status_code,
            call_kwargs={"steamid": "12345", "verbose": False},
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == expected_error

    @pytest.mark.parametrize(
        "responses, expected_result",
        [
            # success responses without filtering
            (
                ["usersummary_success_response_closed_profile"],
                {
                    "community_visibility_state": 1,
                    "has_owned_games": False,
                    "has_recently_played_games": False,
                },
            ),
            (
                [
                    "usersummary_success_response_open_profile",
                    "owned_games_no_games_owned",
                    "recently_played_games_inactive_player_response_data",
                ],
                {
                    "community_visibility_state": 3,
                    "has_owned_games": False,
                    "has_recently_played_games": False,
                },
            ),
            (
                [
                    "usersummary_success_response_open_profile",
                    "owned_games_only_own_free_games",
                    "recently_played_games_free_player_response_data",
                ],
                {
                    "community_visibility_state": 3,
                    "has_owned_games": True,
                    "has_recently_played_games": True,
                },
            ),
            (
                [
                    "usersummary_success_response_open_profile",
                    "owned_games_exclude_free_response",
                    "recently_played_games_inactive_player_response_data",
                ],
                {
                    "community_visibility_state": 3,
                    "has_owned_games": True,
                    "has_recently_played_games": False,
                },
            ),
            (
                [
                    "usersummary_success_response_open_profile",
                    "owned_games_exclude_free_response",
                    "recently_played_games_active_player_response_data",
                ],
                {
                    "community_visibility_state": 3,
                    "has_owned_games": True,
                    "has_recently_played_games": True,
                },
            ),
        ],
        ids=[
            "closed_profile",
            "open_profile_but_no_games",
            "open_profile_free_games",
            "open_profile_inactive_player",
            "open_profile_active_player",
        ],
    )
    def test_fetch_success(
        self,
        mock_request_response,
        request,
        responses,
        expected_result,
    ):
        responses_data = []
        for response in responses:
            responses_data.append({"json_data": request.getfixturevalue(response)})

        if len(responses_data) > 1:  # use side effect
            mock_request_response(
                target_class=SteamUser,
                side_effect=responses_data,
            )
        else:
            mock_request_response(target_class=SteamUser, json_data=responses_data[0]["json_data"])

        source = SteamUser(api_key="mockapikey")
        result = source.fetch(steamid="12345")

        assert result["success"] is True
        assert (
            result["data"]["community_visibility_state"]
            == expected_result["community_visibility_state"]
        )
        assert (
            True if result["data"]["owned_games"] else False is expected_result["has_owned_games"]
        )
        assert (
            True
            if result["data"]["recently_played_games"]
            else False is expected_result["has_recently_played_games"]
        )

    @pytest.mark.parametrize(
        "selected_labels, expected_labels",
        [
            (["steamid"], ["steamid"]),
            (["steamid", "invalid_label"], ["steamid"]),
            (["owned_games", "steamid"], ["steamid", "owned_games"]),
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
        mock_request_response,
        usersummary_success_response_open_profile,
        owned_games_include_free_response,
        recently_played_games_active_player_response_data,
        selected_labels,
        expected_labels,
    ):
        mock_request_response(
            target_class=SteamUser,
            side_effect=[
                {"json_data": usersummary_success_response_open_profile},
                {"json_data": owned_games_include_free_response},
                {"json_data": recently_played_games_active_player_response_data},
            ],
        )
        source = SteamUser(api_key="mockapikey")
        result = source.fetch(steamid="12345", selected_labels=selected_labels)

        assert result["success"] is True

        result_keys = list(result["data"].keys())
        assert sorted(result_keys) == sorted(expected_labels)
        assert len(result["data"]) == len(expected_labels)

    def test_fetch_error_no_api_key(self):
        source = SteamUser()
        result = source.fetch(steamid="12345")

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == "API Key is not assigned. Unable to fetch data."
