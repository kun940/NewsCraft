"""
SQLAlchemy ORM 模型 —— 与后端 后端代码/backend/models/news_models.py 字段完全对齐

只映射爬虫写入涉及的两张表：
    - news_category（新闻分类表）
    - news（新闻表，含 RAG 升级脚本新增的 4 个预留字段，插入时留空）

不映射 user / related_news / favorite / history / ai_chat 等
用户行为表 —— 爬虫只负责「采集新闻入库」，不触碰用户数据。
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, VARCHAR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Category(Base):
    """新闻分类表（对应 scripts/migration/database.sql 的 news_category）"""

    __tablename__ = "news_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, comment="排序顺序")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )


class News(Base):
    """新闻表（对应 scripts/migration/database.sql 的 news + RAG 升级 4 字段）"""

    __tablename__ = "news"
    __table_args__ = (
        Index("fk_news_category_idx", "category_id"),
        Index("idx_publish_time", "publish_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="新闻ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻标题")
    description: Mapped[Optional[str]] = mapped_column(String(500), comment="新闻简介")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="新闻内容")
    image: Mapped[Optional[str]] = mapped_column(String(255), comment="封面图片URL")
    author: Mapped[Optional[str]] = mapped_column(String(50), comment="作者")
    category_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("news_category.id"), nullable=False, comment="分类ID"
    )
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="浏览量")
    publish_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="发布时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now, onupdate=datetime.now, comment="更新时间"
    )
    # ---- RAG 预留字段（database_rag_upgrade.sql 新增，爬虫不填）----
    news_vector_id: Mapped[Optional[str]] = mapped_column(VARCHAR(255), comment="向量数据库文档ID")
    ai_summary: Mapped[Optional[str]] = mapped_column(Text, comment="大模型自动生成的新闻摘要")
    ai_tags: Mapped[Optional[str]] = mapped_column(VARCHAR(255), comment="AI生成的多维度标签")
    content_keywords: Mapped[Optional[str]] = mapped_column(VARCHAR(500), comment="AI提取的新闻核心关键词")
