import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from models.news_models import Categories, News
from sqlalchemy import select, func

from utils.get_db_session import get_db


#获取新闻种类
async def get_categories(db:AsyncSession,skip:int=0, limit:int=10):
    stmt=select(Categories).offset(skip).limit(limit)
    results = await db.execute(stmt)
    return results.scalars().all()

if __name__ == '__main__':
    async def main():
        async for session in get_db():
            results=await get_categories(session)
            print(f"查询结果：{results}")
    asyncio.run(main())

#获取新闻列表
async def get_news_list(db:AsyncSession,categoryid:int,page:int=1,pageSize:int=10):
    stmt=select(News).where(News.category_id == categoryid).offset((page-1)*pageSize).limit(pageSize)
    results = await db.execute(stmt)
    return results.scalars().all()
#获取新闻总量（用于页面滚动）
async def get_news_total(db:AsyncSession,category_id:int):
    stmt=select(func.count(1)).select_from(News).where(News.category_id==category_id)
    results = await db.execute(stmt)
    return results.scalar()

#获取新闻详情
async def get_news_detail(db:AsyncSession,id:int):
    stmt=select(News).where(News.id==id)
    results = await db.execute(stmt)
    return results.scalar_one_or_none()
