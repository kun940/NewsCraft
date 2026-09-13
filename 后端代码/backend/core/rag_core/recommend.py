"""
个性化推荐服务（模块二主链路）：

    GET /api/ai/news/recommend
    缓存命中            → 直接返回
    未命中 + 有画像      → 向量召回 TopN → 过滤已读/已收藏 → 组装 reason/score → 写缓存
    未命中 + 无画像      → 热门兜底（views 降序）→ 写缓存

缓存：整份候选列表（含 strategy），key=ai:recommend:{user_id}，TTL=10 分钟；
行为变化时由 worker 的 sync_user_interest 主动失效。
"""
import json
import logging

from sqlalchemy import select

from config.settings import settings
from core.rag_core.vector_store import (
    get_user_interest,
    similarity_search_by_vector_with_relevance_scores,
)
from models.favorite_models import Favorite
from models.history_models import History
from models.news_models import News
from utils.cache import get_redis

logger = logging.getLogger(__name__)

CACHE_KEY = "ai:recommend:{user_id}"


def _similarity(distance: float) -> float:
    """cosine 距离 → 0~1 相似度（向量已 L2 归一化，近似 1 - d）。"""
    return max(0.0, min(1.0, 1.0 - distance))


def _build_reason(top_tags: str) -> str:
    """推荐理由文案（前端展示用，API 规范 5.3 的 reason 字段）。"""
    tag = (top_tags or "").split(",")[0].strip()
    return f"因为您近期关注「{tag}」相关内容" if tag else "根据您的浏览偏好为您推荐"


async def _load_feedback_ids(db, user_id: int) -> set[int]:
    """已读 + 已收藏的新闻 id（召回结果里过滤掉，避免推荐看过的内容）。"""
    read_ids = (await db.execute(select(History.news_id).where(History.user_id == user_id))).scalars().all()
    fav_ids = (await db.execute(select(Favorite.news_id).where(Favorite.user_id == user_id))).scalars().all()
    return set(read_ids) | set(fav_ids)


async def _news_by_ids(db, news_ids: list[int]) -> dict[int, News]:
    """按 id 批量取新闻（保证响应字段与 /api/news/list 一致且新鲜）。"""
    rows = await db.execute(select(News).where(News.id.in_(news_ids)))
    return {n.id: n for n in rows.scalars().all()}


def _to_item(news: News, reason: str, score: float | None) -> dict:
    """新闻 ORM → 推荐条目 dict（含 reason / score，字段对齐 API 规范 5.3）。"""
    return {
        "id": news.id,
        "title": news.title,
        "description": news.description or "",
        "image": news.image,
        "author": news.author,
        "category_id": news.category_id,
        "views": news.views,
        "publish_time": news.publish_time,
        "ai_summary": news.ai_summary,
        "ai_tags": news.ai_tags,
        "content_keywords": news.content_keywords,
        "reason": reason,
        "score": round(score, 4) if score is not None else None,
    }


async def _vector_recall(db, user_id: int, top_tags: str) -> list[dict]:
    """兴趣向量召回：相似度搜索 → 过滤已读/已收藏 → 按 id 补全新闻 → 组装条目。"""
    interest = get_user_interest(user_id)
    if interest is None:
        return []
    hits = similarity_search_by_vector_with_relevance_scores(
        interest["vector"], top_k=settings.recommend.recall_top_k
    )
    feedback_ids = await _load_feedback_ids(db, user_id)
    candidates = [
        (int(doc.metadata["news_id"]), _similarity(score))
        for doc, score in hits
        if int(doc.metadata["news_id"]) not in feedback_ids
    ]
    news_map = await _news_by_ids(db, [nid for nid, _ in candidates])
    return [
        _to_item(news_map[nid], reason=_build_reason(top_tags), score=score)
        for nid, score in candidates
        if nid in news_map
    ]


async def _hot_fallback(db) -> list[dict]:
    """冷启动兜底：浏览量倒序取热门新闻（strategy=hot_fallback）。"""
    rows = await db.execute(
        select(News).order_by(News.views.desc()).limit(settings.recommend.hot_fallback_count)
    )
    return [_to_item(n, reason="热门精选", score=None) for n in rows.scalars().all()]


def _paginate(items: list[dict], strategy: str, page: int, page_size: int) -> dict:
    """候选列表内存分页（候选 50 条，页大小最大 100，够用且简单）。"""
    start = (page - 1) * page_size
    page_items = items[start:start + page_size]
    return {
        "strategy": strategy,
        "list": page_items,
        "total": len(items),
        "hasMore": start + len(page_items) < len(items),
    }


async def get_recommendations(db, user_id: int, page: int, page_size: int) -> dict:
    """推荐主流程：缓存 → 画像判断 → 召回/兜底 → 分页。"""
    redis = await get_redis()
    cache_key = CACHE_KEY.format(user_id=user_id)

    # 1. 缓存命中：直接返回整页（10 分钟内翻页不触发向量检索）
    cached = await redis.get(cache_key)
    if cached:
        data = json.loads(cached)
        logger.info("推荐缓存命中 user_id=%s", user_id)
        return _paginate(data["items"], data["strategy"], page, page_size)

    # 2. 未命中：按画像决定策略
    interest = get_user_interest(user_id)
    if interest is None:
        items = await _hot_fallback(db)
        strategy = "hot_fallback"
    else:
        items = await _vector_recall(db, user_id, interest["tags"])
        strategy = "vector"

    # 3. 写缓存（default=str 处理 datetime 序列化）
    await redis.set(
        cache_key,
        json.dumps({"strategy": strategy, "items": items}, default=str),
        ex=settings.recommend.cache_ttl,
    )
    return _paginate(items, strategy, page, page_size)