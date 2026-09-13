"""Redis 缓存客户端（复用 settings.redis 配置，业务缓存 db0，与 Arq 队列 db1 隔离）。"""
from redis.asyncio import Redis

from config.settings import settings

_redis: Redis | None = None


async def get_redis() -> Redis:
    """懒加载共享 Redis 客户端（decode_responses=True，存取 JSON 字符串更方便）。"""
    global _redis
    if _redis is None:
        _redis = Redis(
            host=settings.redis.host,
            port=settings.redis.port,
            db=settings.redis.db,
            password=settings.redis.password or None,
            decode_responses=True,
        )
    return _redis