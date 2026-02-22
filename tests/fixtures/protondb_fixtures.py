"""Fixtures for ProtonDB source tests.

The ProtonDB API endpoint is:
    https://www.protondb.com/api/v1/reports/summaries/{appid}.json

Fixture Verification (2026-02-21):
    - Verified against real API responses for appids: 570 (TF2), 730 (CS2), 413150 (Stardew Valley)
    - All field names match the current API response structure
    - TODO: Re-verify if ProtonDB API changes are announced
"""

import pytest


@pytest.fixture
def protondb_success_response_data():
    """Success JSON response for ProtonDB API with platinum tier."""
    return {
        "bestReportedTier": "platinum",
        "confidence": "strong",
        "score": 0.85,
        "tier": "platinum",
        "total": 323,
        "trendingTier": "platinum",
    }


@pytest.fixture
def protondb_gold_tier_response_data():
    """JSON response for ProtonDB API with gold tier."""
    return {
        "bestReportedTier": "gold",
        "confidence": "good",
        "score": 0.75,
        "tier": "gold",
        "total": 150,
        "trendingTier": "silver",
    }


@pytest.fixture
def protondb_not_found_response_data():
    """Empty response body for 404 case."""
    return "Game not found"


@pytest.fixture
def protondb_no_data_response_data():
    """JSON response when game exists but has no tier (e.g., pending/borked)."""
    return {
        "bestReportedTier": "pending",
        "confidence": "inadequate",
        "score": 0.0,
        "tier": None,
        "total": 0,
        "trendingTier": None,
    }


@pytest.fixture
def protondb_server_error_response_data():
    """Server error response (500 Internal Server Error)."""
    return "Internal Server Error"


@pytest.fixture
def protondb_malformed_json_response_data():
    """Malformed JSON response (invalid JSON - returns HTML instead)."""
    return "<html>Error</html>"


@pytest.fixture
def protondb_partial_response_data():
    """Response with missing optional fields (score/trending = None).

    Tests that _transform_data handles partial API responses gracefully,
    returning None for missing fields instead of raising errors.
    """
    return {
        "bestReportedTier": "pending",
        "confidence": "inadequate",
        # "score": missing - should become None
        "tier": None,
        "total": 0,
        # "trendingTier": missing - should become None
    }
