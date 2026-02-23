import pytest

from gameinsights.sources.steamreview import SteamReview


class TestSteamReview:
    @pytest.mark.parametrize(
        "responses, language, expected_result",
        [
            (
                ["review_initial_page", "review_second_page"],
                "all",
                {"len_reviews": 4, "unique_languages": 3},
            ),
            (["review_only_tchinese"], "tchinese", {"len_reviews": 1, "unique_languages": 1}),
            (
                ["review_empty_response"],
                "wronglanguage",
                {"len_reviews": 0, "unique_languages": 0},
            ),
        ],
        ids=[
            "success_with_no_language_filtering",
            "success_with_valid_language_filtering",
            "empty_with_invalid_language_filtering",
        ],
    )
    def test_fetch_mode_review(
        self, source_fetcher, request, responses, language, expected_result
    ):
        if len(responses) > 1:
            mock_kwargs = {
                "side_effect": [
                    {"json_data": request.getfixturevalue(response)} for response in responses
                ]
            }
        else:
            mock_kwargs = {"json_data": request.getfixturevalue(responses[0])}

        result = source_fetcher(
            SteamReview,
            mock_kwargs=mock_kwargs,
            call_kwargs={"steam_appid": "12345", "language": language, "mode": "review"},
        )

        assert result["success"] is True

        assert len(result["data"]["reviews"]) == expected_result["len_reviews"]

        unique_languages = set()
        for review in result["data"]["reviews"]:
            unique_languages.add(review["language"])

        assert len(unique_languages) == expected_result["unique_languages"]

    @pytest.mark.parametrize(
        "selected_labels, expected_labels",
        [
            (["recommendation_id"], ["recommendation_id"]),
            (["recommendation_id", "invalid_label"], ["recommendation_id"]),
        ],
    )
    def test_fetch_mode_review_with_label_filtering(
        self,
        source_fetcher,
        review_only_tchinese,
        selected_labels,
        expected_labels,
    ):
        result = source_fetcher(
            SteamReview,
            mock_kwargs={"json_data": review_only_tchinese},
            call_kwargs={
                "steam_appid": "12345",
                "mode": "review",
                "selected_labels": selected_labels,
            },
        )

        assert result["success"] is True

        result_keys = list(result["data"]["reviews"][0].keys())
        assert sorted(result_keys) == sorted(expected_labels)
        assert len(result["data"]["reviews"][0]) == len(expected_labels)

    @pytest.mark.parametrize(
        "response, language, expected_total_reviews",
        [
            ("review_initial_page", "all", 4),
            ("review_only_tchinese", "tchinese", 1),
            ("review_empty_response", "wronglanguage", 0),
        ],
        ids=[
            "success_with_no_language_filtering",
            "success_with_valid_language_filtering",
            "empty_with_invalid_language_filtering",
        ],
    )
    def test_fetch_mode_summary(
        self, source_fetcher, request, response, language, expected_total_reviews
    ):
        result = source_fetcher(
            SteamReview,
            mock_kwargs={"json_data": request.getfixturevalue(response)},
            call_kwargs={"steam_appid": "12345", "language": language, "mode": "summary"},
        )

        assert result["success"] is True
        assert result["data"]["total_reviews"] == expected_total_reviews

    @pytest.mark.parametrize(
        "selected_labels, expected_labels",
        [
            (["review_score"], ["review_score"]),
            (["review_score", "invalid_label"], ["review_score"]),
        ],
    )
    def test_fetch_mode_summary_with_label_filtering(
        self,
        source_fetcher,
        review_only_tchinese,
        selected_labels,
        expected_labels,
    ):
        result = source_fetcher(
            SteamReview,
            mock_kwargs={"json_data": review_only_tchinese},
            call_kwargs={
                "steam_appid": "12345",
                "mode": "summary",
                "selected_labels": selected_labels,
            },
        )

        assert result["success"] is True

        result_keys = list(result["data"].keys())
        assert sorted(result_keys) == sorted(expected_labels)
        assert len(result["data"]) == len(expected_labels)

    @pytest.mark.parametrize(
        "mode, response, expected_error",
        [
            (
                "summary",
                "review_error_unsuccessful_response",
                "API request failed for game with appid 12345.",
            ),
            (
                "summary",
                "review_error_not_found_response",
                "Game with appid 12345 is not found, or error on the request's cursor.",
            ),
            (
                "review",
                "review_error_unsuccessful_response",
                "API request failed for game with appid 12345.",
            ),
            (
                "review",
                "review_error_not_found_response",
                "Game with appid 12345 is not found, or error on the request's cursor.",
            ),
        ],
        ids=[
            "summary_unsuccessful",
            "summary_not_found_or_cursor_error",
            "review_unsuccessful",
            "review_not_found_or_cursor_error",
        ],
    )
    def test_fetch_error(
        self,
        source_fetcher,
        request,
        mode,
        response,
        expected_error,
    ):
        result = source_fetcher(
            SteamReview,
            mock_kwargs={"json_data": request.getfixturevalue(response)},
            call_kwargs={"steam_appid": "12345", "mode": mode},
        )

        assert result["success"] is False
        assert "error" in result
        assert result["error"] == expected_error
