from fastapi import Request
from app.collector_pool import CollectorPool
from app.cache import ResponseCache
from app.config import Settings


def get_pool(request: Request) -> CollectorPool:
    return request.app.state.pool


def get_cache(request: Request) -> ResponseCache:
    return request.app.state.cache


def get_settings(request: Request) -> Settings:
    return request.app.state.settings
