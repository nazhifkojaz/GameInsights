from pydantic import BaseModel


class HealthCheckResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str
    api_title: str
    api_version: str
    pool_size: int
    pool_available: int
