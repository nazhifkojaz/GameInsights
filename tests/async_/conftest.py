"""Shared async test fixtures."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock

import pytest

from gameinsights.async_.base import _AsyncResponse


@pytest.fixture
def mock_async_request(monkeypatch):
    """Factory: patches AsyncBaseSource._make_request to return a fake _AsyncResponse.

    Usage:
        mock_async_request(TargetClass, status_code=200, json_data={...})
        mock_async_request(TargetClass, text_data="<html>...</html>")
        mock_async_request(TargetClass, side_effect=[
            {"status_code": 200, "json_data": {...}},
            {"status_code": 404},
        ])
    """

    def _patch(
        target_class: type,
        method_name: str = "_make_request",
        status_code: int = 200,
        json_data: dict[str, Any] | None = None,
        text_data: str | None = None,
        side_effect: list[dict[str, Any]] | None = None,
    ) -> AsyncMock:
        def _make_response(
            sc: int,
            jd: dict[str, Any] | None,
            td: str | None,
        ) -> _AsyncResponse:
            if jd is not None:
                body = json.dumps(jd).encode()
            else:
                body = (td or "").encode()
            return _AsyncResponse(status_code=sc, _body=body)

        if side_effect is not None:
            responses = [_make_response(d.get("status_code", 200), d.get("json_data"), d.get("text_data")) for d in side_effect]
            mock = AsyncMock(side_effect=responses)
        else:
            mock = AsyncMock(return_value=_make_response(status_code, json_data, text_data))

        monkeypatch.setattr(target_class, method_name, mock)
        return mock

    return _patch


@pytest.fixture
def stub_async_ratelimit(monkeypatch):
    """Disable async rate limiting in tests so they run at full speed."""
    from aiolimiter import AsyncLimiter

    import gameinsights.utils.async_ratelimit as rl_module

    # Replace AsyncLimiter with an unlimited one (max_rate=1e9)
    class _UnlimitedLimiter(AsyncLimiter):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(max_rate=1_000_000, time_period=1)

    monkeypatch.setattr(rl_module, "AsyncLimiter", _UnlimitedLimiter)
