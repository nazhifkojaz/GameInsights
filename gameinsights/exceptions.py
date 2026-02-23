"""Public exception hierarchy for gameinsights.

Raised at the Collector (public API boundary) so external wrappers
such as FastAPI can map them to HTTP status codes.

Internal source-layer code continues to use SuccessResult / ErrorResult
TypedDicts and must NOT import from this module.

HTTP mapping guide:
    GameNotFoundError           -> 404 Not Found
    SourceUnavailableError      -> 503 Service Unavailable
    InvalidRequestError         -> 422 Unprocessable Entity
    DependencyNotInstalledError -> 500 Internal Server Error
    GameInsightsError (base)    -> 500 Internal Server Error
"""

from __future__ import annotations


class GameInsightsError(Exception):
    """Base class for all gameinsights public exceptions."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class GameNotFoundError(GameInsightsError):
    """The game does not exist for the given Steam appid.

    Raised only when the primary source (SteamStore) confirms the appid
    is absent or unavailable in the requested region/language.
    """

    def __init__(self, appid: str, message: str | None = None) -> None:
        self.appid = appid
        super().__init__(message or f"Game with appid '{appid}' was not found.")


class SourceUnavailableError(GameInsightsError):
    """A data source is unreachable after all retries are exhausted.

    Covers: network errors, timeouts, SSL errors, TooManyRedirects,
    and non-200 HTTP responses from supplementary sources.
    """

    def __init__(self, source: str, reason: str) -> None:
        self.source = source
        self.reason = reason
        super().__init__(f"Source '{source}' is unavailable: {reason}")


class InvalidRequestError(GameInsightsError):
    """The caller passed invalid input to a public Collector method.

    Examples: empty appid string, unsupported parameter value.
    Replaces the bare ValueError previously raised by get_game_review().
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)


class DependencyNotInstalledError(GameInsightsError):
    """An optional dependency required for the called method is absent.

    Wraps ImportError from import_pandas() with a library-specific type
    so the API wrapper can return 500 (configuration error).
    """

    def __init__(self, package: str, install_extra: str) -> None:
        self.package = package
        self.install_extra = install_extra
        super().__init__(
            f"'{package}' is required for this operation. "
            f"Install it with: pip install gameinsights[{install_extra}]"
        )
