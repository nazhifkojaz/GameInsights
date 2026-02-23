"""Common test fixtures shared across multiple test files."""

import pytest


@pytest.fixture
def common_http_error_response():
    """Generic HTTP error response pattern for source failures.

    Use this fixture when mocking sources that return HTTP errors.
    """
    return {
        "success": False,
        "error": "Failed to fetch data. Status code: 500",
    }


@pytest.fixture
def common_not_found_response():
    """Generic "not found" error response pattern.

    Use this fixture when mocking sources that return 404/not found errors.
    """
    return {
        "success": False,
        "error": "Game with appid {appid} is not found.",
    }


@pytest.fixture
def common_timeout_response():
    """Generic timeout error response pattern.

    Use this fixture when mocking sources that timeout.
    """
    return {
        "success": False,
        "error": "Request timeout",
    }


@pytest.fixture
def common_connection_error_response():
    """Generic connection error response pattern.

    Use this fixture when mocking sources that fail to connect.
    """
    return {
        "success": False,
        "error": "Failed to connect",
    }


@pytest.fixture
def common_unexpected_field_data():
    """Data with unexpected field names for robustness testing.

    Use this fixture to test that sources handle unexpected fields gracefully.
    """
    return {
        "wrong_key": "value",
        "another_wrong": 123,
        "unexpected_field": "should be ignored",
    }


@pytest.fixture
def common_empty_response():
    """Generic empty response pattern.

    Use this fixture when mocking sources that return no data.
    """
    return {
        "success": True,
        "data": {},
    }


@pytest.fixture
def common_rate_limit_response():
    """Rate limit error response pattern.

    Use this fixture when testing rate limit handling.
    """
    return {
        "success": False,
        "error": "Rate limit exceeded. Please try again later.",
    }
