import json
import logging
from typing import Any, Optional

from utils.cache import get_redis

logger = logging.getLogger(__name__)

KEY_NEWS_DETAIL = "news:detail:{news_id}"                          # TTL 1 小时
KEY_NEWS_LIST = "news:list:{category_id}:{page}:{size}"            # TTL 30 分钟
KEY_NEWS_CATEGORIES = "news:categories"                            # TTL 2 小时
KEY_HISTORY_LIST = "history:list:{user_id}"                        # TTL 1 小时
# 历史记录缓存条数上限：只缓存最近 N 条，防止单用户缓存无限膨胀（深翻页回源 DB）
HISTORY_CACHE_LIMIT = 200

async def cache_get_json(key: str) -> Optional[Any]:
    """读缓存并解析 JSON；未命中、解析失败或 Redis 异常均返回 None（走降级）。"""
    try:
        redis = await get_redis()
        raw = await redis.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("cache get failed key=%s err=%s", key, exc)
        return None

async def cache_set_json(key: str, data: Any, ttl: int) -> None:
    """写缓存：JSON 序列化 + 过期时间（秒）。"""
    try:
        redis = await get_redis()
        await redis.set(key, json.dumps(data, ensure_ascii=False), ex=ttl)
    except Exception as exc:
        logger.warning("cache set failed key=%s err=%s", key, exc)

async def cache_delete(*keys: str) -> None:
    """删除一个或多个具体缓存键（用于写操作后的精准失效）。"""
    try:
        redis = await get_redis()
        if keys:
            await redis.delete(*keys)
    except Exception as exc:
        logger.warning("cache delete failed keys=%s err=%s", keys, exc)

async def cache_delete_by_pattern(pattern: str) -> int:
    """按模式批量删除缓存键。

    - 用 SCAN 迭代（count=200 分批），不阻塞 Redis；生产环境禁止用 KEYS
    - 返回删除的键数量，用于日志与测试断言
    """
    deleted = 0
    try:
        redis = await get_redis()
        async for key in redis.scan_iter(match=pattern, count=200):
            await redis.delete(key)
            deleted += 1
    except Exception as exc:
        logger.warning("cache delete_by_pattern failed pattern=%s err=%s", pattern, exc)
    return deleted