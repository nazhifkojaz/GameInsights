"""Fixtures for ProtonDB source tests."""

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
