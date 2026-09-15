"""
RAG 问答服务（模块三主链路）：

    问题重写（可选） → bge-m3 向量化 → 混合检索（稠密 + BM25 RRF）
    → 上下文组装 → LLM 生成（流式 / 非流式）→ 引用溯源 → 写 ai_chat_record

对外提供：
    answer_question(db, user_id, question)   → dict（非流式，接口/验证直接用）
    chat_event_stream(db, user_id, question) → async generator（SSE 事件序列）
"""
import json
import logging

from langchain_core.documents import Document
from sqlalchemy import select

from config.settings import settings
from core.rag_core.models import create_chat_model
from core.rag_core.prompts import rag_prompt, rewrite_prompt
from core.rag_core.retriever import NewsBM25Retriever, rrf_fuse
from core.rag_core.vector_store import get_news_store
from crud.ai_crud import save_chat_record
from models.news_models import News

logger = logging.getLogger(__name__)

# 两条检索路都做进程级懒加载缓存：
#   BM25 索引：全量新闻 jieba 分词，构建成本秒级，绝不能在请求里做
#   稠密 retriever：VectorStoreRetriever 绑定 Chroma 实例，避免每次请求重新打开 sqlite
_bm25_retriever: NewsBM25Retriever | None = None
_dense_retriever = None


def _get_dense_retriever():
    """懒加载稠密路 retriever（langchain-chroma 原生：传 query 文本，内部自动向量化 + 检索）。"""
    global _dense_retriever
    if _dense_retriever is None:
        _dense_retriever = get_news_store().as_retriever(
            search_type="similarity",
            search_kwargs={"k": settings.rag.hybrid_candidates},
        )
    return _dense_retriever


async def _get_bm25_retriever(db) -> NewsBM25Retriever:
    """懒加载 BM25 索引（全量新闻 title+content，与 document_factory 拼接一致）。"""
    global _bm25_retriever
    if _bm25_retriever is None:
        rows = await db.execute(select(News.id, News.title, News.content))
        docs = [
            Document(
                page_content=f"{title}\n{content}",
                metadata={"news_id": news_id, "title": title},
            )
            for news_id, title, content in rows.all()
        ]
        _bm25_retriever = NewsBM25Retriever(docs)
    return _bm25_retriever


def invalidate_bm25_cache() -> None:
    """新闻新增/删除后调用，强制下次重建 BM25 索引（稠密路不用管，Chroma 实时查询）。"""
    global _bm25_retriever
    _bm25_retriever = None


async def _rewrite_question(question: str) -> str:
    """口语化问题 → 检索式 query。开关控制；LLM 失败降级用原问题。"""
    if not settings.rag.enable_question_rewrite:
        return question
    try:
        resp = await create_chat_model().ainvoke(rewrite_prompt.format_messages(question=question))
        rewritten = (resp.content or "").strip()
        if rewritten:
            logger.info("问题重写: %s → %s", question, rewritten)
            return rewritten
    except Exception:  # noqa: BLE001
        logger.warning("问题重写失败，使用原问题", exc_info=True)
    return question


def _hybrid_retrieve(query: str, bm25: NewsBM25Retriever) -> list[tuple[Document, float]]:
    """双路召回 + RRF 融合 → [(Document, rrf_score)]，取 recall_top_k 条。"""
    # 稠密路：as_retriever 内部完成 bge-m3 向量化 + 相似度检索，返回按相似度降序的 Document
    dense_docs = _get_dense_retriever().invoke(query)
    # 稀疏路：BM25 分数降序
    sparse_docs = bm25.get_relevant_documents(query, top_k=settings.rag.hybrid_candidates)
    logger.info("混合检索: dense=%s sparse=%s", len(dense_docs), len(sparse_docs))
    return rrf_fuse([dense_docs, sparse_docs], k=settings.rag.rrf_k, top_n=settings.rag.recall_top_k)


def _build_context(hits: list[tuple[Document, float]]) -> tuple[str, list[dict]]:
    """召回结果 → (上下文文本, 引用 sources)。编号与引用一一对应，受 max_context_len 限制。"""
    parts: list[str] = []
    sources: list[dict] = []
    used = 0
    for i, (doc, _score) in enumerate(hits, start=1):
        title = doc.metadata.get("title", "")
        seg = f"[{i}] {title}\n{doc.page_content}\n\n"
        if used + len(seg) > settings.rag.max_context_len:
            remain = settings.rag.max_context_len - used
            if remain > 50:                     # 最后一条截断塞入，但不再计入 sources
                parts.append(seg[:remain])
            break
        parts.append(seg)
        used += len(seg)
        sources.append({"news_id": int(doc.metadata["news_id"]), "title": title})
    return "".join(parts), sources


async def _stream_answer(messages: list) -> None:
    """LLM 流式生成，逐条产出非空增量文本。"""
    llm = create_chat_model()
    async for chunk in llm.astream(messages):
        piece = chunk.content if isinstance(chunk.content, str) else ""
        if piece:
            yield piece


async def _non_stream_answer(messages: list) -> str:
    """LLM 一次性生成完整回答。"""
    resp = await create_chat_model().ainvoke(messages)
    return resp.content or ""


async def answer_question(db, user_id: int, question: str) -> dict:
    """完整 RAG 一次问答：重写 → 检索 → 生成 → 溯源 → 落库。"""
    query = await _rewrite_question(question)
    hits = _hybrid_retrieve(query, await _get_bm25_retriever(db))
    context, sources = _build_context(hits)
    messages = rag_prompt.format_messages(context=context, question=question)

    answer = await _non_stream_answer(messages)
    record_id = await save_chat_record(
        db, user_id, question, answer, [s["news_id"] for s in sources]
    )
    logger.info("chat 完成 user_id=%s record_id=%s sources=%s", user_id, record_id, len(sources))
    return {"record_id": record_id, "answer": answer, "sources": sources}


async def chat_event_stream(db, user_id: int, question: str):
    """
    SSE 事件序列（API 规范 5.4.1）：
        start → 0..n 个 delta → sources → done
        error 可在任意阶段后出现并终止（随后连接关闭）
    """
    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

    yield _sse("start", {"recordId": None})

    # 检索段（重写/混合检索/上下文）在流式开始前一次性算好
    query = await _rewrite_question(question)
    hits = _hybrid_retrieve(query, await _get_bm25_retriever(db))
    context, sources = _build_context(hits)
    messages = rag_prompt.format_messages(context=context, question=question)

    # 生成段：逐 token 产出 delta
    answer_parts: list[str] = []
    try:
        async for piece in _stream_answer(messages):
            answer_parts.append(piece)
            yield _sse("delta", {"content": piece})
    except Exception:  # noqa: BLE001
        logger.exception("chat 流式生成失败 user_id=%s", user_id)
        yield _sse("error", {"message": "AI 服务暂不可用，请稍后再试"})
        return

    # 生成完成 → 落库拿 recordId → 收尾事件
    answer = "".join(answer_parts)
    record_id = await save_chat_record(
        db, user_id, question, answer, [s["news_id"] for s in sources]
    )
    yield _sse("sources", {"sources": sources})
    yield _sse("done", {"answer": answer, "recordId": record_id, "sources": sources})