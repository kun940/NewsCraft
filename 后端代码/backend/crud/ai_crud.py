from datetime import datetime

from sqlalchemy import select,update
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_models import NewsVectorLog


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