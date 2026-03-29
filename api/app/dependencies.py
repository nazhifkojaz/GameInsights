from fastapi import Request
from gameinsights.utils.gamesearch import GameSearch

from app.collector_pool import CollectorPool
from app.db_cache import DatabaseCache
from app.config import Settings


def get_pool(request: Request) -> CollectorPool:
    return request.app.state.pool


def get_cache(request: Request) -> DatabaseCache:
    return request.app.state.cache


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_game_search(request: Request) -> GameSearch:
    return request.app.state.game_search
