"""
HTTP 抓取模块

职责：
    - 统一 User-Agent / 超时
    - 失败自动重试（指数退避 + 抖动）
    - 请求间隔限速（尊重目标站点负载，robots.txt 已允许抓取新闻页）
    - 响应编码检测：HTTP 头 charset → HTML <meta> charset → 内容探测兜底
      （避免内容探测对部分页面误判导致中文乱码）

对外只暴露 Fetcher.get(url) -> str，失败重试耗尽后抛 FetchError。
"""
from __future__ import annotations

import codecs
import logging
import random
import re
import time
from typing import Optional

import requests

from config import settings

logger = logging.getLogger(__name__)

# requests 未显式声明 charset 时的兜底编码（不能当作真实编码使用）
_FALLBACK_ENCODINGS = {"iso-8859-1", "ascii", "windows-1252", "latin-1"}


class FetchError(Exception):
    """抓取失败（重试耗尽后抛出）"""


def _detect_encoding(resp: requests.Response) -> str:
    """
    确定响应文本编码，优先级：
        1. HTTP 响应头声明的 charset
        2. HTML <meta charset=...> 声明（中文站最可靠的信号）
        3. 内容探测（apparent_encoding）兜底
    """
    header_enc = resp.encoding
    if header_enc and header_enc.lower() not in _FALLBACK_ENCODINGS:
        return header_enc

    meta = re.search(
        rb"""<meta[^>]+charset=["']?\s*([\w-]+)""",
        resp.content[:8192],
        re.IGNORECASE,
    )
    if meta:
        enc = meta.group(1).decode("ascii", errors="ignore")
        try:
            codecs.lookup(enc)
            return enc
        except LookupError:
            logger.warning("页面声明了未知编码 %s，忽略", enc)

    return resp.apparent_encoding or "utf-8"


class Fetcher:
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": settings.crawl.user_agent})
        self._last_request_at: float = 0.0

    def _throttle(self) -> None:
        """保证两次请求间隔不小于 request_interval 秒"""
        elapsed = time.time() - self._last_request_at
        interval = settings.crawl.request_interval
        if elapsed < interval:
            time.sleep(interval - elapsed)

    def get(self, url: str) -> str:
        """GET 请求，返回响应文本；连续失败重试后抛 FetchError"""
        last_err: Optional[Exception] = None
        for attempt in range(1, settings.crawl.max_retries + 1):
            self._throttle()
            try:
                resp = self.session.get(url, timeout=settings.crawl.timeout)
                self._last_request_at = time.time()
                if resp.status_code == 200:
                    resp.encoding = _detect_encoding(resp)
                    return resp.text
                last_err = FetchError(f"HTTP {resp.status_code}: {url}")
                logger.warning("第 %s 次请求失败：%s", attempt, last_err)
            except requests.RequestException as exc:
                last_err = exc
                logger.warning("第 %s 次请求异常：%s", attempt, exc)

            if attempt < settings.crawl.max_retries:
                time.sleep(settings.crawl.retry_backoff * attempt + random.uniform(0, 0.5))

        raise FetchError(f"请求失败（已重试 {settings.crawl.max_retries} 次）：{url}") from last_err
