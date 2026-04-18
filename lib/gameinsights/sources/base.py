import time
from abc import ABC, abstractmethod
from typing import Any, Generic, Literal, TypedDict, TypeVar
from urllib.parse import urljoin

import requests
from fake_useragent import UserAgent
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    ConnectionError,
    InvalidURL,
    RequestException,
    SSLError,
    Timeout,
    TooManyRedirects,
)

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
from gameinsights.utils import LoggerWrapper

T = TypeVar("T")


class SuccessResult(TypedDict, Generic[T]):
    success: Literal[True]
    data: T


class ErrorResult(TypedDict):
    success: Literal[False]
    error: str


SourceResult = SuccessResult[dict[str, Any]] | ErrorResult

SYNTHETIC_ERROR_CODE = 599


class BaseSource(ABC):
    _base_url: str | None = None

    def __init__(self, session: requests.Session | None = None) -> None:
        """Initialize the base class for all its children.

        Args:
            session: An existing requests.Session to reuse. When None (the
                     default), a new session is created lazily on first access
                     via the ``session`` property. Passing a shared session
                     enables connection pooling across multiple source instances
                     owned by the same Collector.
        """
        self._logger = LoggerWrapper(self.__class__.__name__)
        self._session = session
        self._ua = UserAgent()

    @property
    def logger(self) -> "LoggerWrapper":
        return self._logger

    @property
    def session(self) -> requests.Session:
        """Get or create a session with connection pooling.

        If a session was injected via the constructor, it is returned directly.
        Otherwise a new session is created lazily and cached on this instance,
        enabling standalone use of any source outside a Collector.
        """
        if self._session is None:
            self._session = requests.Session()
            adapter = HTTPAdapter(
                pool_connections=10,  # Number of connection pools to cache
                pool_maxsize=20,  # Maximum number of connections per pool
            )
            self._session.mount("https://", adapter)
            self._session.mount("http://", adapter)
        return self._session

    @property
    @abstractmethod
    def _valid_labels(self) -> tuple[str, ...]:
        """Get the valid labels for the data fetched from the source."""
        pass

    @property
    @abstractmethod
    def _valid_labels_set(self) -> frozenset[str]:
        """Get the valid labels as a frozenset for quick membership testing."""
        pass

    @property
    def valid_labels(self) -> tuple[str, ...]:
        """Get the valid labels for the data fetched from the source."""
        return self._valid_labels

    @abstractmethod
    def fetch(
        self, appid: str, verbose: bool = True, selected_labels: list[str] | None = None
    ) -> SourceResult:
        """Abstract method to fetch data from the source.

        Args:
            appid (str): The appid of the game to fetch data for.
            verbose (bool): If True, will log the fetching process.
            selected_labels (list[str] | None): A list of labels to filter the data.

        Returns:
            SuccessResult | ErrorResult: A dictionary containing the status, data, or any error message if applicable.
        """
        pass

    def _make_request(
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
    ) -> requests.Response:
        """Default implementation for request.

        Args:
            url (str): Optional url if _base_url is not set
            endpoint (str): Optional path to append to base URL (e.g., steam_appid)
            headers (dict | None): Optional headers dictionary
            params (dict | None): Optional query parameters dictionary
            json (dict | None): Optional JSON body for POST requests (auto-serialized)
            data (str | bytes | None): Optional raw body for POST requests
            method (HttpMethod): HTTP method to use (default: "GET")
            retries (int): Max number of retries
            backoff_factor (float): Multiplier for sleep/cooldown between retries
            timeout (float | tuple): Request timeout in seconds

        Return:
            requests.Response: The response of the request call.
        """
        source_url = url if url else self._base_url
        final_url = source_url.rstrip("/")  # type: ignore[union-attr]
        if endpoint:
            final_url = urljoin(final_url + "/", endpoint.rstrip("/"))

        if headers is None:
            headers = {"User-Agent": self._ua.random}
        else:
            if "User-Agent" not in headers:
                headers = headers.copy()
                headers["User-Agent"] = self._ua.random

        exception_to_retry = (ConnectionError, Timeout)
        exception_to_abort = (
            InvalidURL,
            SSLError,
            TooManyRedirects,
        )

        for attempts in range(1, retries + 2):
            try:
                if method == "GET":
                    return self.session.get(
                        final_url, headers=headers, params=params, timeout=timeout
                    )
                else:  # POST
                    return self.session.post(
                        final_url,
                        headers=headers,
                        params=params,
                        json=json,
                        data=data,
                        timeout=timeout,
                    )
            except exception_to_retry as e:
                if attempts <= retries:
                    sleep_duration = backoff_factor * (2 ** (attempts - 1))  # the cooldown period
                    self.logger.log(
                        f"Encounter error {e}. Retrying in {sleep_duration: .1f}s. (Retry {attempts} of {retries})",
                        level="warning",
                        verbose=True,
                    )
                    time.sleep(sleep_duration)
                    continue
                else:
                    return self._create_synthetic_response(url=final_url, reason=str(e))
            except exception_to_abort as e:
                self.logger.log(
                    f"Encounter fatal error {e}. Abort process..",
                    level="error",
                    verbose=True,
                )
                return self._create_synthetic_response(url=final_url, reason=str(e))
            except RequestException as e:
                self.logger.log(
                    f"Encounter unknown error {e}. Abort process..",
                    level="error",
                    verbose=True,
                )
                return self._create_synthetic_response(url=final_url, reason=str(e))

        return self._create_synthetic_response(url=final_url, reason="unexpected request error")

    def _create_synthetic_response(self, url: str, reason: str) -> requests.Response:
        """create a synthetic response to return"""
        response = requests.Response()
        response.status_code = SYNTHETIC_ERROR_CODE
        response._content = b""
        response.url = url
        response.reason = reason
        response.headers = {}  # type: ignore[assignment]
        return response

    @abstractmethod
    def _transform_data(self, data: dict[str, Any]) -> dict[str, Any]:
        """Repack and transform the data fetched from the source."""
        pass

    def _filter_valid_labels(
        self, selected_labels: list[str], valid_labels: list[str] | tuple[str, ...] | None = None
    ) -> list[str]:
        return _filter_valid_labels(
            selected_labels,
            valid_labels=valid_labels,
            class_valid_labels_set=self._valid_labels_set,
            class_valid_labels=self._valid_labels,
            log_fn=self.logger.log,
        )

    def _build_error_result(self, error_message: str, verbose: bool = True) -> ErrorResult:
        return _build_error_result(error_message, self.logger.log, verbose)

    def _prepare_identifier(self, identifier: str, verbose: bool = True) -> str:
        return _prepare_identifier(identifier, self.logger.log, verbose)

    def _fetch_and_parse_json(
        self,
        response: requests.Response,
    ) -> dict[str, Any] | None:
        return _fetch_and_parse_json(response)

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
