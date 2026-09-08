"""
NewsCraft 新闻爬虫入口（默认数据源：网易新闻）

用法示例：
    python main.py                    # 抓取默认数据源全部新条目并入库
    python main.py --limit 10         # 本次最多处理 10 条
    python main.py --source chinanews # 临时切换为中国新闻网（RSS 即时新闻）
    python main.py --workers 8        # 8 线程并发抓详情
    python main.py --interval 1.0     # 请求间隔 1 秒（更保守的限速）

说明：
    - 数据源在 config.py 的 crawl.source 配置（netease / chinanews）；
    - 需要先按 requirements.txt 安装依赖；
    - 数据库连接复用项目根目录 .env 的 MYSQL_PASSWORD，也可用环境变量覆盖；
    - 重复运行幂等：已入库 / 已抓过的新闻自动跳过。
"""
from __future__ import annotations

import argparse
import logging
import sys

from config import settings
from crawler.pipeline import run

logger = logging.getLogger("main")


def setup_logging(level: str) -> None:
    settings.crawl.log_dir.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(settings.crawl.log_dir / "crawler.log", encoding="utf-8"),
    ]
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="NewsCraft 新闻爬虫")
    parser.add_argument(
        "--source",
        choices=["netease", "chinanews"],
        default=None,
        help="临时切换数据源（默认用 config.py 的 crawl.source）",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="本次最多处理条数，0 表示不限制（默认 0）",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=settings.crawl.workers,
        help=f"详情页抓取并发线程数（默认 {settings.crawl.workers}）",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=settings.crawl.request_interval,
        help=f"两次请求最小间隔秒数（默认 {settings.crawl.request_interval}）",
    )
    parser.add_argument("--log-level", default="INFO", help="日志级别：DEBUG/INFO/WARNING/ERROR")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    setup_logging(args.log_level)
    settings.crawl.workers = max(1, args.workers)
    settings.crawl.request_interval = max(0.1, args.interval)

    logger.info("===== NewsCraft 爬虫启动：%s =====", settings.crawl.source_name)
    stats = run(limit=args.limit, source=args.source)

    print(
        f"\n[完成] 列表解析 {stats.list_items} 条 | 本次处理 {stats.pending} 条 | "
        f"新入库 {stats.inserted} 条 | 重复跳过 {stats.duplicated} 条 | "
        f"详情失败 {stats.detail_failed} 条 | 跳过 {stats.skipped} 条"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
