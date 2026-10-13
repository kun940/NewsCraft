from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func,delete
from sqlalchemy.dialects.mysql import insert as mysql_insert
from models.history_models import History
from models.news_models import News
from schemas.history import HistoryNews


async def history_add(db:AsyncSession,news_id:int,user_id:int):
    """浏览历史写入：INSERT ... ON DUPLICATE KEY UPDATE（依赖 (user_id, news_id) 唯一键）。

    并发安全：由数据库原子判断「有则更新 view_time、无则插入」，无需先 SELECT，
    杜绝 check-then-act 竞态导致的重复行；同时比原来的「SELECT + INSERT/UPDATE」
    少一次查询往返。
    """
    now = datetime.now()
    stmt = (
        mysql_insert(History)
        .values(user_id=user_id, news_id=news_id, view_time=now)
        .on_duplicate_key_update(view_time=now)
    )
    await db.execute(stmt)
    await db.flush()
    # MySQL 8.0 不支持 INSERT ... RETURNING，回读该行返回
    q = select(History).where(History.user_id == user_id, History.news_id == news_id)
    return (await db.execute(q)).scalar_one()

async def history_list(db:AsyncSession,user_id:int,page:int=1,page_size:int=10):
    query=(select(News,History.view_time)
           .join(History,News.id==History.news_id)
           .where(History.user_id==user_id)
           .order_by(History.view_time.desc())
           .offset((page-1)*page_size).limit(page_size)
           )
    results = await db.execute(query)
    rows = results.all()
    return [
        HistoryNews(
            id=news.id,
            title=news.title,
            description=news.description or "",  # 防 NULL 必填校验失败
            view_time=view_time,
            image=news.image,
            author=news.author,
            category_id=news.category_id,
            views=news.views,
            publish_time=news.publish_time,
        )
        for news, view_time in rows
    ]

async def get_history_total(db:AsyncSession,user_id:int):
    stmt=select(func.count(1)).select_from(History).where(History.user_id==user_id)
    results = await db.execute(stmt)
    return results.scalar()

async def history_delete(db:AsyncSession,news_id:int,user_id:int):
    stmt=delete(History).where(History.user_id==user_id,History.news_id==news_id)
    result = await db.execute(stmt)
    await db.flush()
    return result.rowcount > 0

async def history_clear(db:AsyncSession,user_id:int):
    stmt=delete(History).where(History.user_id==user_id)
    await db.execute(stmt)
    await db.flush()