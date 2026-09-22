from typing import List

from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from cache.cache_service import cache_get_json, KEY_NEWS_CATEGORIES, cache_set_json, KEY_NEWS_LIST, KEY_NEWS_DETAIL
from crud.news import get_categories, get_news_total, get_news_list, get_news_detail
from schemas.newsbase import CategoryResponse, NewsListResponse, NewsListData, NewsDetailResponse, CategoryData, \
    NewsDetailData
from utils.get_db_session import get_db

router = APIRouter(prefix="/api/news", tags=["news"])

CATEGORIES_TTL = 2 * 60 * 60
NEWS_LIST_TTL = 30 * 60  # 30 分钟
NEWS_DETAIL_TTL = 60 * 60  # 1 小时

@router.get("/categories",response_model=CategoryResponse)
async def get_category(skip:int=0, limit:int=10,db:AsyncSession=Depends(get_db)):
    """
    查询数据库获得信息返回给前端
    """
    if skip == 0:
        cached = await cache_get_json(KEY_NEWS_CATEGORIES)
        if cached is not None:
            return CategoryResponse(data=[CategoryData(**item) for item in cached])
    category_data= await get_categories(db,skip,limit)
    if skip == 0:
        payload = [CategoryData.model_validate(c).model_dump(mode="json") for c in category_data]
        await cache_set_json(KEY_NEWS_CATEGORIES, payload, CATEGORIES_TTL)
    category_response=CategoryResponse(data=category_data)
    return category_response

@router.get("/list",response_model=NewsListResponse)
async def get_list(categoryId:int,page:int=1,pageSize:int=10,db:AsyncSession=Depends(get_db)):
    key = KEY_NEWS_LIST.format(category_id=categoryId, page=page, size=pageSize)

    cached = await cache_get_json(key)
    if cached is not None:
        # cached 为 {"datalist": [...], "total": N, "has_more": bool}
        return NewsListResponse(data=NewsListData.model_validate(cached))

    news_list= await get_news_list(db,categoryId,page,pageSize)
    total=await get_news_total(db,categoryId)
    has_more=((page-1)*pageSize+len(news_list))< total

    news_list_data=NewsListData(datalist=news_list,total= total,has_more=has_more)
    await cache_set_json(key, news_list_data.model_dump(mode="json"), NEWS_LIST_TTL)
    news_list_response=NewsListResponse(data=news_list_data)
    return news_list_response

@router.get("/detail",response_model=NewsDetailResponse)
async def get_detail(id:int,db:AsyncSession=Depends(get_db)):
    key = KEY_NEWS_DETAIL.format(news_id=id)

    cached = await cache_get_json(key)
    if cached is not None:
        return NewsDetailResponse(data=NewsDetailData.model_validate(cached))

    news_detail_data=await get_news_detail(db,id)
    #数据库不存在该新闻
    if not news_detail_data:
        raise HTTPException(status_code=404,detail="新闻不存在")

    data_obj = NewsDetailData.model_validate(news_detail_data)
    await cache_set_json(key, data_obj.model_dump(mode="json"), NEWS_DETAIL_TTL)

    news_detail_response=NewsDetailResponse(data=news_detail_data)
    return news_detail_response