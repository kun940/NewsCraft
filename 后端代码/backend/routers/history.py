from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from crud.history import history_add, history_list, get_history_total, history_delete, history_clear
from crud.users import get_current_active_user
from schemas.history import AddHistoryRequest, HistoryData, AddHistoryResponse, HistoryListData, HistoryListResponse, \
    HistoryDeleteResponse
from utils.get_db_session import get_db

router=APIRouter(prefix="/api/history",tags=["history"])
@router.post("/add",response_model=AddHistoryResponse)
async def add_history(req:AddHistoryRequest,current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    # 鉴权
    if not current_active_user:
        raise HTTPException(status_code=401, detail="无用户令牌或令牌已过期")
    history=await history_add(db,req.news_id,current_active_user.id)
    history_add_response=AddHistoryResponse(data=history)
    return history_add_response

@router.get("/list",response_model=HistoryListResponse)
async def list_history(page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=100,alias="pageSize"),current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    # 鉴权
    if not current_active_user:
        raise HTTPException(status_code=401, detail="无用户令牌或令牌已过期")
    has_history_list=await history_list(db,current_active_user.id,page,page_size)
    total=await get_history_total(db,current_active_user.id)
    if_more = ((page - 1) * page_size + len(has_history_list)) < total
    history_list_data=HistoryListData(list=has_history_list,total=total,hasMore=if_more)
    history_list_response=HistoryListResponse(data=history_list_data)
    return history_list_response

@router.delete("/delete/{news_id}",response_model=HistoryDeleteResponse)
async def delete_history(news_id:int,current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    # 鉴权
    if not current_active_user:
        raise HTTPException(status_code=401, detail="无用户令牌或令牌已过期")
    deleted=await history_delete(db,news_id,current_active_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="浏览记录不存在")
    history_delete_response=HistoryDeleteResponse()
    return history_delete_response

@router.delete("/clear",response_model=HistoryDeleteResponse)
async def clear_history(current_active_user=Depends(get_current_active_user),db:AsyncSession=Depends(get_db)):
    # 鉴权
    if not current_active_user:
        raise HTTPException(status_code=401, detail="无用户令牌或令牌已过期")
    await history_clear(db,current_active_user.id)
    history_delete_response = HistoryDeleteResponse(message="清空浏览记录成功")
    return history_delete_response