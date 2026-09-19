"""
入库后 AI 加工客户端

爬虫把新新闻写入 MySQL 后，自动向后端推送两条异步任务：
    - POST {base}/api/ai/news/vector   向量化（body: {"newsIds": [...]}）
    - POST {base}/api/ai/news/summary  摘要（body: {"news_ids": [...]}）

设计说明：
    - 后端接口只负责「受理入队」（arq 队列），真正的向量化 / 摘要由后端
      arq worker 异步执行；本客户端只发请求、不等待执行结果。
    - 接口幂等：后端会过滤已加工（vectorize 查 news_vector_id、summary 查
      ai_summary）的新闻，重复触发同一批 ID 无害。
    - 失败策略：后端不可达 / 请求失败时按配置重试，重试耗尽仅记 warning，
      不阻塞爬虫入库主流程 —— 漏掉的新闻可后续用空 body 调用接口补做。
"""
from __future__ import annotations

import logging
import time

import requests

from config import settings

logger = logging.getLogger(__name__)

# 两个接口的请求体字段不一致（后端 schema 约定如此），分别指定
_VECTOR_BODY_FIELD = "newsIds"
_SUMMARY_BODY_FIELD = "news_ids"


class AiClientError(Exception):
    """AI 加工接口调用失败（重试耗尽后抛出）"""


class AiClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        self.base_url = (base_url or settings.ai.base_url).rstrip("/")
        self.timeout = timeout if timeout is not None else settings.ai.timeout
        self.session = requests.Session()
        self.session.headers.update({"Content-Type": "application/json"})

    # ---------------- 对外接口 ----------------

    def process_new_news(self, news_ids: list[int]) -> None:
        """
       对新入库新闻触发向量化 + 摘要。

        任一接口失败只记日志，不抛异常，保证爬虫主流程不受影响。
        """
        if not news_ids:
            return
        if not settings.ai.enabled:
            logger.info("AI 加工已关闭（AI_PROCESS_ENABLED=false），跳过 %s 条新闻的加工触发", len(news_ids))
            return

        logger.info("触发 AI 加工：%s 条新闻（id=%s）", len(news_ids), news_ids[:10])
        self._vectorize(news_ids)
        self._summarize(news_ids)

    # ---------------- 内部实现 ----------------

    def _vectorize(self, news_ids: list[int]) -> None:
        try:
            resp = self._post("/api/ai/news/vector", {_VECTOR_BODY_FIELD: news_ids})
        except AiClientError as exc:
            logger.warning("向量化任务触发失败：%s（后续可用空 body 调用该接口补做）", exc)
            return
        data = (resp.get("data") or {}).get("detail") or []
        queued = sum(1 for item in data if item.get("status") == "queued")
        logger.info("向量化受理成功：queued=%s（接口返回）", queued)

    def _summarize(self, news_ids: list[int]) -> None:
        try:
            resp = self._post("/api/ai/news/summary", {_SUMMARY_BODY_FIELD: news_ids})
        except AiClientError as exc:
            logger.warning("摘要任务触发失败：%s（后续可用空 body 调用该接口补做）", exc)
            return
        data = (resp.get("data") or {}).get("detail") or []
        queued = sum(1 for item in data if item.get("status") == "queued")
        logger.info("摘要受理成功：queued=%s（接口返回）", queued)

    def _post(self, path: str, body: dict) -> dict:
        """POST JSON，失败按配置重试；重试耗尽抛 AiClientError"""
        url = f"{self.base_url}{path}"
        last_err: Exception | None = None
        for attempt in range(1, settings.ai.max_retries + 1):
            try:
                resp = self.session.post(url, json=body, timeout=self.timeout)
                if resp.ok:
                    return resp.json()
                last_err = AiClientError(f"HTTP {resp.status_code}: {path}（{resp.text[:200]}）")
                logger.warning("第 %s 次请求失败：%s", attempt, last_err)
            except requests.RequestException as exc:
                last_err = exc
                logger.warning("第 %s 次请求异常：%s", attempt, exc)

            if attempt < settings.ai.max_retries:
                time.sleep(settings.ai.retry_backoff * attempt)

        raise AiClientError(f"请求失败（已重试 {settings.ai.max_retries} 次）：{url}") from last_err
