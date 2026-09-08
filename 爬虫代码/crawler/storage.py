"""
入库模块

职责：
    - init_db：建表（IF NOT EXISTS 语义，与 database.sql 兼容）
    - get_or_create_category：分类不存在时自动创建
    - insert_news：按标题查重后插入新闻
    - UrlStateStore：已抓 URL 状态持久化（JSON 文件），支撑断点续爬

设计说明：
    - news 表没有 source_url 字段（原表结构未预留），因此去重采用
      「DB 标题查重 + 本地 URL 状态文件」双保险：
        * URL 状态文件负责"本条是否处理过"，避免跨运行重复抓详情；
        * 标题查重负责"库里是否已有同题新闻"，避免重复入库。
    - 若后续希望对源 URL 做数据库级唯一约束，可参考 README 的可选迁移。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from config import settings
from crawler.models import Base, Category, News

logger = logging.getLogger(__name__)


def build_engine():
    """创建同步引擎（pymysql 驱动）"""
    return create_engine(settings.database.url, pool_pre_ping=True, echo=False)


def init_db(engine) -> None:
    """按 ORM 元数据建表；表已存在时自动跳过（CREATE TABLE IF NOT EXISTS）"""
    Base.metadata.create_all(engine)


def get_or_create_category(session: Session, name: str) -> int:
    """按名称查分类 ID；不存在则创建（sort_order 取当前最大值 + 1，保证唯一）"""
    category = session.scalar(select(Category).where(Category.name == name))
    if category is not None:
        return category.id

    max_order = session.scalar(select(func.max(Category.sort_order))) or 0
    category = Category(name=name, sort_order=max_order + 1)
    session.add(category)
    session.flush()
    logger.info("自动创建分类「%s」(id=%s)", name, category.id)
    return category.id


def news_exists_by_title(session: Session, title: str) -> bool:
    """标题查重：库中已存在同题新闻返回 True"""
    return session.scalar(select(News.id).where(News.title == title)) is not None


def insert_news(
    session: Session,
    *,
    title: str,
    content: str,
    description: Optional[str] = None,
    image: Optional[str] = None,
    author: Optional[str] = None,
    category_id: int,
    publish_time: Optional[datetime] = None,
) -> bool:
    """
    插入一条新闻；标题已存在则跳过。
    返回 True 表示本次新插入，False 表示重复跳过。
    """
    if not title or not content:
        logger.warning("标题或正文为空，跳过入库")
        return False
    if news_exists_by_title(session, title):
        return False

    session.add(
        News(
            title=title,
            description=description,
            content=content,
            image=image,
            author=author,
            category_id=category_id,
            views=0,
            publish_time=publish_time or datetime.now(),
        )
    )
    return True


class UrlStateStore:
    """
    已抓 URL 状态存储（JSON 文件，原子写）

    状态分级：
        - done     已成功处理（入库或判重跳过）
        - skipped  无法解析/不支持的页面类型（视频页等），永久跳过不再重试
    网络抓取失败（FetchError）的条目不写入状态，下次运行自动重试。
    兼容旧版 {"urls": [...]} 列表格式，读取时自动迁移为 done。
    """

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self._urls: dict[str, str] = {}
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            raw = data.get("urls", {})
            if isinstance(raw, list):  # 旧格式迁移
                self._urls = {u: "done" for u in raw}
            elif isinstance(raw, dict):
                self._urls = dict(raw)
            logger.info("加载已抓 URL 状态：%s 条", len(self._urls))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("状态文件读取失败，忽略：%s", exc)

    def seen(self, url: str) -> bool:
        return url in self._urls

    def mark(self, url: str, status: str = "done") -> None:
        self._urls[url] = status

    def save(self) -> None:
        """原子写：先写临时文件再 replace，避免半截文件损坏状态"""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(
            json.dumps({"urls": dict(sorted(self._urls.items()))}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp.replace(self.path)
        logger.info("已抓 URL 状态落盘：共 %s 条", len(self._urls))
