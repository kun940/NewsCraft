# NewsCraft 智能新闻资讯平台

> 从「新闻采集」到「AI 加工 → 个性化推荐 → 知识库问答」的一体化新闻资讯系统。
> 技术骨架：FastAPI + MySQL + Redis + Vue3 + Chroma + Ollama（LangChain 1.x + Arq）。

---

## 一、项目简介

NewsCraft 是一个以新闻内容为核心的智能资讯平台，打通了**爬虫采集 → AI 结构化加工 → 向量检索 → 个性化推荐 → RAG 问答**的完整链路：

- **新闻从哪里来**：独立爬虫模块从网易新闻 / 中国新闻网抓取新闻入库（`爬虫代码/`）；
- **新闻如何被加工**：后端异步任务（Arq Worker）调用本地大模型，为每条新闻生成**AI 摘要、标签、关键词**，并用 Embedding 模型做**向量化**存入 Chroma；
- **用户能做什么**：分类浏览、搜索阅读、收藏、历史记录、基于行为画像的**个性化推荐**、基于站内新闻知识库的**智能问答**（引用溯源）。

项目保留传统 CRUD 资讯平台的全部能力，AI 能力以独立模块叠加，互不侵入。

## 二、功能特性

| 模块 | 能力 | 说明 |
| --- | --- | --- |
| 新闻浏览 | 分类列表 / 详情 / 分页 | 7 个分类（国内/国际/社会/科技/财经/体育/娱乐） |
| 用户体系 | 注册 / 登录 / 资料 / 改密 | Token 认证（`user_token` 表，签发即入库） |
| 收藏 | 添加 / 取消 / 列表 / 清空 | 收藏行为参与推荐画像计算 |
| 历史 | 浏览记录 / 删除 / 清空 | 浏览行为参与推荐画像计算 |
| AI 新闻加工 | 摘要 / 标签 / 关键词 / 向量化 | 异步批量执行，幂等可重投（模块一） |
| 个性化推荐 | 兴趣向量召回 / 热门兜底 | 行为加权 + 时间衰减，Redis 缓存（模块二） |
| RAG 问答 | 智能问答 / 问答历史 / 引用溯源 | 混合检索（稠密 + BM25），支持 SSE 流式（模块三） |
| 新闻爬虫 | 网易 / 中新网双数据源 | 断点续爬、标题查重、完全幂等，可定时调度 |

## 三、技术栈

| 层 | 技术 |
| --- | --- |
| 前端 | Vue 3 · Vite 7 · Vant 4 · Pinia · vue-router · vue-i18n · axios |
| 后端 | Python 3.13 · FastAPI · SQLAlchemy 2（异步，aiomysql）· pydantic-settings · uvicorn |
| 数据库 | MySQL 8.0（`newscraft_app`，utf8mb4）· Redis 7（缓存 db0 + 任务队列 db1） |
| 向量与模型 | Chroma（`news_vectors` / `user_interests` 集合）· Ollama（bge-m3 Embedding / qwen2.5 LLM）· LangChain 1.x · 自研 BM25 稀疏检索 |
| 异步任务 | Arq（复用 Redis，`tasks/worker.py`） |
| 爬虫 | requests + SQLAlchemy + ThreadPoolExecutor（`爬虫代码/`） |
| 部署 | Docker / docker-compose（MySQL、Redis、API、Worker、前端 nginx 5 容器编排）· uv 多阶段构建 |

> 模型层做了 Provider 抽象：`core/rag_core/models.py` 模型工厂按配置一键切换 **ollama（本地）/ deepseek / dashscope（通义）/ openai**，改配置不改代码。

## 四、系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端（Vue3 + Vant）                       │
│   新闻列表/详情/收藏/历史          AI 推荐区块 / 智能问答            │
└───────────────┬──────────────────────────────────┬─────────────┘
                │ /api/*（nginx 同源反代）          │ /api/ai/*
                ▼                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                        FastAPI 后端（:8000）                      │
│  routers: news / user / favorite / history   routers/ai_rag      │
│  core/rag_core：模型工厂 · 向量库 · 混合检索 · 摘要/问答链         │
└──────┬──────────────┬──────────────┬──────────────┬────────────┘
       ▼              ▼              ▼              ▼
   ┌───────┐      ┌───────┐      ┌────────┐    ┌──────────┐
   │ MySQL │      │ Redis │      │ Chroma │    │  Ollama  │
   │ 业务表 │      │缓存+队列│      │ 向量库  │    │ bge-m3 / │
   └───────┘      └───────┘      └────────┘    │ qwen2.5  │
       ▲              ▲                        └──────────┘
       │              │
   ┌───┴──────────────┴───┐     ┌──────────────────────┐
   │   arq Worker（异步）  │◄────│  新闻爬虫（爬虫代码/）  │
   │ 向量化/摘要/兴趣同步   │     │ 网易/中新网 → MySQL    │
   └──────────────────────┘     └──────────────────────┘
```

**核心数据流**：新闻入库 → 触发 AI 向量化 + 摘要（异步）→ 用户行为采集 → 兴趣向量建模 → 向量召回推荐（Redis 缓存 + 热门兜底）↔ 知识库 RAG 问答（引用溯源）。

## 五、目录结构

```
NewsCraft/
├── README.md                    # 项目说明（本文件）
├── 部署文档.md                  # 部署运维指南（Docker / 本地）
├── docker-compose.yml           # 一键编排：MySQL + Redis + API + Worker + 前端
├── Dockerfile.backend           # 后端镜像（uv 多阶段构建，INSTALL_AI 控制 AI 依赖）
├── Dockerfile.frontend          # 前端镜像（Vite 构建 + nginx 托管）
├── .env.example                 # 环境变量模板（复制为 .env 后填写）
├── pyproject.toml / uv.lock     # Python 依赖（ai 可选组：langchain/chroma/arq 等）
├── 后端代码/
│   └── backend/
│       ├── main.py              # FastAPI 入口（注册全部路由）
│       ├── config/              # config.yaml + settings.py（配置中心）
│       ├── routers/             # news / users / favorite / history / ai_rag
│       ├── core/rag_core/       # 模型工厂 / 向量库 / 混合检索 / 摘要·问答链
│       ├── tasks/worker.py      # Arq Worker（向量化 / 摘要 / 兴趣同步）
│       ├── models/ crud/ schemas/ utils/
│       └── chroma_db/           # 向量库本地持久化（运行时生成，git 忽略）
├── 爬虫代码/
│   ├── main.py                  # 爬虫 CLI 入口
│   ├── config.py                # 爬虫配置（数据源 / 分类映射 / 请求策略）
│   └── crawler/                 # fetcher / netease / parser / storage / pipeline / ai_client
├── 03-前端项目代码/xwzx-news/   # Vue3 前端（Vite + Vant）
├── scripts/migration/           # database.sql（建库建表）+ database_rag_upgrade.sql（AI 预留）
├── docs/                        # 架构 / API / 教程等文档（详见第九节）
└── api_smoke_test.py            # 后端接口冒烟测试脚本
```

## 六、快速开始

### 方式一：Docker 一键部署（推荐）

前置要求：Docker + Docker Compose。

```powershell
# 1. 准备环境变量（复制模板并填写真实值）
Copy-Item .env.example .env
#    编辑 .env：MYSQL_PASSWORD / SECRET_KEY / DEEPSEEK_API_KEY 必填

# 2. 构建并启动全部服务
docker compose up -d --build

# 3. 验证
#    前端：http://localhost:8080
#    后端接口文档：http://localhost:8000/docs
docker compose ps                    # 5 个服务均应为 running
docker compose logs -f backend-api   # 查看后端日志
```

> 容器内已通过 `EMBEDDING__BASE_URL=http://host.docker.internal:11434` 连接宿主机的 Ollama。
> AI 能力（向量化/推荐/问答）需要宿主机先装好 Ollama 并拉取模型，详见《部署文档.md》第 3 节。

### 方式二：本地开发

前置要求：Python 3.13 + uv（或 pip）、Node 20、MySQL 8、Redis 7、Ollama。

```powershell
# ---------- 1. 后端 ----------
cd "D:\learning programs\NewsCraft"
Copy-Item .env.example .env          # 填写 MYSQL_PASSWORD / SECRET_KEY / DEEPSEEK_API_KEY
uv sync --extra ai                   # 安装全部依赖（含 AI 可选组）

# 建库建表（先确认 MySQL 已启动、.env 密码正确）
mysql -u root -p < scripts\migration\database.sql
mysql -u root -p < scripts\migration\database_rag_upgrade.sql

# 启动 Ollama 并拉取模型（AI 功能依赖）
ollama pull bge-m3
ollama pull qwen2.5:7b

# 启动后端 API + 异步 Worker（两个终端，均在 backend 目录下）
cd 后端代码\backend
..\..\.venv\Scripts\python.exe -m uvicorn main:app --reload --port 8000
..\..\.venv\Scripts\python.exe -m arq tasks.worker.WorkerSettings

# ---------- 2. 前端 ----------
cd 03-前端项目代码\xwzx-news
npm install
npm run dev                          # http://localhost:5173

# ---------- 3. 新闻爬虫（可选）----------
cd 爬虫代码
..\.venv\Scripts\python.exe main.py  # 默认网易源，抓取新条目入库
```

## 七、数据库初始化与 AI 加工

数据库由两个幂等脚本初始化，`docker compose up` 首次启动时也会自动执行：

| 脚本 | 内容 |
| --- | --- |
| `scripts/migration/database.sql` | 建库 `newscraft_app` + 8 张业务表（user / user_token / news_category / news / related_news / favorite / history / ai_chat） |
| `scripts/migration/database_rag_upgrade.sql` | news 表加 4 个 AI 预留字段、user 表加 2 个预留字段，新建 `ai_chat_record`（问答历史）与 `news_vector_log`（AI 任务日志） |

**存量新闻 AI 加工**（新新闻由爬虫自动触发，存量需手动补做一次，需登录 token）：

```powershell
# 全量向量化 + 全量摘要（缺省 body 即处理所有未加工新闻）
curl.exe -X POST http://localhost:8000/api/ai/news/vector -H "Authorization: Bearer <TOKEN>" -d "{}"
curl.exe -X POST http://localhost:8000/api/ai/news/summary -H "Authorization: Bearer <TOKEN>" -d "{}"
```

加工结果写入 `news.ai_summary / ai_tags / content_keywords / news_vector_id`，执行状态记录在 `news_vector_log`（幂等依据）。

## 八、新闻爬虫

独立于后端运行，只共享同一个 MySQL 数据库。默认抓取**网易新闻 7 个频道页**（每频道前 8 条，正文配图覆盖率约 90%），可随时切换**中新网 RSS 即时新闻**。

```powershell
cd 爬虫代码
..\.venv\Scripts\python.exe main.py                    # 默认网易源
..\.venv\Scripts\python.exe main.py --source chinanews # 切换中新网
..\.venv\Scripts\python.exe main.py --limit 10 --workers 8
```

- **完全幂等**：URL 状态文件（`data/crawled_urls.json`）+ 数据库标题查重双保险，可安全接入定时任务；
- **自动联动 AI**：新入库新闻自动触发后端向量化 + 摘要（失败不影响入库，可空 body 补做）；
- 详细说明见《新闻爬取与加工》文档。

## 九、相关文档

| 文档 | 位置 | 内容 |
| --- | --- | --- |
| **部署文档** | `部署文档.md`（项目根目录） | 环境要求、Docker / 本地部署步骤、配置变量、验证清单、故障排查 |
| **新闻爬取与加工** | `docs/新闻爬取与加工.md` | 爬虫与 AI 加工全链路原理、数据字典、运维实践 |
| 开发架构文档 | `docs/NewsCraft开发架构文档.md` | 系统架构、模块边界、数据设计、技术选型（v1.2） |
| API 接口规范 | `docs/API接口规范文档.md`、`docs/API接口规范文档-V2-RAG升级.md` | 各接口请求/响应字段契约 |
| Docker 原理讲解 | `docs/Docker部署指南.md` | Dockerfile / compose 逐段拆解（教学向） |
| AI 加工链路教程 | `docs/NewsCraft新闻AI加工链路搭建教程.md` | 模块一从零搭建教程 |
| 推荐链路教程 | `docs/NewsCraft个性化推荐链路搭建教程.md` | 模块二实现教程 |
| RAG 问答链路教程 | `docs/NewsCraftRAG问答链路搭建教程.md` | 模块三实现教程 |

## 十、常见问题

| 现象 | 解决 |
| --- | --- |
| 前端 8080 打不开 | `docker compose ps` 确认 5 个服务 running；前端镜像构建失败多为 npm 源问题，可换国内源后重试 |
| 接口报 502 | 后端容器未就绪：`docker compose logs backend-api` 排查；确认 MySQL/Redis 健康检查通过 |
| AI 接口 503 / 向量化失败 | 宿主机 Ollama 未启动或模型未拉取：`ollama pull bge-m3`、`ollama pull qwen2.5:7b` |
| 修改代码不生效 | Docker 部署需重新构建：`docker compose up -d --build backend-api` |
| 想切云端大模型 | 改 `后端代码/backend/config/config.yaml` 的 `llm.provider / api_key / base_url / chat_model`，代码零改动 |
| 数据库想重置 | `docker compose down -v`（会清空数据卷，慎用） |

---

> 详细部署与运维步骤见《部署文档.md》；爬虫与 AI 加工原理见《新闻爬取与加工》。
