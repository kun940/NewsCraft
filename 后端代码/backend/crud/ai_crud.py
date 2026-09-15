from datetime import datetime

from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_models import NewsVectorLog, AiChatRecord


#AI加工记录表
async def is_task_done(db:AsyncSession,news_id:int,task_type:str)->bool:
    """检查表中某个新闻的特定任务类型是否完成"""
    stmt=select(NewsVectorLog).where(NewsVectorLog.news_id == news_id,NewsVectorLog.task_type==task_type,NewsVectorLog.task_status=="success")
    result=await db.execute(stmt)
    return result.scalar_one_or_none() is not None

async def create_task_log(db: AsyncSession, news_id: int, task_type: str) -> NewsVectorLog:
    """写入一条 pending 任务记录，作为执行依据。"""
    log = NewsVectorLog(news_id=news_id, task_type=task_type, task_status="pending")
    db.add(log)
    await db.flush()
    return log


async def mark_task_success(db: AsyncSession, log_id: int, vector_id: str | None = None) -> None:
    """标记任务执行成功"""
    await db.execute(
        update(NewsVectorLog)
        .where(NewsVectorLog.id == log_id)
        .values(task_status="success", vector_id=vector_id, finished_at=datetime.now())
    )


async def mark_task_failed(db: AsyncSession, log_id: int, error: str) -> None:
    """标记任务执行失败"""
    await db.execute(
        update(NewsVectorLog)
        .where(NewsVectorLog.id == log_id)
        .values(task_status="failed", error_message=str(error)[:2000], finished_at=datetime.now())
    )

#AI问答历史表
async def save_chat_record(
    db: AsyncSession, user_id: int, question: str, answer: str, ref_news_ids: list[int]
) -> int:
    """写入一条 RAG 问答记录，返回 record id（引用 ID 逗号分隔落库，空列表存 NULL）。"""
    record = AiChatRecord(
        user_id=user_id,
        question=question,
        answer=answer,
        reference_news_ids=",".join(str(i) for i in ref_news_ids) if ref_news_ids else None,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record.id


async def list_chat_records(
    db: AsyncSession, user_id: int, page: int, page_size: int
) -> tuple[list[AiChatRecord], int]:
    """按创建时间倒序分页查该用户的问答记录，返回 (记录列表, 总数)。"""
    total = await db.scalar(
        select(func.count()).select_from(AiChatRecord).where(AiChatRecord.user_id == user_id)
    )
    rows = await db.execute(
        select(AiChatRecord)
        .where(AiChatRecord.user_id == user_id)
        .order_by(AiChatRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(rows.scalars().all()), total or 0