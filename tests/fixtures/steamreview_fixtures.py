"""Fixtures for SteamReview source tests."""

import pytest


@pytest.fixture
def review_initial_page():
    """First page of review results."""
    return {
        "success": 1,
        "query_summary": {
            "num_reviews": 2,
            "review_score": 5,
            "review_score_desc": "Mostly Positive",
            "total_positive": 2,
            "total_negative": 2,
            "total_reviews": 4,
        },
        "reviews": [
            {
                "recommendationid": "1",
                "author": {
                    "steamid": "1",
                    "num_games_owned": 1,
                    "num_reviews": 1,
                    "playtime_forever": 3,
                    "playtime_last_two_weeks": 0,
                    "playtime_at_review": 3,
                    "last_played": 12345,
                },
                "language": "english",
                "review": "mock review",
                "voted_up": True,
            },
            {
                "recommendationid": "2",
                "author": {
                    "steamid": "2",
                    "num_games_owned": 1,
                    "num_reviews": 1,
                    "playtime_forever": 2,
                    "playtime_last_two_weeks": 1,
                    "playtime_at_review": 2,
                    "last_played": 12345,
                },
                "language": "tchinese",
                "review": "mock review but in tchinese",
                "voted_up": False,
            },
        ],
        "cursor": "nextcursor",
    }


@pytest.fixture
def review_second_page():
    """Second page of review results."""
    return {
        "success": 1,
        "query_summary": {
            "num_reviews": 2,
        },
        "reviews": [
            {
                "recommendationid": "3",
                "author": {
                    "steamid": "3",
                    "num_games_owned": 1,
                    "num_reviews": 1,
                    "playtime_forever": 3,
                    "playtime_last_two_weeks": 0,
                    "playtime_at_review": 3,
                    "last_played": 12345,
                },
                "language": "english",
                "review": "mock review",
                "voted_up": True,
            },
            {
                "recommendationid": "4",
                "author": {
                    "steamid": "4",
                    "num_games_owned": 1,
                    "num_reviews": 1,
                    "playtime_forever": 2,
                    "playtime_last_two_weeks": 1,
                    "playtime_at_review": 2,
                    "last_played": 12345,
                },
                "language": "schinese",
                "review": "another mock review",
                "voted_up": False,
            },
        ],
        "cursor": "nextcursor",
    }


@pytest.fixture
def review_error_not_found_response():
    """Error response when reviews are not found."""
    return {"success": 1, "query_summary": {"num_reviews": 0}, "reviews": [], "cursor": None}


@pytest.fixture
def review_error_unsuccessful_response():
    """Error response when request is unsuccessful."""
    return {"success": 0, "query_summary": {"num_reviews": 0}, "reviews": [], "cursor": None}


@pytest.fixture
def review_empty_response():
    """Response when there are no reviews yet."""
    return {
        "success": 1,
        "query_summary": {
            "num_reviews": 0,
            "review_score": 0,
            "review_score_desc": "No user reviews",
            "total_positive": 0,
            "total_negative": 0,
            "total_reviews": 0,
        },
        "reviews": [],
        "cursor": "*",
    }


@pytest.fixture
def review_only_tchinese():
    """Response with only Traditional Chinese reviews."""
    return {
        "success": 1,
        "query_summary": {
            "num_reviews": 1,
            "review_score": 0,
            "total_positive": 0,
            "total_negative": 1,
            "total_reviews": 1,
        },
        "reviews": [
            {
                "recommendationid": "2",
                "author": {
                    "steamid": "2",
                    "num_games_owned": 1,
                    "num_reviews": 1,
                    "playtime_forever": 3,
                    "playtime_last_two_weeks": 0,
                    "playtime_at_review": 3,
                    "last_played": 12345,
                },
                "language": "tchinese",
                "review": "mock review but in tchinese",
                "voted_up": False,
            },
        ],
        "cursor": "*",
    }
