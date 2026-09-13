"""异步队列Arq的worker端"""
import logging

from config.settings import settings
from core.rag_core.chains import get_summary_chain
from core.rag_core.document_factory import news_to_document
from core.rag_core.vector_store import add_news
from crud.ai_crud import is_task_done, create_task_log, mark_task_success, mark_task_failed
from models.news_models import News, Categories
from utils.get_db_session import AsyncSessionLocal
from arq.connections import RedisSettings as ArqRedisSettings
logging.basicConfig(level=logging.INFO)
logger=logging.getLogger(__name__)
#任务函数
async def generate_summary_batch(ctx,news_id:list[int]):
    chain=get_summary_chain()
    done=0
    async with AsyncSessionLocal() as db:
        for per_news_id in news_id:
            is_done=await is_task_done(db,per_news_id,"summary")
            if is_done:
                logger.info(f"summary 已成功过，跳过id为{news_id}的新闻")
                continue
            news = await db.get(News, news_id)
            if news is None:
                logger.warning(f"id为{news_id}的新闻不存在，跳过")
                continue
            log=await create_task_log(db,per_news_id,"summary")
            try:
                result=await chain.ainvoke({"title": news.title, "content": news.content[:2000]})
                news.ai_summary = result.summary
                news.ai_tags = ",".join(result.tags)
                news.content_keywords = ",".join(result.keywords)
                await mark_task_success(db, log.id)
                done += 1
                logger.info(f"id为{news_id}的新闻summary完成")
            except Exception as exc:  # noqa: BLE001  单条失败只记日志，批次继续
                await mark_task_failed(db, log.id, str(exc))
                logger.exception("summary 失败 news_id=%s", news_id)
        await db.commit()
    return done

async def vectorize_news_batch(ctx, news_ids: list[int]) -> int:
    """向量化：新闻 → Document → bge-m3 → Chroma，回填 news_vector_id。"""
    done = 0
    async with AsyncSessionLocal() as db:
        for news_id in news_ids:
            if await is_task_done(db, news_id, "vectorize"):
                logger.info("vectorize 已成功过，跳过 news_id=%s", news_id)
                continue
            news = await db.get(News, news_id)
            if news is None:
                logger.warning("news_id=%s 不存在，跳过", news_id)
                continue
            category = await db.get(Categories, news.category_id)
            log = await create_task_log(db, news_id, "vectorize")
            try:
                doc = news_to_document(news, category.name if category else None)
                ids = add_news([doc])            # 内部调用 bge-m3 生成向量并写入 Chroma
                news.news_vector_id = ids[0]     # Chroma 文档ID = 新闻主键字符串
                await mark_task_success(db, log.id, vector_id=ids[0])
                done += 1
                logger.info("vectorize 完成 news_id=%s", news_id)
            except Exception as exc:  # noqa: BLE001
                await mark_task_failed(db, log.id, str(exc))
                logger.exception("vectorize 失败 news_id=%s", news_id)
        await db.commit()
    return done


class WorkerSettings:
    """Arq Worker 配置：函数注册 + Redis 连接 + 并发。"""

    functions = [vectorize_news_batch, generate_summary_batch]
    redis_settings = ArqRedisSettings.from_dsn(settings.tasks.arq_redis_url)
    redis_settings.conn_timeout = 5
    redis_settings.conn_retries = 10
    redis_settings.conn_retry_delay = 2
    redis_settings.max_connections = 20
    max_jobs = settings.tasks.concurrency
    job_timeout = 300