from app.routers.games import router as games_router
from app.routers.users import router as users_router
from app.routers.health import router as health_router

__all__ = ["games_router", "users_router", "health_router"]
