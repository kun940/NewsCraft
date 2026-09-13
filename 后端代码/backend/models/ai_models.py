"""AI 相关表模型：news_vector_log（任务日志 + 幂等依据）。"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AiBase(DeclarativeBase):
    pass


class NewsVectorLog(AiBase):
    """新闻 AI 任务执行日志：每个 (news_id, task_type) 一条执行记录。"""

    __tablename__ = "news_vector_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, comment="新闻ID")
    task_type: Mapped[str] = mapped_column(String(50), comment="vectorize / summary")
    task_status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/success/failed")
    vector_id: Mapped[Optional[str]] = mapped_column(String(255), comment="Chroma 文档ID")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="重试次数")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="失败原因")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)


"""AI 相关表模型：news_vector_log（任务日志 + 幂等依据）。"""
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class AiBase(DeclarativeBase):
    pass


class NewsVectorLog(AiBase):
    """新闻 AI 任务执行日志：每个 (news_id, task_type) 一条执行记录。"""

    __tablename__ = "news_vector_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    news_id: Mapped[Optional[int]] = mapped_column(Integer, index=True, comment="新闻ID")
    task_type: Mapped[str] = mapped_column(String(50), comment="vectorize / summary")
    task_status: Mapped[str] = mapped_column(String(20), default="pending", comment="pending/success/failed")
    vector_id: Mapped[Optional[str]] = mapped_column(String(255), comment="Chroma 文档ID")
    retry_count: Mapped[int] = mapped_column(Integer, default=0, comment="重试次数")
    error_message: Mapped[Optional[str]] = mapped_column(Text, comment="失败原因")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime)