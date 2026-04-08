"""Tests for AsyncBaseSource and _AsyncResponse."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest  # noqa: F401

from gameinsights.async_.base import AsyncBaseSource, _AsyncResponse
from gameinsights.sources.base import SYNTHETIC_ERROR_CODE

# ---------------------------------------------------------------------------
# Concrete subclass for testing
# ---------------------------------------------------------------------------

class _ConcreteSource(AsyncBaseSource):
    _base_url = "https://example.com/api"
    _valid_labels = ("field_a", "field_b")
    _valid_labels_set = frozenset(_valid_labels)

    async def fetch(self, appid: str, verbose: bool = True, selected_labels: list[str] | None = None) -> Any:
        response = await self._make_request(endpoint=appid)
        data = self._fetch_and_parse_json(response, verbose)
        if data is None:
            return self._build_error_result(f"Failed for {appid}")
        return {"success": True, "data": self._transform_data(data)}

    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        return data


# ---------------------------------------------------------------------------
# _AsyncResponse tests
# ---------------------------------------------------------------------------

class TestAsyncResponse:
    def test_async_response_json_parses_body(self) -> None:
        payload = {"foo": "bar"}
        r = _AsyncResponse(status_code=200, _body=json.dumps(payload).encode())
        assert r.json() == payload

    def test_async_response_text_decodes_body(self) -> None:
        r = _AsyncResponse(status_code=200, _body=b"hello")
        assert r.text == "hello"

    def test_async_response_ok_true_for_2xx(self) -> None:
        assert _AsyncResponse(status_code=200, _body=b"").ok is True
        assert _AsyncResponse(status_code=201, _body=b"").ok is True

    def test_async_response_ok_false_for_4xx_5xx(self) -> None:
        assert _AsyncResponse(status_code=404, _body=b"").ok is False
        assert _AsyncResponse(status_code=500, _body=b"").ok is False

    def test_async_response_synthetic_error_code(self) -> None:
        r = _AsyncResponse(status_code=SYNTHETIC_ERROR_CODE, _body=b"")
        assert r.status_code == 599
        assert r.ok is False


# ---------------------------------------------------------------------------
# AsyncBaseSource._make_request tests
# ---------------------------------------------------------------------------

class TestAsyncMakeRequest:
    async def test_make_request_returns_response_on_success(self) -> None:
        src = _ConcreteSource()
        payload = {"result": 42}

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.url = "https://example.com/api/570"
        mock_resp.read = AsyncMock(return_value=json.dumps(payload).encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch.object(src.session, "get", return_value=mock_resp):
            result = await src._make_request(endpoint="570")

        assert result.status_code == 200
        assert result.json() == payload

    async def test_make_request_returns_synthetic_on_timeout(self) -> None:
        # asyncio.TimeoutError is in the retriable bucket
        src = _ConcreteSource()
        with patch.object(src.session, "get", side_effect=asyncio.TimeoutError()):
            result = await src._make_request(endpoint="570", retries=1, backoff_factor=0)

        assert result.status_code == SYNTHETIC_ERROR_CODE

    async def test_make_request_retries_on_retriable_error(self) -> None:
        # Verify retry loop: first call raises TimeoutError, second succeeds
        src = _ConcreteSource()
        payload = {"ok": True}

        success_resp = AsyncMock()
        success_resp.status = 200
        success_resp.reason = "OK"
        success_resp.url = "https://example.com/api/570"
        success_resp.read = AsyncMock(return_value=json.dumps(payload).encode())
        success_resp.__aenter__ = AsyncMock(return_value=success_resp)
        success_resp.__aexit__ = AsyncMock(return_value=False)

        call_count = 0

        def side_effect(*args: Any, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise asyncio.TimeoutError()
            return success_resp

        with patch.object(src.session, "get", side_effect=side_effect):
            result = await src._make_request(endpoint="570", retries=3, backoff_factor=0)

        assert result.status_code == 200
        assert call_count == 2

    async def test_make_request_returns_synthetic_on_unknown_error(self) -> None:
        # Unknown exceptions fall through to catch-all and return synthetic
        src = _ConcreteSource()
        with patch.object(src.session, "get", side_effect=RuntimeError("unexpected")):
            result = await src._make_request(endpoint="570")

        assert result.status_code == SYNTHETIC_ERROR_CODE

    async def test_make_request_uses_post_method(self) -> None:
        src = _ConcreteSource()
        payload = {"key": "val"}

        mock_resp = AsyncMock()
        mock_resp.status = 200
        mock_resp.reason = "OK"
        mock_resp.url = "https://example.com/api/"
        mock_resp.read = AsyncMock(return_value=json.dumps(payload).encode())
        mock_resp.__aenter__ = AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = AsyncMock(return_value=False)

        with patch.object(src.session, "post", return_value=mock_resp) as mock_post:
            result = await src._make_request(method="POST", json={"q": "dota"})

        mock_post.assert_called_once()
        assert result.status_code == 200


# ---------------------------------------------------------------------------
# Pure helper method tests
# ---------------------------------------------------------------------------

class TestPureHelpers:
    def test_build_error_result(self) -> None:
        src = _ConcreteSource()
        result = src._build_error_result("something failed", verbose=False)
        assert result["success"] is False
        assert result["error"] == "something failed"

    def test_fetch_and_parse_json_returns_dict(self) -> None:
        src = _ConcreteSource()
        r = _AsyncResponse(200, json.dumps({"a": 1}).encode())
        assert src._fetch_and_parse_json(r) == {"a": 1}

    def test_fetch_and_parse_json_returns_none_for_non_200(self) -> None:
        src = _ConcreteSource()
        r = _AsyncResponse(404, b"")
        assert src._fetch_and_parse_json(r) is None

    def test_fetch_and_parse_json_returns_none_for_non_dict(self) -> None:
        src = _ConcreteSource()
        r = _AsyncResponse(200, json.dumps([1, 2, 3]).encode())
        assert src._fetch_and_parse_json(r) is None

    def test_apply_label_filter_filters_correctly(self) -> None:
        src = _ConcreteSource()
        data = {"field_a": 1, "field_b": 2, "other": 3}
        filtered = src._apply_label_filter(data, ["field_a"])
        assert filtered == {"field_a": 1}

    def test_apply_label_filter_returns_all_when_none(self) -> None:
        src = _ConcreteSource()
        data = {"field_a": 1, "field_b": 2}
        assert src._apply_label_filter(data, None) == data
