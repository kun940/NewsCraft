"""新闻内容进出向量库"""
from datetime import datetime

from langchain_chroma import Chroma

from config.settings import settings
from core.rag_core.models import create_embeddings

NEWS_COLLECTION = settings.vector_db.collection

def get_news_store()-> Chroma:
    """持久化新闻向量集合（cosine 距离，local 落盘到 persist_directory）。"""
    return Chroma(
        collection_name=NEWS_COLLECTION,
        embedding_function=create_embeddings(),
        persist_directory=settings.vector_db.persist_directory,
        collection_metadata={"hnsw:space": "cosine"},
    )


"""批量写入新闻向量。id 复用新闻主键，重复写同一 id 自动覆盖（等价 upsert）。"""
def add_news(documents:list) -> list[str]:#chroma数据的id是字符串
    ids=[str(d.metadata["news_id"])for d in documents]
    get_news_store().add_documents(documents, ids=ids)
    return ids

"""根据新闻id删除chroma里的新闻数据，保持 MySQL 与 Chroma 一致。"""
def delete_news(news_id:int)->None:
    get_news_store().delete(ids=[str(news_id)])

def get_news_by_ids(news_ids: list[int]) -> list[dict]:
    """按 id 批量取回 document/metadata（溯源、调试用）。"""
    got = get_news_store().get(ids=[str(i) for i in news_ids])
    rows = []
    for i, doc in enumerate(got.get("documents") or []):
        meta = (got.get("metadatas") or [])[i] or {}
        rows.append({"news_id": meta.get("news_id"), "title": meta.get("title"), "content": doc})
    return rows

"""持久化用户画像向量，与新闻向量共用一个库的持久化目录"""
USER_COLLECTION=settings.recommend.user_collection
def get_user_store()-> Chroma:
    return Chroma(
        collection_name=USER_COLLECTION,
        embedding_function=create_embeddings(),
        persist_directory=settings.vector_db.persist_directory,
        collection_metadata={"hnsw:space": "cosine"},
    )

def upsert_user_interest(user_id: int, vector: list[float], tags: str) -> None:
    """
    写入/覆盖用户兴趣画像（幂等 upsert）。
    id = user_id 字符串；embedding 直接传入合成好的向量
    """
    get_user_store()._collection.upsert(
        ids=[str(user_id)],
        embeddings=[vector],
        metadatas=[{
            "user_id": user_id,
            "interest_tags": tags,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }],
    )