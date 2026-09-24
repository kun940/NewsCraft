import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from core.rag_core.rag_service import _get_bm25_retriever, _get_dense_retriever
from core.rag_core.vector_store import get_user_store
from routers import news, users, favorite, history, ai_rag

from fastapi.middleware.cors import CORSMiddleware

from utils.cache import get_redis
from utils.get_arq_pool import get_arq_pool
from utils.get_db_session import AsyncSessionLocal
from sqlalchemy import text

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- 启动段：接收任何请求之前 ----
    # 1) MySQL：校验可用 + 预建连接
    async with AsyncSessionLocal() as session:
        await session.execute(text("SELECT 1"))
    # 2) Redis：ping 才真正建连
    redis = await get_redis()
    await redis.ping()
    # 3) arq 池：校验 Redis db1
    await get_arq_pool()
    # 4) Chroma 用户库（新闻库由下面稠密路顺带打开）
    get_user_store()
    # 5) 重活：BM25 全量索引 + 稠密 retriever
    async with AsyncSessionLocal() as session:
        await _get_bm25_retriever(session)
    _get_dense_retriever()
    logger.info("lifespan 启动完成，资源已预热")
    yield


app = FastAPI(lifespan=lifespan)

#跨域资源共享中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173",  #前端地址
    "http://127.0.0.1:5173"],#允许的源，开发阶段允许所有源，生产环境需要指定源
    allow_credentials=True,#允许携带cookie
    allow_methods=["*"],#允许的请求方法
    allow_headers=["*"],#允许的请求头
)

app.include_router(news.router)
app.include_router(users.router)
app.include_router(favorite.router)
app.include_router(history.router)
app.include_router(ai_rag.router)