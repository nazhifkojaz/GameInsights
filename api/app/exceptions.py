from fastapi import Request
from fastapi.responses import JSONResponse
from gameinsights import (
    GameInsightsError,
    GameNotFoundError,
    SourceUnavailableError,
    InvalidRequestError,
    DependencyNotInstalledError,
)

_EXCEPTION_MAP: dict[type[GameInsightsError], tuple[int, str]] = {
    GameNotFoundError: (404, "not_found"),
    InvalidRequestError: (422, "invalid_request"),
    SourceUnavailableError: (503, "source_unavailable"),
    DependencyNotInstalledError: (500, "dependency_error"),
}


async def gameinsights_exception_handler(
    request: Request, exc: GameInsightsError
) -> JSONResponse:
    status_code, error_type = _EXCEPTION_MAP.get(type(exc), (500, "internal_error"))
    body: dict = {"error": error_type, "message": str(exc)}

    if isinstance(exc, GameNotFoundError):
        body["identifier"] = exc.identifier
    elif isinstance(exc, SourceUnavailableError):
        body["source"] = exc.source

    return JSONResponse(status_code=status_code, content=body)
