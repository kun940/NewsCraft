from fastapi import APIRouter, Depends,HTTPException,Query

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession

from crud.favorite import favorite_check, favorite_add, favorite_delete, favorite_list, get_favorite_total, \
    favorite_clear
from crud.users import get_current_active_user
from schemas.favorite import FavoriteStateData, FavoriteStateResponse, FavoriteAddResponse, \
    FavoriteAddRequest, FavoriteDeleteResponse, FavoriteListResponse, FavoriteNews, FavoriteListData
from utils.get_db_session import get_db

router = APIRouter(prefix="/api/favorite",tags=["favorite"])

@router.get("/check",response_model=FavoriteStateResponse)
async def check_favorite(newsId:int,current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    #鉴权
    if not current_active_user:
        raise HTTPException(status_code=401, detail="无用户令牌或令牌已过期")
    #查表
    result=await favorite_check(db,current_active_user.id,newsId)
    if result:
        result=True
    else:
        result=False
    #返回响应
    state=FavoriteStateData(isFavorite=result)
    response=FavoriteStateResponse(data=state)
    return response

@router.post("/add",response_model=FavoriteAddResponse)
async def add_favorite(req:FavoriteAddRequest,current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    #鉴权
    if not current_active_user:
        raise HTTPException(status_code=401, detail="无用户令牌或令牌已过期")
    added_favorite=await favorite_add(db,req.news_id,current_active_user)
    response=FavoriteAddResponse(data=added_favorite)
    return response

@router.delete("/remove",response_model=FavoriteDeleteResponse)
async def delete_favorite(newsId:int,current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    # 鉴权
    if not current_active_user:
        raise HTTPException(status_code=401, detail="无用户令牌或令牌已过期")
    await favorite_delete(db,newsId,current_active_user.id)
    response=FavoriteDeleteResponse()
    return response

@router.get("/list",response_model=FavoriteListResponse)
async def list_favorite(page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100,alias="pageSize"),current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    # 鉴权
    if not current_active_user:
        raise HTTPException(status_code=401, detail="无用户令牌或令牌已过期")
    fav_list:List[FavoriteNews]=await favorite_list(db,page,page_size,current_active_user.id)
    total=await get_favorite_total(db,current_active_user.id)
    if_more=((page-1)*page_size+len(fav_list))< total
    fav_list_data=FavoriteListData(list=fav_list,total=total,has_more=if_more)
    fav_list_response=FavoriteListResponse(data=fav_list_data)
    return fav_list_response

@router.delete("/clear",response_model=FavoriteDeleteResponse)
async def clear_favorite(db:AsyncSession=Depends(get_db),current_active_user=Depends(get_current_active_user)):
    # 鉴权
    if not current_active_user:
        raise HTTPException(status_code=401, detail="无用户令牌或令牌已过期")
    await favorite_clear(db,current_active_user.id)
    response=FavoriteDeleteResponse()
    return response