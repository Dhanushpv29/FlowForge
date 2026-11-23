from functools import lru_cache

from redis import Redis

from flowforge.core.config import get_settings
from flowforge.db.session import get_db

__all__ = ["get_db", "get_redis"]


@lru_cache
def get_redis() -> Redis:
    """Shared Redis client. Short timeouts so a dead Redis cannot hang requests."""
    return Redis.from_url(
        get_settings().redis_url, socket_connect_timeout=1, socket_timeout=1, decode_responses=True
    )
