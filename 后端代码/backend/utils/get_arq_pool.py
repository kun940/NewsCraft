from arq import create_pool
from arq.connections import ArqRedis, RedisSettings

from config.settings import settings

_arq_pool: ArqRedis | None = None

async def get_arq_pool() -> ArqRedis:
    """懒加载共享 Arq 连接池（首个请求时创建，进程内复用）。"""
    global _arq_pool
    if _arq_pool is None:
        _arq_pool = await create_pool(RedisSettings.from_dsn(settings.tasks.arq_redis_url))
    return _arq_pool