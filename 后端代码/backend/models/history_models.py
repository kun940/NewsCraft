from sqlalchemy.orm import Mapped, mapped_column,DeclarativeBase
from sqlalchemy import Integer, DateTime, ForeignKey,Index
from datetime import datetime

from models.news_models import News
from models.users_models import User


class Base(DeclarativeBase):
    pass
class History(Base):
    """
    浏览历史表0RM模型
    """
    __tablename__ = 'history'
    #创建表级别的配置
    __table_args__= (
    Index('fk_history_user_idx','user_id'),
    Index('fk_history_news_idx','news_id'),
    Index('idx_view_time','view_time'),
    )
    #字段配置
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True,comment="历史ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False,comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey(News.id), nullable=False,comment="新闻ID")
    view_time: Mapped[datetime] = mapped_column(DateTime,default=datetime.now,nullable=False,comment="浏览时间")
    def _repr_(self):
        return f"<History(id={self.id},user_id={self.user_id},news_id={self.news_id}, view_time={self.view_time})>"