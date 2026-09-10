from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func,delete
from models.history_models import History
from models.news_models import News
from schemas.history import HistoryNews


async def history_add(db:AsyncSession,news_id:int,user_id:int):
    # 检查是否浏览过新闻
    query = select(History).where(History.user_id == user_id, History.news_id == news_id)
    result = await db.execute(query)
    history = result.scalar_one_or_none()
    if history is None:
        history = History(user_id=user_id, news_id=news_id, view_time=datetime.now())
        db.add(history)
        await db.flush()
        await db.refresh(history)
        return history
    else:
        history.view_time = datetime.now()
        await db.flush()
        await db.refresh(history)
        return history

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