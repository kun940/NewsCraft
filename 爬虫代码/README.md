# NewsCraft 新闻爬虫（爬虫代码/）

基于 `newscraft_app` 数据库的新闻表及相关表设计的新闻爬虫，从主流新闻网站抓取新闻入库。
与 `后端代码/` 平级，独立运行，不依赖后端代码，只共享同一个 MySQL 数据库。

## 一、数据源

爬虫支持两种数据源，在 `config.py` 的 `crawl.source` 切换（也可用 `main.py --source` 临时覆盖）：

### 默认：网易新闻（netease，推荐）

| 维度 | 说明 |
|---|---|
| 时效性 | 各频道页服务端渲染，条目按时间倒序，当天新闻为主 |
| 有图率 | **实测约 90%**（正文配图），远高于中新网；无图的多为快讯/微博/收评等客观无图类型 |
| 分类 | 国内/国际/社会/科技/财经/体育/娱乐 7 个频道页，与库内分类一一对应 |
| 详情 | `www.163.com/dy/article/xxx.html` 等，标题 `h1.post_title`、正文 `div.post_body`、图片经 `nimg.ws.126.net` 代理 |

列表（7 个频道页）：

| 分类 | 频道页 |
|---|---|
| 国内 | https://news.163.com/domestic/ |
| 国际 | https://news.163.com/world/ |
| 社会 | https://news.163.com/society/ |
| 科技 | https://tech.163.com/ |
| 财经 | https://money.163.com/ |
| 体育 | https://sports.163.com/ |
| 娱乐 | https://ent.163.com/ |

### 备选：中国新闻网（chinanews，可切回）

RSS「即时新闻」实时滚动，列表稳定，但约 40% 为纯文字稿（记者会/公告/简讯），**有图率约 56%**。
列表：`http://www.chinanews.com.cn/rss/scroll-news.xml`（约 30 条/次）
详情：标题 `h1.content_left_title`、正文 `div.left_zw`、时间 `#pubtime_baidu`。

## 二、目录结构

```
爬虫代码/
├── main.py                 # CLI 入口：python main.py [--source X] [--limit N] ...
├── config.py               # 配置中心：DB 连接 / 数据源 / 分类映射 / 请求策略
├── requirements.txt        # 依赖清单
├── .env.example            # 可选覆盖项（默认复用项目根目录 .env 的 MYSQL_PASSWORD）
├── .gitignore
├── crawler/
│   ├── __init__.py
│   ├── fetcher.py          # HTTP 抓取：UA、超时、指数退避重试、请求限速、编码三级检测
│   ├── netease.py          # 网易适配器：频道页列表提取 + 详情页解析（含图片代理解码）
│   ├── parser.py           # 中新网适配器：RSS 列表解析 + 详情页正文解析
│   ├── models.py           # SQLAlchemy 模型：news_category / news（与后端字段对齐）
│   ├── storage.py          # 入库：建表、分类兜底创建、标题查重插入、URL 状态持久化
│   └── pipeline.py         # 流水线编排：按数据源分派 → 列表 → 过滤 → 并发抓详情 → 串行入库
├── data/
│   └── crawled_urls.json   # 已抓 URL 状态（自动生成，断点续爬，git 忽略）
└── logs/
    └── crawler.log         # 运行日志（自动生成）
```

## 三、与数据库的对应关系

| 数据库表 | 爬虫行为 |
|---|---|
| `news_category` | 网易：频道名即分类名；中新网：按 URL 路径段映射（`category_map`）。分类不存在时自动创建（`sort_order` 取最大值+1） |
| `news` | 写入 title / description / content / image / author / category_id / views(0) / publish_time；RAG 预留 4 字段（news_vector_id、ai_summary、ai_tags、content_keywords）留空 |
| `related_news` / `favorite` / `history` / `ai_chat` | 用户行为表，爬虫不触碰 |

中新网 URL 路径段 → 分类映射（`config.py` 中 `category_map` 可调）：

| URL 一级路径 | 数据库分类 |
|---|---|
| `/gn/` | 国内 |
| `/gj/` `/aseaninfo/` | 国际 |
| `/sh/` `/jk/` | 社会 |
| `/ty/` | 体育 |
| `/yl/` | 娱乐 |
| `/cj/` | 财经 |
| `/kj/` `/it/` | 科技 |
| 其他（edu/auto 等） | 国内（兜底，可配置） |

## 四、封面图提取策略

`image` 字段（封面图）**只保留真实正文配图**，两种数据源各自的提取规则：

| 数据源 | 正文容器 | 图片规则 |
|---|---|---|
| 网易 | `div.post_body` | 第一张真实 `<img>`；过滤 logo/icon/占位/1x1/.gif；`nimg.ws.126.net` 代理解码还原真实 URL；http 统一转 https |
| 中新网 | `div.left_zw` | 第一张通过过滤的 `<img>`（过滤图标/宽高 <100px 小图，兼容 `data-src` 懒加载）；回退 `og:image` |

> 实测说明：网易新闻有图率约 90%，无图的多为快讯（"每经AI快讯"等）、微博转发、盘后收评等
> 源站本身无配图的类型；中新网约 40% 纯文字稿（记者会/公告/简讯）。二者均属数据源客观情况，
> 无法通过抓取补图，前端已做占位展示。

## 五、数据流

```
网易：7 个频道页列表 → 每频道取前 N 条（netease_per_channel=8，默认 56 条）
中新网：RSS 即时新闻列表（约 30 条）
   │  fetcher.get()（重试/限速）
   ▼
过滤：① URL 状态文件查重 ② 中新网排除视频/图集页 ③ --limit 截断
ThreadPoolExecutor（默认 4 线程）并发抓详情页
   │
   ▼  网易 parse_detail() / 中新网 parse_detail()：标题/正文/时间/作者/来源/封面图
主线程串行入库（SQLAlchemy Session 单线程，避免会话跨线程）
   │  ① 分类兜底创建 → ② 标题查重 → ③ 插入 news → ④ 标记 URL 状态
   ▼
data/crawled_urls.json + logs/crawler.log
```

网易数据源额外做**时效过滤**：详情发布时间超过 `max_age_days`（默认 3 天）的旧闻跳过，
避免频道页混入的历史文章入库（实测可拦截频道页顶部偶发的旧文）。

## 六、安装与运行

```bash
# 1. 安装依赖（复用项目虚拟环境）
cd 后端代码/..  # 项目根目录
.venv\Scripts\python.exe -m pip install -r 爬虫代码\requirements.txt

# 2. 运行（数据库连接自动复用项目根目录 .env 的 MYSQL_PASSWORD）
cd 爬虫代码
..\.venv\Scripts\python.exe main.py                    # 默认网易源，抓取全部新条目
..\.venv\Scripts\python.exe main.py --source chinanews # 临时切回中新网 RSS
..\.venv\Scripts\python.exe main.py --limit 10         # 本次最多处理 10 条
..\.venv\Scripts\python.exe main.py --workers 8        # 8 线程并发抓详情
..\.venv\Scripts\python.exe main.py --interval 1.0     # 请求间隔放宽到 1 秒
```

命令行参数：

| 参数 | 默认 | 说明 |
|---|---|---|
| `--source` | config 默认 | 临时切换数据源：netease / chinanews |
| `--limit` | 0 | 本次最多处理条数，0 不限制 |
| `--workers` | 4 | 详情页抓取并发线程数 |
| `--interval` | 0.5 | 两次请求最小间隔（秒） |
| `--log-level` | INFO | DEBUG/INFO/WARNING/ERROR |

数据库连接可用环境变量覆盖：`DB_HOST` / `DB_PORT` / `DB_USER` / `MYSQL_PASSWORD` / `DB_NAME`。

## 七、去重与幂等策略

`news` 表未预留源 URL 字段，故采用双保险去重：

1. **本地 URL 状态文件**（`data/crawled_urls.json`）：记录每条 URL 的处理状态
   - `done`：已成功入库或判重跳过，不再抓取
   - `skipped`：无正文/不支持类型，永久跳过
   - 网络失败（FetchError）的条目不记录 → 下次运行自动重试（断点续爬）
2. **数据库标题查重**：入库前 `SELECT id FROM news WHERE title=?`，同题新闻跳过

因此**重复运行完全幂等**，可安全接入定时调度：

- Windows：任务计划程序，如 `schtasks /create /tn NewsCrawler /tr "..." /sc hourly`
- 或脚本循环：`while ($true) { python main.py; Start-Sleep 3600 }`

> 可选增强：如需对源 URL 做数据库级唯一约束，可执行
> `ALTER TABLE news ADD COLUMN source_url VARCHAR(500) NULL, ADD UNIQUE KEY uk_source_url (source_url);`
> 并将 `insert_news` 的查重键从标题改为 source_url（需在模型与 parser 中相应调整）。

## 八、运行示例

```
[完成] 列表解析 2242 条 | 本次处理 34 条 | 新入库 32 条 | 重复跳过 0 条 | 详情失败 0 条 | 跳过 2 条
```

网易源首次运行实测：7 个频道页解析 2200+ 条链接，取每频道前 8 条共 56 条待抓，
新入库 46 条实时新闻（2026-09-07），**有图率约 90%**，7 个分类全覆盖；
跳过 2 条为频道页顶部混入的超龄旧闻（时效过滤生效）。
中新网源切回方式：`python main.py --source chinanews`（约 30 条/次，有图率约 56%）。

## 九、合规与礼貌抓取

- 已核对目标站 `robots.txt`，仅抓取允许的新闻页路径；
- 默认请求间隔 0.5s、失败指数退避、并发 4，避免对站点造成压力；
- 只抓公开新闻页面，不采集用户数据；内容版权归原站，仅入库供应用展示与检索。
