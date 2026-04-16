from pydantic import BaseModel


class ErrorResponse(BaseModel):
    error: str
    message: str
    identifier: str | None = None
    source: str | None = None
