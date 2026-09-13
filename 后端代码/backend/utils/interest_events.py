"""行为事件 → 兴趣画像刷新通知（异步入队，失败绝不阻断主流程）。"""
import logging

from utils.get_arq_pool import get_arq_pool

logger = logging.getLogger(__name__)


async def notify_interest_sync(user_id: int, news_id: int, action: str) -> None:
    try:
        pool = await get_arq_pool()
        # 节流锁：60 秒内已触发过则跳过本次（键已存在 → set 返回 None → 直接 return）
        acquired = await pool.set(f"interest:sync:{user_id}", "1", ex=60, nx=True)
        if not acquired:
            return
        await pool.enqueue_job("sync_user_interest", user_id, news_id, action)
        logger.info("兴趣同步已入队 user_id=%s news_id=%s action=%s", user_id, news_id, action)
    except Exception:  # noqa: BLE001
        logger.warning("兴趣同步入队失败 user_id=%s news_id=%s", user_id, news_id)