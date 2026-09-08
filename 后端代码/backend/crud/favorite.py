from fastapi import HTTPException
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.favorite_models import Favorite
from models.news_models import News
from models.users_models import User
from schemas.favorite import FavoriteNews


async def favorite_check(db:AsyncSession,user_id,news_id):
    stmt=select(Favorite).where(Favorite.user_id==user_id,Favorite.news_id==news_id)
    result=await db.execute(stmt)
    result=result.scalar_one_or_none()
    return result

async def favorite_add(db:AsyncSession,news_id:int,current_active_user:User):
    # 1. 判断新闻是否存在
    query=select(News).where(News.id==news_id)
    result=await db.execute(query)
    result=result.scalar_one_or_none()
    if not result:
        raise HTTPException(status_code=404,detail="新闻不存在")
    # 2. 判断是否已经收藏（用户+新闻唯一）
    stmt=select(Favorite).where(Favorite.user_id==current_active_user.id,Favorite.news_id==news_id)
    is_exist=await db.execute(stmt)
    is_exist=is_exist.scalar_one_or_none()
    if is_exist:
        raise HTTPException(status_code=400, detail="已收藏该新闻")
    # 3. 创建收藏记录
    favorite=Favorite(
        user_id=current_active_user.id,
        news_id=news_id,
    )
    db.add(favorite)
    await db.flush()
    await db.refresh(favorite)
    return favorite

async def favorite_delete(db:AsyncSession,news_id:int,user_id:int):
    stmt = delete(Favorite).where(
        Favorite.news_id == news_id,
        Favorite.user_id == user_id
    )
    result = await db.execute(stmt)

async def favorite_list(db:AsyncSession,page:int,page_size:int,user_id:int):
    query=(select(News,Favorite.created_at)
           .join(Favorite,News.id==Favorite.news_id)
           .where(Favorite.user_id==user_id)
           .order_by(Favorite.created_at.desc())
           .offset((page-1)*page_size).limit(page_size))
    result=await db.execute(query)
    rows=result.all()
    return [
        FavoriteNews(
            id=news.id,
            title=news.title,
            description=news.description or "",            # 防 NULL 必填校验失败
            favorite_time=created_at,
            image=news.image,
            author=news.author,
            category_id=news.category_id,
            views=news.views,
            publish_time=news.publish_time,
        )
        for news, created_at in rows
    ]

#获取收藏总量（用于页面滚动）
async def get_favorite_total(db:AsyncSession,user_id:int):
    stmt=select(func.count(1)).select_from(Favorite).where(Favorite.user_id==user_id)
    results = await db.execute(stmt)
    return results.scalar()

async def favorite_clear(db:AsyncSession,user_id:int):
    stmt=delete(Favorite).where(Favorite.user_id==user_id)
    await db.execute(stmt)


