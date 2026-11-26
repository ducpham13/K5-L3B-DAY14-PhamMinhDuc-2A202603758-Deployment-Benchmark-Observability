"""
Kết nối Redis dùng chung cho rate limiter và cost guard.
"""
import redis as redis_lib

from app.config import settings

r: redis_lib.Redis = redis_lib.from_url(settings.redis_url, decode_responses=True, socket_connect_timeout=2)


def redis_healthy() -> bool:
    try:
        return r.ping()
    except Exception:
        return False
