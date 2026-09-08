"""
解析模块

1) parse_rss：解析中新网 RSS 2.0 即时新闻列表
   - 字段：title / link / description / pubDate
   - 分类由 URL 路径段映射得到（见 config.crawl.category_map）

2) parse_detail：解析中新网新闻详情页（HTML）
   - 标题   h1.content_left_title
   - 正文   div.left_zw（仅取 <p> 段落文本）
   - 发布时间 span#pubtime_baidu（回退 div.content_left_time）
   - 作者   span#author_baidu（"作者：XXX"）
   - 来源   span#source_baidu
   - 封面图 div.left_zw 内第一张 <img>
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import urljoin
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class RawNewsItem:
    """RSS 列表中的一条新闻（尚未抓详情）"""

    title: str
    url: str
    description: str = ""
    pub_date: Optional[datetime] = None
    category: str = ""


@dataclass
class NewsDetail:
    """详情页解析结果"""

    title: str
    content: str
    publish_time: Optional[datetime] = None
    author: str = ""
    source: str = ""
    image: str = ""


# ---------------------------------------------------------------- RSS 列表

def parse_rss(xml_text: str) -> list[RawNewsItem]:
    """解析 RSS 2.0，返回新闻条目列表（跳过缺 title / link 的脏条目）"""
    items: list[RawNewsItem] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.error("RSS XML 解析失败：%s", exc)
        return items

    for node in root.iter("item"):
        title = (node.findtext("title") or "").strip()
        link = (node.findtext("link") or "").strip()
        if not title or not link:
            continue
        items.append(
            RawNewsItem(
                title=title,
                url=link,
                description=_clean_text(node.findtext("description") or ""),
                pub_date=_parse_rfc822(node.findtext("pubDate") or ""),
                category=category_from_url(link),
            )
        )
    return items


def category_from_url(url: str) -> str:
    """按 URL 一级路径段映射数据库分类名，未匹配用兜底分类"""
    rest = url.split("//", 1)[-1]
    path = rest.split("/", 1)[1] if "/" in rest else ""
    seg = path.split("/")[0]
    return settings.crawl.category_map.get(seg, settings.crawl.default_category)


# ---------------------------------------------------------------- 详情页

def parse_detail(html_text: str) -> Optional[NewsDetail]:
    """解析详情页；缺少标题或正文容器时返回 None"""
    soup = BeautifulSoup(html_text, "lxml")

    h1 = soup.select_one("h1.content_left_title")
    body_div = soup.select_one("div.left_zw")
    if not h1 or not body_div:
        logger.debug("详情页缺少标题或正文容器，跳过")
        return None

    title = h1.get_text(strip=True)

    paragraphs = [p.get_text(strip=True) for p in body_div.find_all("p")]
    content = "\n".join(p for p in paragraphs if p)

    publish_time = _extract_publish_time(soup)
    author = _extract_author(soup)
    source = _extract_source(soup)
    image = _extract_cover_image(soup, body_div)

    return NewsDetail(
        title=title,
        content=content,
        publish_time=publish_time,
        author=author,
        source=source,
        image=image,
    )


# 图标 / 占位图 / 装饰图特征（src 或 class 命中则跳过）
_ICON_PATTERNS = (
    "logo", "toparr", "arrow", "/default/", "icon", "placeholder",
    "1x1", "blank", ".gif", "share_", "qrcode", "badge",
)


def _extract_cover_image(soup: BeautifulSoup, body_div) -> str:
    """
    提取新闻封面图，优先级：
        1. 正文 left_zw 内第一张真实配图（过滤图标/装饰图/过小图）
        2. og:image 社交分享图（部分站点在此声明封面）
    纯文字新闻无任何配图时返回空串，由前端占位兜底。
    """
    for img in body_div.find_all("img"):
        src = _img_src(img)
        if not src:
            continue
        if _is_icon_or_small(img, src):
            continue
        return urljoin(settings.crawl.source_home, src)

    og = soup.find("meta", attrs={"property": "og:image"})
    if og and og.get("content"):
        return og["content"].strip()
    return ""


def _img_src(img) -> str:
    """兼容懒加载写法：src / data-src / data-original"""
    return (img.get("src") or img.get("data-src") or img.get("data-original") or "").strip()


def _is_icon_or_small(img, src: str) -> bool:
    """判断是否图标/装饰图：路径特征命中，或宽高属性过小（<100px）"""
    low = (src + " " + " ".join(img.get("class") or [])).lower()
    if any(p in low for p in _ICON_PATTERNS):
        return True
    try:
        w = int(img.get("width") or 0)
        h = int(img.get("height") or 0)
    except ValueError:
        w = h = 0
    if w and h and (w < 100 or h < 100):
        return True
    return False


def _extract_publish_time(soup: BeautifulSoup) -> Optional[datetime]:
    """发布时间：优先隐藏域 span#pubtime_baidu，回退 div.content_left_time 文本"""
    pub_el = soup.select_one("span#pubtime_baidu")
    if pub_el:
        dt = _parse_dt(pub_el.get_text(strip=True))
        if dt:
            return dt
    time_el = soup.select_one("div.content_left_time")
    if time_el:
        m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{1,2}):(\d{2})", time_el.get_text())
        if m:
            try:
                return datetime(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]))
            except ValueError:
                pass
    return None


def _extract_author(soup: BeautifulSoup) -> str:
    author_el = soup.select_one("span#author_baidu")
    if author_el:
        return re.sub(r"^作者[：:]?", "", author_el.get_text(strip=True)).strip()
    return ""


def _extract_source(soup: BeautifulSoup) -> str:
    source_el = soup.select_one("span#source_baidu")
    if source_el:
        return re.sub(r"^来源[：:]?", "", source_el.get_text(strip=True)).strip()
    return ""


# ---------------------------------------------------------------- 工具函数

def _clean_text(text: str) -> str:
    """压缩空白字符，去除首尾空白"""
    return re.sub(r"\s+", " ", text).strip()


def _parse_rfc822(value: str) -> Optional[datetime]:
    """RSS pubDate：'Mon, 7 Sep 2026 15:54:04 +0800' → naive datetime"""
    try:
        dt = parsedate_to_datetime(value)
        return dt.replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def _parse_dt(value: str) -> Optional[datetime]:
    """'2026-09-07 15:54:04' 或 '2026-09-07 15:54' → datetime"""
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None
