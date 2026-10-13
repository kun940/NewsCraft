"""
views 计数改造（P0-1 热点行锁修复）

把「每次浏览都 UPDATE news.views」从请求同步路径摘除：
    请求内   → Redis INCR（无锁原子，单键 ~10 万 ops/s，不存在行锁排队）
    后台回写 → 定期批量 flush：GETDEL 原子取走增量 → UPDATE views += delta
              → 失效该新闻 detail 缓存；UPDATE 失败时把 delta 补偿回 Redis

运行方式（二选一）：
    1. arq worker 已注册 cron（tasks/worker.py: 每分钟调 flush_views）
    2. 独立进程：python -m utils.view_counter（常驻循环）

一致性说明：
    - 展示值 = MySQL 基准 views + Redis 未回写增量（detail 接口合入）
    - GETDEL 保证「取走即删除」，同一份增量最多回写一次，不会重复计数
    - 回写失败补偿 INCRBY，保证不丢
    - Redis 不可用时 incr_view 降级返回 0：只丢计数，不阻塞浏览
"""
import asyncio
import logging

from sqlalchemy import update

from models.news_models import News
from utils.cache import get_redis
from utils.get_db_session import AsyncSessionLocal

logger = logging.getLogger(__name__)

VIEW_COUNTER_PREFIX = "news:views:"
VIEW_DETAIL_PREFIX = "news:detail:"
VIEW_SYNC_INTERVAL = 60  # 秒


def _counter_key(news_id: int) -> str:
    return f"{VIEW_COUNTER_PREFIX}{news_id}"


def _detail_key(news_id: int) -> str:
    return f"{VIEW_DETAIL_PREFIX}{news_id}"


async def incr_view(news_id: int) -> int:
    """浏览计数 +1，返回当前未回写增量。

    Redis 不可用时降级返回 0（只丢本次计数，不阻塞浏览请求）。
    """
    try:
        redis = await get_redis()
        delta = await redis.incr(_counter_key(news_id))
        return int(delta)
    except Exception as exc:  # noqa: BLE001
        logger.warning("incr_view failed news_id=%s err=%s", news_id, exc)
        return 0


async def flush_views() -> int:
    """批量回写：扫描增量 key → GETDEL 原子取走 → UPDATE views += delta → 失效 detail 缓存。

    返回回写的新闻条数。UPDATE 失败时把已取走的 delta 补偿回 Redis，下轮重试，不丢计数。
    """
    redis = await get_redis()
    keys = [k async for k in redis.scan_iter(match=f"{VIEW_COUNTER_PREFIX}*", count=200)]
    if not keys:
        return 0

    # pipeline 一次往返批量取走增量（GETDEL：Redis 6.2+，原子取走并删除）
    pipe = redis.pipeline()
    for key in keys:
        pipe.getdel(key)
    try:
        deltas = await pipe.execute()
    except Exception as exc:  # noqa: BLE001
        logger.warning("flush_views getdel failed err=%s", exc)
        return 0

    rows: list[tuple[int, int]] = []
    for key, delta in zip(keys, deltas):
        if delta:
            rows.append((int(key.rsplit(":", 1)[1]), int(delta)))
    if not rows:
        return 0

    try:
        async with AsyncSessionLocal() as db:
            for news_id, delta in rows:
                await db.execute(
                    update(News).where(News.id == news_id).values(views=News.views + delta)
                )
            await db.commit()
    except Exception:  # noqa: BLE001
        # 补偿：把已取走的增量加回去，下轮再试，避免丢计数
        logger.exception("flush_views 回写失败，补偿增量 rows=%s", rows)
        for news_id, delta in rows:
            try:
                await redis.incrby(_counter_key(news_id), delta)
            except Exception:  # noqa: BLE001
                logger.exception("补偿失败 news_id=%s delta=%s", news_id, delta)
        raise

    # 回写成功 → 失效这些新闻的 detail 缓存（下次重建读到新 views）
    for news_id, _delta in rows:
        try:
            await redis.delete(_detail_key(news_id))
        except Exception:  # noqa: BLE001
            logger.warning("删除 detail 缓存失败 news_id=%s", news_id)
    logger.info("flush_views 回写 %s 条", len(rows))
    return len(rows)


async def view_sync_loop() -> None:
    """常驻循环：每 VIEW_SYNC_INTERVAL 秒回写一次（独立进程入口用）。"""
    logger.info("view_sync_loop 启动，间隔 %s 秒", VIEW_SYNC_INTERVAL)
    while True:
        try:
            await flush_views()
        except Exception:  # noqa: BLE001
            logger.exception("view_sync_loop 单轮失败，下轮重试")
        await asyncio.sleep(VIEW_SYNC_INTERVAL)


async def _main() -> None:
    await view_sync_loop()


if __name__ == "__main__":
    asyncio.run(_main())
