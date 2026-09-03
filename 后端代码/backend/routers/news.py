from typing import List

from fastapi import APIRouter, Depends,HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from crud.news import get_categories, get_news_total, get_news_list, get_news_detail
from schemas.newsbase import CategoryResponse, NewsListResponse, NewsListData, NewsDetailResponse
from utils.get_db_session import get_db

router = APIRouter(prefix="/api/news", tags=["news"])

@router.get("/categories",response_model=CategoryResponse)
async def get_category(skip:int=0, limit:int=10,db:AsyncSession=Depends(get_db)):
    """
    查询数据库获得信息返回给前端
    """
    category_data= await get_categories(db,skip,limit)
    category_response=CategoryResponse(data=category_data)
    return category_response

@router.get("/list",response_model=NewsListResponse)
async def get_list(categoryId:int,page:int=1,pageSize:int=10,db:AsyncSession=Depends(get_db)):
    news_list= await get_news_list(db,categoryId,page,pageSize)
    total=await get_news_total(db,categoryId)
    has_more=((page-1)*pageSize+len(news_list))< total
    news_list_data=NewsListData(datalist=news_list,total= total,has_more=has_more)
    news_list_response=NewsListResponse(data=news_list_data)
    return news_list_response

@router.get("/detail",response_model=NewsDetailResponse)
async def get_detail(id:int,db:AsyncSession=Depends(get_db)):
    news_detail_data=await get_news_detail(db,id)
    #数据库不存在该新闻
    if not news_detail_data:
        raise HTTPException(status_code=404,detail="新闻不存在")
    news_detail_response=NewsDetailResponse(data=news_detail_data)
    return news_detail_response