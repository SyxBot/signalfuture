from fastapi import Request

from cache.sqlite_cache import SQLiteCache
from services.filter_engine import FilterEngine
from services.token_feed import TokenFeedService


def get_cache(request: Request) -> SQLiteCache:
    return request.app.state.cache


def get_filter_engine(request: Request) -> FilterEngine:
    return request.app.state.filter_engine


def get_feed_service(request: Request) -> TokenFeedService:
    return request.app.state.feed_service
