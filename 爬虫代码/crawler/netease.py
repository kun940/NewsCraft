"""
网易新闻数据源适配器

列表：各频道页（服务端渲染 HTML，条目按时间倒序，最新在前）
详情：www.163.com/dy/article/xxx.html 或 www.163.com/money/article/xxx.html 等

说明：
    - 网易详情页正文容器为 div.post_body，图片为真实配图（经 nimg.ws.126.net 代理转发）；
    - 图片提取时过滤 logo/icon/占位图，并解析 nimg 代理还原真实 URL（http 统一转 https）；
    - 正文去除「责任编辑：xxx」类尾注段落。
"""
from __future__ import annotations

import re
import urllib.parse
from datetime import datetime
from typing import Optional

from bs4 import BeautifulSoup

# 频道页文章链接：www.163.com/dy|money|news.../article/xxx.html
_LINK_RE = re.compile(r'href="(https?://[^"]+?/article/[^"]+\.html)"')
# 详情页发布时间：2026-09-07 13:56:16
_TIME_RE = re.compile(r"(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2}):(\d{2})")
# 来源：来源：新京报
_SOURCE_RE = re.compile(r"来源[:：]\s*([^<\s，。]{2,20})")
# 正文中应剔除的尾注/声明段落开头
_TAIL_PREFIXES = ("责任编辑", "特别声明", "本文来源", "原标题", "校对")
# 图片 URL 中的图标/占位特征
_IMG_NOISE = ("logo", "icon", "placeholder", "1x1", ".gif", "default/head")


def extract_links(html: str) -> list[str]:
    """从频道页提取文章链接（保持页面顺序，去重）"""
    return list(dict.fromkeys(_LINK_RE.findall(html)))


def parse_detail(html: str) -> Optional[dict]:
    """
    解析网易详情页，返回字段：
        title / content / publish_time(datetime|None) / source / image
    无标题或正文时返回 None（视为不可用页面）。
    """
    soup = BeautifulSoup(html, "lxml")

    title_el = soup.select_one("h1.post_title") or soup.select_one("h1")
    title = title_el.get_text(strip=True) if title_el else ""

    body = soup.select_one(".post_body") or soup.select_one(".post_text") or soup.select_one("div#content")
    paras: list[str] = []
    if body is not None:
        for p in body.find_all("p"):
            text = p.get_text(strip=True)
            if text and not text.startswith(_TAIL_PREFIXES):
                paras.append(text)
    content = "\n\n".join(paras)

    if not title or not content:
        return None

    return {
        "title": title,
        "content": content,
        "publish_time": _parse_time(html, soup),
        "source": _parse_source(html),
        "image": _extract_image(body) if body is not None else "",
    }


def _parse_time(html: str, soup: BeautifulSoup) -> Optional[datetime]:
    m = _TIME_RE.search(html)
    if m:
        try:
            return datetime(*map(int, m.groups()))
        except ValueError:
            pass
    meta = soup.select_one('meta[property="article:published_time"]')
    if meta and meta.get("content"):
        try:
            return datetime.fromisoformat(meta["content"].replace("Z", "+00:00").replace("+08:00", ""))
        except ValueError:
            pass
    return None


def _parse_source(html: str) -> str:
    m = _SOURCE_RE.search(html)
    return m.group(1).strip() if m else ""


def _extract_image(body) -> str:
    """正文内第一张真实配图：过滤图标/占位图，nimg 代理解码，http 转 https"""
    for img in body.find_all("img"):
        src = img.get("src") or img.get("data-src") or img.get("data-original") or ""
        if not src.startswith(("http", "//")):
            continue
        url = src if src.startswith("http") else "https:" + src
        if any(noise in url.lower() for noise in _IMG_NOISE):
            continue
        # nimg.ws.126.net 代理：?url= 参数内才是真实图片地址
        if "nimg.ws.126.net" in url and "url=" in url:
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
            raw = qs.get("url", [""])[0]
            if raw:
                url = raw
        if url.startswith("http://"):
            url = "https://" + url[len("http://"):]
        return url
    return ""
