import time
import warnings
from abc import ABC, abstractmethod
from typing import Any, Literal, TypedDict
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

from gameinsights.utils import LoggerWrapper


class SuccessResult(TypedDict):
    success: Literal[True]
    data: dict[str, Any]


class ErrorResult(TypedDict):
    success: Literal[False]
    error: str


SourceResult = SuccessResult | ErrorResult

# a custom error code for the synthetic response
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

    @staticmethod
    def close_session() -> None:
        """Deprecated. Session lifecycle is now managed by Collector.

        This method is a no-op. Use ``Collector.close()`` or the
        Collector as a context manager instead.
        """
        warnings.warn(
            "BaseSource.close_session() is deprecated and has no effect. "
            "Use Collector.close() or the Collector context manager instead.",
            DeprecationWarning,
            stacklevel=2,
        )

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
    ) -> SuccessResult | ErrorResult:
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
        method: Literal["GET", "POST"] = "GET",
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
            method (Literal["GET", "POST"]): HTTP method to use (default: "GET")
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

        # Prepare headers with User-Agent
        ua = UserAgent()
        if headers is None:
            headers = {"User-Agent": ua.random}
        else:
            # Only add User-Agent if not already present
            if "User-Agent" not in headers:
                headers = headers.copy()
                headers["User-Agent"] = ua.random

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
                if attempts < retries:
                    sleep_duration = backoff_factor * (2 ** (attempts - 1))  # the cooldown period
                    self.logger.log(
                        f"Encounter error {e}. Retrying in {sleep_duration: .1f}s. (Attempt {attempts+1} of {retries})",
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
        """Filter the selected labels to only include valid labels.

        Args:
            selected_labels (list[str]): A list of labels to filter.
            valid_labels (list[str] | tuple[str, ...] | None): Valid labels to compare with. If None, uses the class's valid labels.
        Returns:
            list[str]: A list of valid labels.
        """

        validation_set = (
            frozenset(valid_labels) if valid_labels is not None else self._valid_labels_set
        )

        valid: list[str] = []
        invalid: list[str] = []
        for label in selected_labels:
            (valid if label in validation_set else invalid).append(label)

        # log the invalid labels if any
        if invalid:
            reference_labels = valid_labels if valid_labels is not None else self._valid_labels
            self.logger.log(
                f"Ignoring the following invalid labels: {invalid}, valid labels are: {reference_labels}",
                level="warning",
                verbose=True,
            )

        return valid

    def _build_error_result(self, error_message: str, verbose: bool = True) -> ErrorResult:
        """Error message/returns handler.
        Args:
            error_message (str): Error Message.
            verbose (bool): If True, will log the error message. (Default to True)
        Returns:
            ErrorResult: A dictionary containing the ErrorResult.
        """
        self.logger.log(error_message, level="error", verbose=verbose)

        return ErrorResult(success=False, error=error_message)

    def _prepare_identifier(self, identifier: str, verbose: bool = True) -> str:
        """Convert identifier to string and log fetch start.

        Args:
            identifier: The game identifier (appid, name, etc.)
            verbose: Whether to log

        Returns:
            String representation of identifier
        """
        identifier_str = str(identifier)
        self.logger.log(
            f"Fetching data for appid {identifier_str}.",
            level="info",
            verbose=verbose,
        )
        return identifier_str

    def _fetch_and_parse_json(
        self,
        response: requests.Response,
        verbose: bool = True,
    ) -> dict[str, Any] | None:
        """Parse JSON response with error handling.

        Args:
            response: HTTP response object
            verbose: Whether to log errors

        Returns:
            Parsed JSON data, or None if request failed or parsing failed
        """
        if response.status_code != 200:
            return None

        try:
            data = response.json()
            # Type narrowing: requests.Response.json() returns Any, but we expect dict
            if isinstance(data, dict):
                return data
            return None
        except Exception:
            # Don't log here - let the caller build the error result
            # This allows custom error messages per source
            return None

    def _apply_label_filter(
        self,
        data: dict[str, Any],
        selected_labels: list[str] | None,
    ) -> dict[str, Any]:
        """Filter data by selected labels if provided.

        Args:
            data: The data dictionary to filter
            selected_labels: Labels to include (None = all labels)

        Returns:
            Filtered data dictionary
        """
        if selected_labels:
            return {
                label: data[label]
                for label in self._filter_valid_labels(selected_labels)
                if label in data
            }
        return data
