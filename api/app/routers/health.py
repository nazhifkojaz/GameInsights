from fastapi import APIRouter, Depends
from typing import Any
from app.dependencies import get_pool, get_settings
from app.collector_pool import CollectorPool
from app.config import Settings
from app.schemas.health import HealthCheckResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("", response_model=HealthCheckResponse)
async def health_check(
    pool: CollectorPool = Depends(get_pool),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return {
        "status": "ok",
        "api_title": settings.api_title,
        "api_version": settings.api_version,
        "pool_size": pool.size,
        "pool_available": pool.available,
    }
