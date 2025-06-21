"""
API routes for news processing and post generation
"""
from .news import router as news_router
from .sessions import router as sessions_router
from .posts import router as posts_router

__all__ = ["news_router", "sessions_router", "posts_router"]
