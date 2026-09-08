"""
爬虫全局配置中心

配置优先级（从高到低）：
    1. 系统环境变量
    2. .env 文件（先加载爬虫目录下的 .env，再加载项目根目录 .env 覆盖同名项）
    3. 下方默认值

项目根目录的 .env 已含 MYSQL_PASSWORD，爬虫直接复用，
无需在爬虫目录重复维护数据库密码。
"""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# 爬虫代码/ 目录与项目根目录（与 后端代码/ 平级）
CRAWLER_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CRAWLER_DIR.parent

# 依次加载爬虫目录与项目根目录的 .env；根目录同名变量覆盖爬虫目录
load_dotenv(CRAWLER_DIR / ".env", encoding="utf-8")
load_dotenv(PROJECT_ROOT / ".env", encoding="utf-8", override=True)


def _get(name: str, default: str) -> str:
    return os.environ.get(name, default)


class DatabaseConfig:
    """MySQL 连接配置（与后端 config.yaml 的 database 段对齐）"""

    host = _get("DB_HOST", "localhost")
    port = int(_get("DB_PORT", "3306"))
    user = _get("DB_USER", "root")
    password = _get("MYSQL_PASSWORD", "")
    name = _get("DB_NAME", "newscraft_app")
    charset = _get("DB_CHARSET", "utf8mb4")

    @property
    def url(self) -> str:
        return (
            f"mysql+pymysql://{self.user}:{self.password}"
            f"@{self.host}:{self.port}/{self.name}?charset={self.charset}"
        )


class CrawlConfig:
    """爬取目标与策略配置"""

    # ---- 数据源（默认网易新闻，图片覆盖率远高于中新网） ----
    # 可选值：netease（网易新闻频道页） / chinanews（中新网 RSS 即时新闻）
    source = "netease"
    source_home = "https://www.163.com"

    # 中新网 RSS 即时新闻（source=chinanews 时使用）
    rss_url = "http://www.chinanews.com.cn/rss/scroll-news.xml"

    # 网易频道列表页（source=netease 时使用）：(分类名, 列表页 URL)
    # 频道页为服务端渲染 HTML，条目按时间倒序（最新在前）
    netease_channels = [
        ("国内", "https://news.163.com/domestic/"),
        ("国际", "https://news.163.com/world/"),
        ("社会", "https://news.163.com/society/"),
        ("科技", "https://tech.163.com/"),
        ("财经", "https://money.163.com/"),
        ("体育", "https://sports.163.com/"),
        ("娱乐", "https://ent.163.com/"),
    ]
    netease_per_channel = 8      # 每个频道最多取前 N 条
    max_age_days = 3             # 详情发布时间超过该天数的新闻跳过

    # ---- 网络请求 ----
    user_agent = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 NewsCraftCrawler/1.0"
    )
    timeout = 15                  # 单次请求超时（秒）
    max_retries = 3               # 失败重试次数
    retry_backoff = 1.5           # 重试基础间隔（秒，指数退避）
    request_interval = 0.5        # 两次请求最小间隔（秒），礼貌限速
    workers = 4                   # 详情页抓取并发线程数

    # ---- 运行参数 ----
    max_items = 0                 # 单次运行最多入库条数，0 表示不限制

    # ---- 分类映射（中新网）：URL 一级路径段 → 数据库 news_category.name ----
    category_map = {
        "gn": "国内",
        "gj": "国际",
        "aseaninfo": "国际",      # 东盟频道
        "sh": "社会",
        "jk": "社会",             # 健康频道
        "ty": "体育",
        "yl": "娱乐",
        "cj": "财经",
        "kj": "科技",
        "it": "科技",
    }
    default_category = "国内"      # 未匹配路径段（edu/auto 等）的兜底分类

    # 排除的 URL 特征（中新网）：视频页(/shipin/)、图片图集页(/tp/)等无文字正文，直接跳过不抓
    exclude_url_patterns = ("/shipin/", "/video/", "/live/", "/tp/")

    # ---- 运行时文件 ----
    state_file = CRAWLER_DIR / "data" / "crawled_urls.json"   # 已抓 URL 状态（断点续爬）
    log_dir = CRAWLER_DIR / "logs"

    @property
    def source_name(self) -> str:
        return "网易新闻" if self.source == "netease" else "中国新闻网"


class Settings:
    database = DatabaseConfig()
    crawl = CrawlConfig()


settings = Settings()
