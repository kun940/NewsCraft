from datetime import datetime
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, Integer, String, Index, Text, ForeignKey, VARCHAR


#新闻相关模型类的基类
class Base(DeclarativeBase):
    created_at:Mapped[datetime]=mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )

#新闻分类模型类
class Categories(Base):
    __tablename__ ="news_category"
    id:Mapped[int]=mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="分类ID"
    )
    name:Mapped[str]=mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="分类名称"
    )
    sort_order:Mapped[int]=mapped_column(
        Integer,
        unique=True,
        nullable=False,
        comment="排序顺序"
    )

#新闻模型类
class News(Base):
    __tablename__ = "news"
    # 创建索引:提升查询速度→添加目录
    __table_args__ = (
        Index('fk_news_category_idx', 'category_id'),
        Index('idx_publish_time', 'publish_time')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="新闻ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻标题")
    description: Mapped[Optional[str]] = mapped_column(String(500), comment="新闻简介")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="新闻内容")
    image: Mapped[Optional[str]] = mapped_column(String(255), comment="封面图片URL")
    author: Mapped[Optional[str]] = mapped_column(String(50), comment="作者")
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey('news_category.id'), nullable=False)
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="浏览量")
    publish_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="发布时间")
    news_vector_id:Mapped[str]=mapped_column(VARCHAR,comment="向量数据库文档ID")
    ai_summary:Mapped[Optional[str]]=mapped_column(Text,comment="大模型自动生成的新闻摘要")
    ai_tags:Mapped[Optional[str]]=mapped_column(VARCHAR,comment="AI生成的多维度标签")
    content_keywords:Mapped[Optional[str]]=mapped_column(VARCHAR,comment="AI提取的新闻核心关键词")


    def __repr__(self):
        return f"<News(id={self.id}, title='{self.title}', views={self.views})>"