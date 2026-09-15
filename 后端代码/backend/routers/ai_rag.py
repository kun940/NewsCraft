import logging

from arq import ArqRedis
from fastapi import APIRouter, Depends,HTTPException,Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.rag_core.recommend import get_recommendations
from crud.ai_crud import is_task_done
from crud.users import get_current_active_user
from models.news_models import News
from schemas.ai import VectorResponse, VectorRequest, VectorDetailItem, VectorResponseData, SummaryResponse, \
    SummaryRequest, SummaryDetailItem, SummaryResponseData, RecommendResponse
from utils.get_arq_pool import get_arq_pool
from utils.get_db_session import get_db
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from core.rag_core.rag_service import answer_question, chat_event_stream
from crud.ai_crud import list_chat_records
from schemas.ai import (
    ChatRequest, ChatResponse, ChatData, SourceItem,
    HistoryResponse, HistoryItem, HistoryData,
)

router=APIRouter(prefix="/api/ai",tags=["ai"])
logger=logging.getLogger(__name__)

@router.post("/news/vector",response_model=VectorResponse)
async def vectorize_news(req:VectorRequest,arq_pool: ArqRedis = Depends(get_arq_pool),db:AsyncSession=Depends(get_db)):
    """明确要向量化的是哪些新闻，过滤要跳过的新闻，剩下的入队给arq队列"""

    if req.news_ids :
        news_ids=req.news_ids
    else:
        stmt=select(News.id).where(News.news_vector_id.is_(None))
        result=await db.execute(stmt)
        rows=result.scalars().all()
        news_ids=rows

    accepted=0
    skipped=0
    detail=[]

    for news_id in news_ids:
        if await is_task_done(db,news_id,"vectorize"):
            skipped+=1
            detail_item=VectorDetailItem(newsId=news_id,status="skipped")
            detail.append(detail_item)
            continue
        await arq_pool.enqueue_job("vectorize_news_batch", [news_id])
        accepted+=1
        detail_item=VectorDetailItem(newsId=news_id,status="queued")
        detail.append(detail_item)

    logger.info("vectorize 受理：queued=%s skipped=%s", accepted, skipped)
    return VectorResponse(
        message="向量化任务已受理",
        data=VectorResponseData(acceptedCount=accepted, skippedCount=skipped, detail=detail),
    )

@router.post("/news/summary", response_model=SummaryResponse)
async def generate_summary(
    req: SummaryRequest,
    db: AsyncSession = Depends(get_db),
):

    # 1. 确定待处理新闻：缺省 = 全部未加工（ai_summary 为空，存量补做）
    if req.news_ids:
        news_ids = req.news_ids
    else:
        rows = await db.scalars(select(News.id).where(News.ai_summary.is_(None)))
        news_ids = list(rows.all())

    # 2. 过滤已成功加工的（幂等），其余入队
    pool = await get_arq_pool()
    accepted, detail = 0, []
    for nid in news_ids:
        if await is_task_done(db, nid, "summary"):
            detail.append(SummaryDetailItem(news_id=nid, status="skipped"))
            continue
        await pool.enqueue_job("generate_summary_batch", [nid])
        accepted += 1
        detail.append(SummaryDetailItem(news_id=nid, status="queued"))
    await db.commit()

    logger.info("summary 受理：queued=%s skipped=%s", accepted, len(detail) - accepted)
    return SummaryResponse(
        message="批量摘要任务已受理",
        data=SummaryResponseData(accepted_count=accepted, skipped_count=len(detail) - accepted, detail=detail),
    )

@router.get("/news/recommend", response_model=RecommendResponse)
async def recommend_news(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
    current_active_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """个性化推荐（分页）：有兴趣画像→向量召回；无画像→热门兜底。"""
    if not current_active_user:
        raise HTTPException(status_code=401, detail="未登录")
    data = await get_recommendations(db, current_active_user.id, page, page_size)
    return RecommendResponse(message="success", data=data)


async def _sources_from_ref_ids(db, ref_ids: str | None) -> list[dict]:
    """'1,2' → [{news_id, title}]（history 列表用；内部一律 Python 风格字段名）。"""
    if not ref_ids:
        return []
    ids = [int(x) for x in ref_ids.split(",") if x.strip()]
    if not ids:
        return []
    rows = await db.execute(select(News.id, News.title).where(News.id.in_(ids)))
    return [{"news_id": news_id, "title": title} for news_id, title in rows.all()]


@router.post("/chat")
async def chat(
    req: ChatRequest,
    current_active_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """RAG 智能问答：stream=true 走 SSE 流式；false 一次性 JSON（API 规范 5.4）。"""
    if not current_active_user:
        raise HTTPException(status_code=401, detail="未登录")
    if req.stream:
        return StreamingResponse(
            chat_event_stream(db, current_active_user.id, req.question),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",   # 关掉 Nginx/代理缓冲，保证逐 token 下发
            },
        )
    data = await answer_question(db, current_active_user.id, req.question)
    return ChatResponse(message="success", data=ChatData(**data))


@router.get("/chat/history", response_model=HistoryResponse)
async def chat_history(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
    current_active_user=Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """问答历史（分页，按时间倒序）。"""
    if not current_active_user:
        raise HTTPException(status_code=401, detail="未登录")
    records, total = await list_chat_records(db, current_active_user.id, page, page_size)
    items = []
    for r in records:
        items.append(HistoryItem(
            id=r.id,
            question=r.question,
            answer=r.answer,
            reference_news_ids=r.reference_news_ids,
            sources=[SourceItem(**s) for s in await _sources_from_ref_ids(db, r.reference_news_ids)],
            created_at=r.created_at,
        ))
    has_more = page * page_size < total
    return HistoryResponse(message="success", data=HistoryData(list=items, total=total, has_more=has_more))