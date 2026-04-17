"""Async base class for all async sources."""

from __future__ import annotations

import asyncio
import json as json_module
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin

import aiohttp
from fake_useragent import UserAgent

from gameinsights._types import HttpMethod
from gameinsights.sources._helpers import (
    apply_label_filter as _apply_label_filter,
)
from gameinsights.sources._helpers import (
    build_error_result as _build_error_result,
)
from gameinsights.sources._helpers import (
    fetch_and_parse_json as _fetch_and_parse_json,
)
from gameinsights.sources._helpers import (
    filter_valid_labels as _filter_valid_labels,
)
from gameinsights.sources._helpers import (
    prepare_identifier as _prepare_identifier,
)
from gameinsights.sources.base import (
    SYNTHETIC_ERROR_CODE,
    ErrorResult,
    SuccessResult,
)
from gameinsights.utils import LoggerWrapper


@dataclass
class _AsyncResponse:
    """Consumed HTTP response for use in sync downstream code.

    Wraps an aiohttp response whose body has already been read, exposing the
    same attributes that sources read from requests.Response (.status_code,
    .json(), .text, .ok, .url, .reason).
    """

    status_code: int
    _body: bytes = field(repr=False)
    url: str = ""
    reason: str = ""

    def json(self) -> Any:
        return json_module.loads(self._body)

    @property
    def text(self) -> str:
        return self._body.decode(errors="replace")

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 300


class AsyncBaseSource(ABC):
    """Abstract base for all async sources.

    Provides an async _make_request() backed by aiohttp with the same retry
    logic, backoff, and synthetic-599 error contract as the sync BaseSource.
    """

    _base_url: str | None = None

    def __init__(self, session: aiohttp.ClientSession | None = None) -> None:
        self._logger = LoggerWrapper(self.__class__.__name__)
        self._session = session
        self._ua = UserAgent()

    @property
    def logger(self) -> LoggerWrapper:
        return self._logger

    @property
    def session(self) -> aiohttp.ClientSession:
        """Lazily create a ClientSession for standalone source use.

        When used inside AsyncCollector the session is injected via __init__,
        so this property is only exercised in standalone / test scenarios.
        """
        if self._session is None:
            connector = aiohttp.TCPConnector(limit=20, limit_per_host=10)
            self._session = aiohttp.ClientSession(connector=connector)
        return self._session

    async def close(self) -> None:
        """Close the underlying aiohttp session if we own it."""
        if self._session is not None and not self._session.closed:
            await self._session.close()

    # ------------------------------------------------------------------
    # Core HTTP method
    # ------------------------------------------------------------------

    async def _make_request(
        self,
        url: str | None = None,
        endpoint: str | None = None,
        headers: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        data: str | bytes | None = None,
        method: HttpMethod = "GET",
        retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: float | tuple[float, float] = (30, 60),
    ) -> _AsyncResponse:
        """Async HTTP request with retry/backoff — mirrors BaseSource._make_request.

        Returns an _AsyncResponse (or a synthetic-599 _AsyncResponse on failure).
        Never raises.
        """
        source_url = url if url else self._base_url
        final_url = source_url.rstrip("/")  # type: ignore[union-attr]
        if endpoint:
            final_url = urljoin(final_url + "/", endpoint.rstrip("/"))

        if headers is None:
            headers = {"User-Agent": self._ua.random}
        elif "User-Agent" not in headers:
            headers = headers.copy()
            headers["User-Agent"] = self._ua.random

        if isinstance(timeout, tuple):
            connect_t, total_t = timeout
            aio_timeout = aiohttp.ClientTimeout(connect=connect_t, total=total_t)
        else:
            aio_timeout = aiohttp.ClientTimeout(total=timeout)

        # Fatal exceptions must be checked before retriable because ClientSSLError
        # inherits from ClientConnectorError (Python catches the first matching clause).
        fatal = (
            aiohttp.ClientSSLError,
            aiohttp.TooManyRedirects,
            aiohttp.InvalidUrlClientError,
        )
        retriable = (aiohttp.ClientConnectorError, asyncio.TimeoutError)

        for attempt in range(1, retries + 2):
            try:
                request_kwargs: dict[str, Any] = {
                    "headers": headers,
                    "params": params,
                    "timeout": aio_timeout,
                }
                if method == "POST":
                    if json is not None:
                        request_kwargs["json"] = json
                    elif data is not None:
                        request_kwargs["data"] = data

                async with (
                    self.session.get(final_url, **request_kwargs)
                    if method == "GET"
                    else self.session.post(final_url, **request_kwargs)
                ) as resp:
                    body = await resp.read()
                    return _AsyncResponse(
                        status_code=resp.status,
                        _body=body,
                        url=str(resp.url),
                        reason=resp.reason or "",
                    )

            except fatal as e:
                self.logger.log(
                    f"Encounter fatal error {e}. Abort process..",
                    level="error",
                    verbose=True,
                )
                return self._create_synthetic_response(url=final_url, reason=str(e))

            except retriable as e:
                if attempt <= retries:
                    sleep_duration = backoff_factor * (2 ** (attempt - 1))
                    self.logger.log(
                        f"Encounter error {e}. Retrying in {sleep_duration:.1f}s. "
                        f"(Retry {attempt} of {retries})",
                        level="warning",
                        verbose=True,
                    )
                    await asyncio.sleep(sleep_duration)
                    continue
                return self._create_synthetic_response(url=final_url, reason=str(e))

            except Exception as e:
                self.logger.log(
                    f"Encounter unknown error {e}. Abort process..",
                    level="error",
                    verbose=True,
                )
                return self._create_synthetic_response(url=final_url, reason=str(e))

        return self._create_synthetic_response(url=final_url, reason="unexpected request error")

    def _create_synthetic_response(self, url: str, reason: str) -> _AsyncResponse:
        return _AsyncResponse(
            status_code=SYNTHETIC_ERROR_CODE,
            _body=b"",
            url=url,
            reason=reason,
        )

    # ------------------------------------------------------------------
    # Pure helpers — identical logic to BaseSource, no async required
    # ------------------------------------------------------------------

    def _build_error_result(self, error_message: str, verbose: bool = True) -> ErrorResult:
        return _build_error_result(error_message, self.logger.log, verbose)

    def _prepare_identifier(self, identifier: str, verbose: bool = True) -> str:
        return _prepare_identifier(identifier, self.logger.log, verbose)

    def _fetch_and_parse_json(
        self,
        response: _AsyncResponse,
        verbose: bool = True,
    ) -> dict[str, Any] | None:
        return _fetch_and_parse_json(
            response, verbose, extra_json_exceptions=(aiohttp.ContentTypeError,)
        )

    def _filter_valid_labels(
        self,
        selected_labels: list[str],
        valid_labels: list[str] | tuple[str, ...] | None = None,
    ) -> list[str]:
        return _filter_valid_labels(
            selected_labels,
            valid_labels=valid_labels,
            class_valid_labels_set=self._valid_labels_set,
            class_valid_labels=self._valid_labels,
            log_fn=self.logger.log,
        )

    def _apply_label_filter(
        self,
        data: dict[str, Any],
        selected_labels: list[str] | None,
    ) -> dict[str, Any]:
        if not selected_labels:
            return data
        return _apply_label_filter(
            data, selected_labels, self._filter_valid_labels(selected_labels)
        )

    # ------------------------------------------------------------------
    # Abstract interface
    # ------------------------------------------------------------------

    @property
    @abstractmethod
    def _valid_labels(self) -> tuple[str, ...]:
        pass

    @property
    @abstractmethod
    def _valid_labels_set(self) -> frozenset[str]:
        pass

    @abstractmethod
    async def fetch(
        self,
        appid: str,
        verbose: bool = True,
        selected_labels: list[str] | None = None,
    ) -> SuccessResult[dict[str, Any]] | ErrorResult:
        pass

    @abstractmethod
    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        pass
