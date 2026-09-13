"""
用户兴趣画像（模块二核心）：

    行为采集（浏览/收藏） → 行为新闻向量加权合成 → L2 归一化
    → 双写：Chroma user_interests（权威） + MySQL user 冗余字段

加权公式（架构文档 6.4）：
    user_vector = Σ (weight(action) × decay(Δt) × news_vector) / 归一化
    weight: 收藏=2.0  浏览=1.0
    decay(Δt) = 0.95^(Δt/24h)
"""
import json
import logging
import math
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import select

from config.settings import settings
from core.rag_core.vector_store import get_news_store, upsert_user_interest
from models.favorite_models import Favorite
from models.history_models import History
from models.news_models import News
from models.users_models import User

logger = logging.getLogger(__name__)


def _decay_weight(event_time: datetime, now: datetime) -> float:
    """时间衰减权重：0.95^(Δt/24h)，Δ 越小权重越高。"""
    dt_hours = max(0.0, (now - event_time).total_seconds() / 3600.0)
    return settings.recommend.decay_base ** (dt_hours / settings.recommend.decay_period_hours)


def _l2_normalize(vector: list[float]) -> list[float]:
    """L2 归一化（纯 Python 实现，不为一行数学引 numpy 依赖）。"""
    norm = math.sqrt(sum(x * x for x in vector))
    return [x / norm for x in vector] if norm else vector


async def _load_behaviors(db, user_id: int, now: datetime) -> list[tuple[int, datetime, float, str]]:
    """最近 behavior_days 天的浏览 + 全部收藏 → [(news_id, 行为时间, 行为权重, ai_tags)]。"""
    since = now - timedelta(days=settings.recommend.behavior_days)
    rows: list[tuple[int, datetime, float, str]] = []

    # 浏览（read）：权重 weight_read，只看时间窗口内
    hist = await db.execute(
        select(History.news_id, History.view_time)
        .where(History.user_id == user_id, History.view_time >= since)
    )
    for news_id, view_time in hist.all():
        rows.append((news_id, view_time, settings.recommend.weight_read, ""))

    # 收藏（favorite）：权重 weight_favorite，收藏是强偏好，不分时间窗口
    fav = await db.execute(
        select(Favorite.news_id, Favorite.created_at).where(Favorite.user_id == user_id)
    )
    for news_id, fav_time in fav.all():
        rows.append((news_id, fav_time, settings.recommend.weight_favorite, ""))

    # 同一批 id 一次 IN 查询补 ai_tags（兴趣标签统计用）
    if rows:
        news_ids = {r[0] for r in rows}
        news_rows = await db.execute(select(News.id, News.ai_tags).where(News.id.in_(news_ids)))
        tags_by_id = dict(news_rows.all())
        rows = [(nid, t, w, tags_by_id.get(nid) or "") for nid, t, w, _ in rows]
    return rows


async def refresh_user_interest(db, user_id: int) -> None:
    """重算并写入用户兴趣画像（幂等：全量重算 + 覆盖写，可重复调用）。"""
    now = datetime.now()
    behaviors = await _load_behaviors(db, user_id, now)
    if not behaviors:
        logger.info("user_id=%s 无行为数据，跳过画像刷新", user_id)
        return

    # 1. 批量取行为新闻的向量（Chroma；行为表只存了 news_id，向量在向量库）
    news_ids = [str(r[0]) for r in behaviors]
    got = get_news_store().get(ids=news_ids, include=["embeddings"])
    embeddings_by_id = dict(zip(got.get("ids", []), got.get("embeddings", [])))

    # 2. 加权合成：只累计有向量的新闻（没有 = 模块一还没加工到，先跳过）
    acc = None
    for news_id, event_time, weight, _ in behaviors:
        emb = embeddings_by_id.get(str(news_id))
        if emb is None:
            continue
        w = weight * _decay_weight(event_time, now)
        acc = [x * w for x in emb] if acc is None else [a + x * w for a, x in zip(acc, emb)]
    if acc is None:
        logger.warning("user_id=%s 行为新闻均未向量化，跳过画像刷新", user_id)
        return
    user_vector = _l2_normalize(acc)

    # 3. 兴趣标签：行为新闻 ai_tags 频次统计，取 TopN（逗号分隔落库）
    tag_counter = Counter()
    for _, _, _, tags in behaviors:
        tag_counter.update(t.strip() for t in tags.split(",") if t.strip())
    interest_tags = ",".join(t for t, _ in tag_counter.most_common(settings.recommend.interest_tag_top_n))

    # 4. 双写：Chroma 权威 + MySQL 冗余（user_interest_vector 严禁返回前端）
    upsert_user_interest(user_id, user_vector, interest_tags)
    user = await db.get(User, user_id)
    if user:
        user.user_interest_vector = json.dumps(user_vector, ensure_ascii=False)
        user.user_interest_tags = interest_tags or None
        await db.commit()

    logger.info("兴趣画像刷新完成 user_id=%s 标签=%s", user_id, interest_tags or "(空)")