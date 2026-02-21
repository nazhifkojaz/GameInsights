"""Shared test fixtures and imports for all test modules."""

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
    ):
        class Response:
            def __init__(self, status_code, json_data, text_data):
                self.status_code = status_code
                self.ok = 200 <= status_code < 300
                self._json = json_data
                self._text = text_data or ""
                self.reason = "Mock Reason"

            def json(self):
                return self._json

            @property
            def text(self):
                return self._text

            def raise_for_status(self):
                if not self.ok:
                    raise requests.HTTPError(f"Mock error {self.status_code}")

        def make_response_from_dict(d):
            return Response(d.get("status_code", 200), d.get("json_data"), d.get("text_data"))

        if side_effect:
            # now it takes either exception or dict
            responses = [
                e if isinstance(e, Exception) else make_response_from_dict(e) for e in side_effect
            ]
            mock_method = Mock(side_effect=responses)
        else:
            mock_method = Mock(return_value=Response(status_code, json_data, text_data))

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

        source = source_cls(**(instantiate_kwargs or {}))
        target_method = getattr(source, method)
        return target_method(**(call_kwargs or {}))

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
