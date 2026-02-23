"""Shared test fixtures and imports for all test modules."""

import json
from unittest.mock import Mock

import pytest
import requests

# Import all fixtures from tests/fixtures/ directory
# Pytest will automatically make these available to all tests
from tests.fixtures.gamalytic_fixtures import *  # noqa: F403
from tests.fixtures.hltb_fixtures import *  # noqa: F403
from tests.fixtures.model_fixtures import *  # noqa: F403
from tests.fixtures.protondb_fixtures import *  # noqa: F403
from tests.fixtures.steamachievements_fixtures import *  # noqa: F403
from tests.fixtures.steamcharts_fixtures import *  # noqa: F403
from tests.fixtures.steamreview_fixtures import *  # noqa: F403
from tests.fixtures.steamspy_fixtures import *  # noqa: F403
from tests.fixtures.steamstore_fixtures import *  # noqa: F403
from tests.fixtures.steamuser_fixtures import *  # noqa: F403


@pytest.fixture
def mock_request_response(monkeypatch):
    """Factory fixture to mock a response and patch _make_request in the target class"""

    def _patch_method(
        target_class,
        method_name: str | None = None,
        status_code: int = 200,
        json_data: dict | None = None,
        text_data: str | None = None,
        side_effect: list | None = None,
        json_raises: type[Exception] | None = None,
    ):
        class Response:
            def __init__(self, status_code, json_data, text_data, json_raises):
                self.status_code = status_code
                self.ok = 200 <= status_code < 300
                self._json = json_data
                self._text = text_data or ""
                self.reason = "Mock Reason"
                self._json_raises = json_raises

            def json(self):
                if self._json_raises:
                    if isinstance(self._json_raises, Exception):
                        raise self._json_raises
                    if issubclass(self._json_raises, json.JSONDecodeError):
                        raise self._json_raises("Invalid JSON", "", 0)
                    raise self._json_raises("Invalid JSON")
                return self._json

            @property
            def text(self):
                return self._text

            def raise_for_status(self):
                if not self.ok:
                    raise requests.HTTPError(f"Mock error {self.status_code}")

        def make_response_from_dict(d):
            return Response(
                d.get("status_code", 200),
                d.get("json_data"),
                d.get("text_data"),
                d.get("json_raises"),
            )

        if side_effect:
            # now it takes either exception or dict
            responses = [
                e if isinstance(e, Exception) else make_response_from_dict(e) for e in side_effect
            ]
            mock_method = Mock(side_effect=responses)
        else:
            mock_method = Mock(
                return_value=Response(status_code, json_data, text_data, json_raises)
            )

        target_method_names: list[str] = []
        if method_name is not None:
            target_method_names.append(method_name)
        else:
            if hasattr(target_class, "_fetch_search_results"):
                target_method_names.append("_fetch_search_results")
            target_method_names.append("_make_request")

        for name in target_method_names:
            if hasattr(target_class, name):
                monkeypatch.setattr(target_class, name, mock_method)

        return mock_method

    return _patch_method


@pytest.fixture
def stub_ratelimit(monkeypatch):
    import gameinsights.utils.ratelimit as ratelimit_module

    class StubRateLimitException(Exception):
        def __init__(self, message="rate limit exceeded", period_remaining=0.0):
            super().__init__(message)
            self.period_remaining = period_remaining

    class StubLimiter:
        def __init__(self):
            self.limits_invocations = 0

        def limits(self, *, calls: int, period: int):
            self.limits_invocations += 1
            state = {"count": 0}

            def decorator(func):
                def wrapped(*args, **kwargs):
                    if state["count"] >= calls:
                        state["count"] = 0
                        raise StubRateLimitException("Rate limit exceeded", float(period))
                    state["count"] += 1
                    return func(*args, **kwargs)

                return wrapped

            return decorator

    stub = StubLimiter()
    monkeypatch.setattr(ratelimit_module, "RateLimitException", StubRateLimitException)
    monkeypatch.setattr(ratelimit_module, "limits", stub.limits)

    return stub


@pytest.fixture
def source_fetcher(mock_request_response):
    """Helper fixture to streamline source method calls with mocked responses."""

    def _call(
        source_cls,
        *,
        method: str = "fetch",
        mock_kwargs: dict | None = None,
        instantiate_kwargs: dict | None = None,
        call_kwargs: dict | None = None,
        status_code: int = 200,
    ):
        mock_options = dict(mock_kwargs or {})
        if "status_code" in mock_options or "side_effect" in mock_options:
            mock_request_response(
                target_class=source_cls,
                **mock_options,
            )
        else:
            mock_request_response(
                target_class=source_cls,
                status_code=status_code,
                **mock_options,
            )

        # Inject a session if the caller did not supply one.
        kwargs = {**(instantiate_kwargs or {})}
        created_session = None
        if kwargs.get("session") is None:
            created_session = requests.Session()
            kwargs["session"] = created_session

        try:
            source = source_cls(**kwargs)
            target_method = getattr(source, method)
            return target_method(**(call_kwargs or {}))
        finally:
            if created_session is not None:
                created_session.close()

    return _call


@pytest.fixture
def collector_with_mocks(mock_request_response, monkeypatch, request):
    """Collector instance wired with mocked sources for integration-style tests."""
    from gameinsights.collector import Collector
    from gameinsights.sources import (
        Gamalytic,
        HowLongToBeat,
        ProtonDB,
        SteamAchievements,
        SteamCharts,
        SteamReview,
        SteamSpy,
        SteamStore,
    )

    # Mock the HowLongToBeat token method
    def mock_get_token(*args, **kwargs):
        return "mock_token"

    monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

    sources_payloads = [
        (
            Gamalytic,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("gamalytic_success_response_data")
                }
            },
        ),
        (
            HowLongToBeat,
            {"mock_kwargs": {"text_data": request.getfixturevalue("hltb_success_response_data")}},
        ),
        (
            ProtonDB,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("protondb_success_response_data")
                }
            },
        ),
        (
            SteamAchievements,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("achievements_success_response_data")
                }
            },
        ),
        (
            SteamCharts,
            {
                "mock_kwargs": {
                    "text_data": request.getfixturevalue("steamcharts_success_response_data")
                }
            },
        ),
        (
            SteamReview,
            {"mock_kwargs": {"json_data": request.getfixturevalue("review_only_tchinese")}},
        ),
        (
            SteamSpy,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("steamspy_success_response_data")
                }
            },
        ),
        (
            SteamStore,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("steamstore_success_response_data")
                }
            },
        ),
    ]

    for source_cls, kwargs in sources_payloads:
        mock_request_response(target_class=source_cls, **kwargs["mock_kwargs"])

    return Collector()


@pytest.fixture
def collector_with_one_failed_source(mock_request_response, monkeypatch, request):
    """Collector with one mocked source failing to test resilience.

    This fixture mocks all sources to succeed except SteamCharts, which returns
    a 500 error. This allows testing that the collector continues collecting data
    from successful sources even when one fails.
    """
    from gameinsights.collector import Collector
    from gameinsights.sources import (
        Gamalytic,
        HowLongToBeat,
        ProtonDB,
        SteamAchievements,
        SteamCharts,
        SteamReview,
        SteamSpy,
        SteamStore,
    )

    # Mock the HowLongToBeat token method
    def mock_get_token(*args, **kwargs):
        return "mock_token"

    monkeypatch.setattr(HowLongToBeat, "_get_search_token", mock_get_token)

    sources_payloads = [
        (
            Gamalytic,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("gamalytic_success_response_data")
                }
            },
        ),
        (
            HowLongToBeat,
            {"mock_kwargs": {"text_data": request.getfixturevalue("hltb_success_response_data")}},
        ),
        (
            ProtonDB,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("protondb_success_response_data")
                }
            },
        ),
        (
            SteamAchievements,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("achievements_success_response_data")
                }
            },
        ),
        # SteamCharts FAILS with 500 error
        (
            SteamCharts,
            {"mock_kwargs": {"status_code": 500, "text_data": "Internal Server Error"}},
        ),
        (
            SteamReview,
            {"mock_kwargs": {"json_data": request.getfixturevalue("review_only_tchinese")}},
        ),
        (
            SteamSpy,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("steamspy_success_response_data")
                }
            },
        ),
        (
            SteamStore,
            {
                "mock_kwargs": {
                    "json_data": request.getfixturevalue("steamstore_success_response_data")
                }
            },
        ),
    ]

    for source_cls, kwargs in sources_payloads:
        mock_request_response(target_class=source_cls, **kwargs["mock_kwargs"])

    return Collector()


@pytest.fixture
def without_pandas(monkeypatch):
    """Mock context that prevents pandas from being imported.

    Use this fixture to test behavior when pandas is not installed.
    This replaces the duplicate mock_import pattern across multiple test files.

    Clears sys.modules["pandas"] so the import hook is actually triggered
    even if pandas was already imported in this process.
    """
    import builtins
    import sys
    from unittest.mock import patch

    # Remove cached pandas module so Python calls __import__ instead of
    # returning the cached module from sys.modules.
    monkeypatch.delitem(sys.modules, "pandas", raising=False)

    original_import = builtins.__import__

    def mock_import(name, *args, **kwargs):
        if name == "pandas":
            raise ImportError("No module named 'pandas'")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=mock_import):
        yield


# Test helper functions


def assert_list_not_tuple(data, expected_len=None):
    """Helper to assert data is a list (not tuple) and optionally check length.

    Args:
        data: The data to check
        expected_len: Optional expected length of the list

    Raises:
        AssertionError: If data is not a list, is a tuple, or length doesn't match
    """
    assert isinstance(data, list), f"Expected list, got {type(data)}"
    assert not isinstance(data, tuple), "Data should not be a tuple"
    if expected_len is not None:
        assert len(data) == expected_len, f"Expected length {expected_len}, got {len(data)}"


def assert_fetch_result(
    result,
    identifier,
    success=True,
    data_not_none=True,
    error_is_none=True,
):
    """Helper to assert FetchResult properties.

    Args:
        result: The FetchResult to validate
        identifier: Expected identifier value
        success: Expected success status (default True)
        data_not_none: Whether data should be not None (default True)
        error_is_none: Whether error should be None (default True)

    Raises:
        AssertionError: If any assertion fails
    """
    from gameinsights.collector import FetchResult

    assert isinstance(result, FetchResult), f"Expected FetchResult, got {type(result)}"
    assert (
        result.identifier == identifier
    ), f"Expected identifier '{identifier}', got '{result.identifier}'"
    assert result.success is success, f"Expected success={success}, got {result.success}"
    if data_not_none:
        assert result.data is not None, "Expected data to not be None"
    if error_is_none:
        assert result.error is None, f"Expected error to be None, got: {result.error}"
