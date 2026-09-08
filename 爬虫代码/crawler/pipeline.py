"""
抓取流水线编排

支持两种数据源（config.crawl.source 切换，也可用 main.py --source 覆盖）：
    - netease   网易新闻：多频道列表页 → 详情页（默认，图片覆盖率高）
    - chinanews 中国新闻网：RSS 即时新闻 → 详情页

通用流程：
    1. 抓列表（RSS / 频道页）
    2. 过滤：已抓过的 URL（状态文件）直接跳过
    3. 并发抓取详情页（ThreadPoolExecutor）
    4. 串行入库：分类兜底创建 → 标题查重 → 插入 → 标记 URL

线程安全说明：
    - 网络抓取阶段在线程池中并发执行（requests 线程安全）；
    - SQLAlchemy Session 只在主线程使用，插入严格串行，避免会话跨线程。
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from sqlalchemy.orm import sessionmaker

from config import settings
from crawler import netease
from crawler.fetcher import FetchError, Fetcher
from crawler.parser import NewsDetail, parse_detail, parse_rss
from crawler.storage import (
    UrlStateStore,
    build_engine,
    get_or_create_category,
    init_db,
    insert_news,
)

logger = logging.getLogger(__name__)


@dataclass
class CrawlStats:
    """一次运行的统计汇总"""

    list_items: int = 0          # 列表解析出的条目总数
    pending: int = 0             # 本次待抓详情数（去重后）
    detail_failed: int = 0       # 详情抓取/解析失败数
    inserted: int = 0            # 新入库数
    duplicated: int = 0          # 重复跳过数
    skipped: int = 0             # 不支持类型 / 超龄新闻跳过数


def run(limit: int = 0, source: str | None = None) -> CrawlStats:
    """
    执行一次完整抓取。
    limit: 本次最多处理条数，0 表示不限制。
    source: 临时切换数据源（netease/chinanews），不传则用 config 默认值。
    """
    if source:
        if source not in ("netease", "chinanews"):
            raise ValueError(f"未知数据源：{source}（可选 netease / chinanews）")
        settings.crawl.source = source
        logger.info("本次运行切换数据源：%s", source)

    if settings.crawl.source == "netease":
        return _run_netease(limit)
    return _run_chinanews(limit)


# ================================================================
# 数据源一：中国新闻网（RSS 即时新闻）
# ================================================================

def _run_chinanews(limit: int = 0) -> CrawlStats:
    """
    执行一次完整抓取（中国新闻网）。
    limit: 本次最多处理条数，0 表示不限制。
    """
    stats = CrawlStats()
    fetcher = Fetcher()
    state = UrlStateStore(settings.crawl.state_file)
    engine = build_engine()
    init_db(engine)

    # ---------- 1. 抓 RSS 列表 ----------
    logger.info("抓取 RSS 列表：%s", settings.crawl.rss_url)
    try:
        rss_text = fetcher.get(settings.crawl.rss_url)
    except FetchError as exc:
        logger.error("列表抓取失败，本次运行终止：%s", exc)
        return stats

    items = parse_rss(rss_text)
    stats.list_items = len(items)
    logger.info("RSS 解析到 %s 条新闻", stats.list_items)
    if not items:
        logger.warning("RSS 为空或解析失败，检查网络与站点可用性")
        return stats

    # ---------- 2. 过滤：已抓 URL / 不支持类型 / 条数上限 ----------
    patterns = settings.crawl.exclude_url_patterns
    pending = [it for it in items if not state.seen(it.url)]
    kept: list = []
    for it in pending:
        if any(p in it.url for p in patterns):
            stats.skipped += 1
            state.mark(it.url, status="skipped")   # 视频页等无正文，永久跳过
            logger.info("不支持类型跳过：%s", it.title)
        else:
            kept.append(it)
    pending = kept
    if limit > 0 and len(pending) > limit:
        pending = pending[:limit]
    stats.pending = len(pending)
    logger.info("去重后待抓详情 %s 条（本次上限 %s，已跳过 %s 条）", len(pending), limit or "不限", stats.skipped)
    if not pending:
        logger.info("没有新的待抓新闻，本次运行结束")
        state.save()
        return stats

    # ---------- 3. 并发抓详情页 ----------
    details: dict[str, NewsDetail | None] = {}
    with ThreadPoolExecutor(max_workers=settings.crawl.workers) as pool:
        futures = {pool.submit(_fetch_detail, fetcher, it.url): it.url for it in pending}
        for future in as_completed(futures):
            url = futures[future]
            try:
                detail = future.result()
            except FetchError as exc:
                logger.warning("详情抓取失败：%s", exc)
                detail = None
            if detail is None:
                stats.detail_failed += 1
            details[url] = detail

    # ---------- 4. 串行入库 ----------
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with SessionLocal() as session:
            for item in pending:
                detail = details.get(item.url)
                if detail is None:
                    # 抓到了页面但解析不出正文（无 h1/正文容器）：
                    # 视为不支持类型，永久跳过，避免每次运行重复抓取
                    state.mark(item.url, status="skipped")
                    continue

                category_id = get_or_create_category(session, item.category)
                publish_time = detail.publish_time or item.pub_date or datetime.now()
                description = item.description or _shorten(detail.content)

                inserted = insert_news(
                    session,
                    title=detail.title,
                    content=detail.content,
                    description=description,
                    image=detail.image or None,
                    author=detail.author or None,
                    category_id=category_id,
                    publish_time=publish_time,
                )
                if inserted:
                    stats.inserted += 1
                    logger.info("入库成功：%s（%s）", detail.title, item.category)
                else:
                    stats.duplicated += 1
                    logger.info("标题重复跳过：%s", detail.title)
                state.mark(item.url, status="done")
            session.commit()
    except Exception:
        logger.exception("入库阶段异常，事务回滚")
        raise

    state.save()
    _log_summary(stats)
    return stats


# ================================================================
# 数据源二：网易新闻（频道页 → 详情页）
# ================================================================

def _run_netease(limit: int = 0) -> CrawlStats:
    """
    执行一次完整抓取（网易新闻）。
    各频道页取前 netease_per_channel 条（频道页按时间倒序），
    详情发布时间超过 max_age_days 的跳过。
    """
    stats = CrawlStats()
    fetcher = Fetcher()
    state = UrlStateStore(settings.crawl.state_file)
    engine = build_engine()
    init_db(engine)
    per_channel = settings.crawl.netease_per_channel
    max_age = timedelta(days=settings.crawl.max_age_days)

    # ---------- 1. 抓各频道列表页，收集候选 (分类, URL) ----------
    candidates: list[tuple[str, str]] = []
    for category, page_url in settings.crawl.netease_channels:
        try:
            html = fetcher.get(page_url)
        except FetchError as exc:
            logger.warning("频道页抓取失败 %s：%s", page_url, exc)
            continue
        links = netease.extract_links(html)
        stats.list_items += len(links)
        fresh = [u for u in links[:per_channel] if not state.seen(u)]
        candidates.extend((category, u) for u in fresh)
        logger.info("频道「%s」解析 %s 条链接，取前 %s 条，未处理 %s 条",
                    category, len(links), per_channel, len(fresh))

    if limit > 0 and len(candidates) > limit:
        candidates = candidates[:limit]
    stats.pending = len(candidates)
    logger.info("去重后待抓详情 %s 条（本次上限 %s）", len(candidates), limit or "不限")
    if not candidates:
        logger.info("没有新的待抓新闻，本次运行结束")
        state.save()
        return stats

    # ---------- 2. 并发抓详情页 ----------
    details: dict[str, dict | None] = {}
    with ThreadPoolExecutor(max_workers=settings.crawl.workers) as pool:
        futures = {pool.submit(_fetch_netease_detail, fetcher, url): url for _, url in candidates}
        for future in as_completed(futures):
            url = futures[future]
            try:
                detail = future.result()
            except FetchError as exc:
                logger.warning("详情抓取失败：%s", exc)
                detail = None
            if detail is None:
                stats.detail_failed += 1
            details[url] = detail

    # ---------- 3. 串行入库（含时效过滤） ----------
    now = datetime.now()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    try:
        with SessionLocal() as session:
            for category, url in candidates:
                detail = details.get(url)
                if detail is None:
                    state.mark(url, status="skipped")
                    continue

                pub = detail["publish_time"] or now
                if now - pub > max_age:
                    stats.skipped += 1
                    state.mark(url, status="done")   # 超龄旧闻，标记避免重复抓
                    logger.info("超龄跳过：%s（%s）", detail["title"], pub)
                    continue

                category_id = get_or_create_category(session, category)
                inserted = insert_news(
                    session,
                    title=detail["title"],
                    content=detail["content"],
                    description=_shorten(detail["content"]),
                    image=detail["image"] or None,
                    author=detail["source"] or None,
                    category_id=category_id,
                    publish_time=pub,
                )
                if inserted:
                    stats.inserted += 1
                    logger.info("入库成功：%s（%s）", detail["title"], category)
                else:
                    stats.duplicated += 1
                    logger.info("标题重复跳过：%s", detail["title"])
                state.mark(url, status="done")
            session.commit()
    except Exception:
        logger.exception("入库阶段异常，事务回滚")
        raise

    state.save()
    _log_summary(stats)
    return stats


def _fetch_detail(fetcher: Fetcher, url: str) -> NewsDetail | None:
    """线程池任务（中新网）：抓详情页并解析"""
    html = fetcher.get(url)
    return parse_detail(html)


def _fetch_netease_detail(fetcher: Fetcher, url: str) -> dict | None:
    """线程池任务（网易）：抓详情页并解析"""
    html = fetcher.get(url)
    return netease.parse_detail(html)


def _shorten(content: str, length: int = 100) -> str:
    """正文太长时截断生成简介"""
    text = " ".join(content.split())
    return text[:length] + ("…" if len(text) > length else "")


def _log_summary(stats: CrawlStats) -> None:
    logger.info(
        "运行汇总：列表 %s 条 | 待抓 %s | 新入库 %s | 重复跳过 %s | 详情失败 %s | 跳过 %s",
        stats.list_items,
        stats.pending,
        stats.inserted,
        stats.duplicated,
        stats.detail_failed,
        stats.skipped,
    )
