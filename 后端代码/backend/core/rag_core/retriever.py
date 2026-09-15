"""
混合检索（模块三核心）：稠密向量 + BM25 稀疏双路召回，RRF 融合。

    dense  = Chroma 按问题向量召回（cosine 距离，越小越相似）
    sparse = jieba 中文分词 + rank_bm25 关键词召回
    RRF    = score(d) = Σ 1 / (k + rank_i(d))，按 news_id 聚合，天然去重

不依赖 langchain-community（无 1.x 稳定版），BM25 基于 rank_bm25 + jieba 自实现。
"""
import logging
from collections import defaultdict

import jieba
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)


class NewsBM25Retriever:
    """稀疏路：jieba 分词 + BM25Okapi。构造一次建索引，之后反复查询。"""

    def __init__(self, documents: list[Document]):
        self.documents = documents
        # BM25Okapi 需要分词后的词列表；索引只建一次，查询复用
        self._bm25 = BM25Okapi([jieba.lcut(d.page_content) for d in documents])
        logger.info("BM25 索引构建完成，共 %s 篇新闻", len(documents))

    def get_relevant_documents(self, query: str, top_k: int = 50) -> list[Document]:
        """按 BM25分数倒序返回 top_k 篇；分数为 0 的（完全没有关键词命中）不进候选。"""
        scores = self._bm25.get_scores(jieba.lcut(query))
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        return [self.documents[i] for i in ranked[:top_k] if scores[i] > 0]


def rrf_fuse(
    ranked_lists: list[list[Document]],
    k: int = 60,
    top_n: int = 5,
) -> list[tuple[Document, float]]:
    """
    RRF 融合多路排名结果：score(d) = Σ 1 / (k + rank_i(d))，rank 从 1 开始。
    按 metadata['news_id'] 聚合（同一新闻双路命中自动合并分数），
    返回 [(document, rrf_score)]，按分数降序取 top_n 条。
    """
    scores: dict[str, float] = defaultdict(float)
    doc_by_id: dict[str, Document] = {}
    for ranked in ranked_lists:
        for rank, doc in enumerate(ranked, start=1):      # rank 从 1 开始
            news_id = str(doc.metadata.get("news_id"))
            scores[news_id] += 1.0 / (k + rank)
            doc_by_id.setdefault(news_id, doc)
    ordered = sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
    return [(doc_by_id[news_id], score) for news_id, score in ordered[:top_n]]