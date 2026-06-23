# 统一上下文管理中心 — 产品初始化说明书 v1.0

> 版本：第一版 | 日期：2026-06-23

> 用途：指导运维人员完成本产品从零到可运行的完整初始化过程

---

## 1. 产品概述

统一上下文管理中心（Context Platform）是一个企业级上下文基础设施组件，提供上下文采集、存储、检索、可信度评估、生命周期管理和知识图谱功能。产品可作为独立应用运行，也可作为组件/插件嵌入到更大的本体产品中。

技术架构：Python 单体应用（Modular Monolith）+ React 前端 + PostgreSQL 主存储 + pgvector 向量检索 + LightRAG 知识图谱 + Mem0 记忆体系。

---

## 2. 运行环境要求

### 2.1 操作系统

| 环境 | 操作系统 | 说明 |
|------|---------|------|
| 开发环境 | macOS 13+ 或 Linux (Ubuntu 22.04+ / Debian 12+) | 需安装 Docker Desktop |
| 生产环境 | Linux (Ubuntu 22.04+ / Debian 12+ / CentOS 9+) | 国内云服务器或本地服务器，数据不出境 |
| Windows | 支持（通过 Docker Desktop + WSL2） | 非推荐，开发阶段可用 |

### 2.2 硬件最低配置

| 资源 | 开发环境 | 生产环境（小规模，<10人） | 生产环境（中规模，10-50人） |
|------|---------|--------------------------|---------------------------|
| CPU | 4 核 | 4 核 | 8 核 |
| 内存 | 8 GB | 8 GB | 16 GB |
| 存储 | 50 GB SSD | 100 GB SSD | 200 GB SSD |
| 网络 | 可访问外网（API调用） | 稳定内网 + 可选外网（DeepSeek API等） | 同左 |

**说明**：
- BGE-M3 嵌入模型本地部署需要约 2-4 GB 内存/显存用于模型加载
- PostgreSQL + pgvector 向量索引约占存储的 30%-50%
- 存储需求随上下文条目增长，初期每 10,000 条上下文约占用 2-5 GB（含向量）
- 生产环境推荐使用 SSD，向量索引和全文检索对 IO 要求较高

### 2.3 软件前置依赖

| 软件 | 最低版本 | 用途 | 安装方式 |
|------|---------|------|---------|
| Docker | 24.0+ | 容器化运行基础设施（PostgreSQL/Qdrant/Redis） | [Docker Desktop](https://www.docker.com/products/docker-desktop/) 或 Docker Engine |
| Docker Compose | 2.20+ | 编排多容器服务 | Docker Desktop 内置，或 `apt install docker-compose-plugin` |
| Python | 3.12+ | 后端运行环境 | `pyenv` 安装或系统包管理器，推荐使用 `venv` 虚拟环境 |
| Node.js | 20+ | 前端构建和运行 | `nvm` 安装或系统包管理器 |
| Git | 2.40+ | 版本管理（本地仓库） | 系统包管理器 |

**可选依赖**：

| 软件 | 版本 | 用途 | 备注 |
|------|------|------|------|
| Redis | 7.0+ | 权限缓存 + 配置缓存 | 不安装则自动降级为内存 LRU |
| Qdrant | 1.7+ | Mem0 记忆向量存储 | 仅启用 Mem0 集成时需要 |
| cURL | 8.0+ | 健康检查 | 通常系统自带 |

---

## 3. 工具链要求

### 3.1 后端工具链（Python）

| 工具/库 | 版本 | 用途 | 安装方式 |
|---------|------|------|---------|
| FastAPI | 0.115+ | Web 框架 | `pip install fastapi` |
| uvicorn | 0.30+ | ASGI 服务器 | `pip install uvicorn[standard]` |
| SQLAlchemy | 2.0+ | ORM | `pip install sqlalchemy[asyncio]` |
| Alembic | 1.14+ | 数据库迁移 | `pip install alembic` |
| asyncpg | 0.29+ | PostgreSQL 异步驱动 | `pip install asyncpg` |
| pgvector (python) | 0.3+ | pgvector Python 客户端 | `pip install pgvector` |
| LightRAG | 1.5+ | 知识图谱引擎 | `pip install lightrag-hku` |
| Mem0 | latest | Agent 记忆管理 | `pip install mem0ai` |
| mcp | 1.x | MCP 协议支持 | `pip install mcp` |
| dlt | 1.x | 数据采集管道 | `pip install dlt` |
| Prefect | 3.x | 任务编排与调度 | `pip install prefect` |
| python-jose | 3.3+ | JWT 认证 | `pip install python-jose[cryptography]` |
| bcrypt | 4.1+ | 密码/API Key 哈希 | `pip install bcrypt` |
| httpx | 0.28+ | 异步 HTTP 客户端 | `pip install httpx` |
| slowapi | 0.1+ | API 限流 | `pip install slowapi` |
| pydantic | 2.7+ | 数据验证 | FastAPI 内置 |
| BGE-M3 | - | 向量嵌入模型（本地） | 通过 `FlagEmbedding` 或 `sentence-transformers` 加载 |
| pytest | 8.x | 测试框架 | `pip install pytest pytest-asyncio pytest-cov` |
| Black | 24.x | 代码格式化 | `pip install black` |
| Ruff | 0.4+ | 代码检查 | `pip install ruff` |
| mypy | 1.9+ | 类型检查 | `pip install mypy` |

### 3.2 前端工具链（TypeScript/React）

| 工具/库 | 版本 | 用途 | 安装方式 |
|---------|------|------|---------|
| TypeScript | 5.x | 类型安全 | `npm install typescript` |
| React | 19+ | UI 框架 | `npm install react react-dom` |
| Vite | 6.x | 构建工具 | `npm install vite` |
| Tailwind CSS | 4.x | 原子化 CSS | `npm install tailwindcss` |
| shadcn/ui | latest | UI 组件库 | `npx shadcn-ui@latest init` |
| Lucide Icons | latest | SVG 图标 | `npm install lucide-react` |
| React Router | 6.x | 路由 | `npm install react-router-dom` |
| TanStack Query | 5.x | 服务端状态管理 | `npm install @tanstack/react-query` |
| Recharts | 2.12+ | 图表组件（管理端） | `npm install recharts` |
| Cytoscape.js | 3.30+ | 知识图谱可视化（用户端） | `npm install cytoscape` |
| react-hook-form | 7.x | 表单管理 | `npm install react-hook-form` |
| zod | 3.x | 表单校验 | `npm install zod` |
| sonner | latest | Toast 通知 | `npm install sonner` |
| Playwright | latest | E2E 测试 | `npm install -D @playwright/test` |
| Vitest | 1.x | 单元测试 | `npm install -D vitest` |
| ESLint | 9.x | 代码检查 | `npm install -D eslint` |
| Prettier | 3.x | 代码格式化 | `npm install -D prettier` |

**管理端额外依赖**：

| Refine | 5.x | 管理面板框架 | `npm install @refinedev/core @refinedev/react-router-v6` |

**完整依赖清单**：参见项目源码中的 `backend/requirements.txt`、`frontend/admin/package.json` 和 `frontend/user/package.json`。

---

## 4. 部署架构与 Docker 服务清单

### 4.1 Docker Compose 服务拓扑

```
┌──────────────────────────────────────────────────────────────────┐
│  Docker Network: context-platform-net                            │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ Backend  │  │ Admin UI │  │ User UI  │  │ Prefect      │   │
│  │ :8000    │  │ :3001    │  │ :3002    │  │ Server       │   │
│  └────┬─────┘  └──────────┘  └──────────┘  └──────────────┘   │
│       │                                                          │
│  ┌────┴─────┐  ┌──────────┐  ┌──────────┐                      │
│  │ PostgreSQL│  │  Qdrant  │  │  Redis   │                      │
│  │ :5432    │  │  :6333   │  │  :6379   │                      │
│  │ +pgvector │  │ (Mem0)   │  │ (缓存)   │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
└──────────────────────────────────────────────────────────────────┘
```

### 4.2 服务清单

| 服务名称 | 容器镜像 | 端口 | 用途 | 是否必须 |
|---------|---------|------|------|---------|
| db | `pgvector/pgvector:pg16` | 5432 | PostgreSQL 16 + pgvector 向量扩展 + pg_bestmatch BM25 全文检索 | 是 |
| backend | 自构建 `context-platform-backend` | 8000 | FastAPI 后端服务 | 是 |
| redis | `redis:7-alpine` | 6379 | 权限缓存 + 配置缓存 + 事件广播 | 否（不安装自动降级为内存 LRU） |
| qdrant | `qdrant/qdrant` | 6333 | Mem0 语义记忆向量存储 | 否（仅启用 Mem0 时需要） |
| frontend-admin | 自构建 `context-platform-admin` | 3001 | 管理端前端 (Refine + shadcn/ui) | 是 |
| frontend-user | 自构建 `context-platform-user` | 3002 | 用户端前端 (React + Cytoscape.js) | 是 |

### 4.3 Docker 数据卷

| 卷名 | 挂载路径 | 用途 | 备份策略 |
|------|---------|------|---------|
| pgdata | `/var/lib/postgresql/data` | PostgreSQL 数据文件 | 每日凌晨 2:00 pg_dump 全量备份 |
| qdrant_data | `/qdrant/storage` | Qdrant 向量数据 | 按需备份 |
| redis_data | `/data` | Redis 持久化数据 | 按需备份 |

### 4.4 部署模式

**模式 A：独立运行（standalone）**

产品使用内置 JWT 认证、独立前端 UI。适用场景：作为独立系统使用。

**模式 B：嵌入运行（embedded）**

产品作为组件嵌入父产品。通过环境变量 `RUNTIME_MODE=embedded` 和 `TENANT_MODE=multi` 启用。外部 API 通过 `/api/v1/external/` 访问，支持 API Key / JWT 委托 / 自定义 Token 三种认证方式。

**部署方案（按阶段）**：

| 阶段 | 部署方式 | 域名 | SSL |
|------|---------|------|-----|
| Phase 1-2 | Docker Compose 手动部署（本地开发机器） | IP + 端口 | 无 |
| Phase 3 | Dokploy/Coolify 一键部署 + Nginx 反向代理 | 独立域名 | Let's Encrypt 自动签发 |

---

## 5. 部署所需资源清单

### 5.1 外部 API 密钥与服务

| 资源 | 用途 | 获取方式 | 是否必须 | 预估成本 |
|------|------|---------|---------|---------|
| DeepSeek API Key | LLM 调用（分类/实体抽取/推理） | [platform.deepseek.com](https://platform.deepseek.com) 注册获取 | 是 | 按量付费，约 1元/百万 Token |
| 飞书应用凭证（App ID + App Secret） | 飞书文档/群消息采集 + 飞书 Bot 推送 | [飞书开放平台](https://open.feishu.cn) 创建应用 | 否（仅启用飞书采集时需要） | 飞书 API 免费额度内 |
| 邮件服务器凭证 | 邮件采集（IMAP） | 公司邮件系统管理员提供 | 否（仅启用邮件采集时需要） | 无额外成本 |

### 5.2 外部服务依赖

| 服务 | 用途 | 备注 |
|------|------|------|
| DeepSeek API (`api.deepseek.com`) | LLM 推理 | 需要稳定的外网访问 |
| 飞书开放平台 API | 采集和推送 | 可选，需内网可访问飞书 API |
| 项目知识库 API（IMA/飞书云盘/其他） | 文档同步采集 | 各平台 API 地址不同，需分别配置 |
| 财经数据 API（stock-data-pro） | 上市客户财报自动抓取 | 可选 |
| 客户项目系统 API | 项目里程碑/变更数据 | P2 阶段，可选 |

### 5.3 本地/内网资源

| 资源 | 说明 |
|------|------|
| BGE-M3 嵌入模型文件 | 首次运行时自动下载（约 2 GB），需可访问 Hugging Face 或镜像站 |
| NLTK / spaCy 模型数据 | 实体抽取所需 NLP 模型，首次运行时下载 |
| Memory.md 监听目录 | 文件监听/扫描的目标目录，如 `.codebuddy/memory/` |
| iCloud 同步目录（可选） | MEMORY.md 和附件多机同步 |
| SSL 证书（Phase 3） | Let's Encrypt 自动签发或自行准备 |

### 5.4 存储资源

| 资源 | 初始大小 | 增长预估 | 说明 |
|------|---------|---------|------|
| PostgreSQL 数据 | ~1 GB | 每万条上下文约 2-5 GB（含向量索引） | 主存储 |
| PostgreSQL WAL 归档 | ~5 GB | 持续增长，保留 7 天 | 增量备份 |
| 备份文件 | ~1 GB × 30天 = 30 GB | 按数据类型线性增长 | pg_dump 全量备份 |
| Qdrant 向量数据 | ~500 MB | 按 Agent 记忆量增长 | Mem0 存储 |

---

## 6. 配置清单

### 6.1 环境变量配置（`.env` 文件）

初始化时，复制 `.env.example` 为 `.env` 并填写以下变量：

| 序号 | 变量名 | 类型 | 必填 | 默认值 | 说明 | 填写样例 |
|------|--------|------|------|--------|------|---------|
| 1 | `DATABASE_URL` | str | 是 | - | PostgreSQL 连接字符串 | `postgresql+asyncpg://admin:password@db:5432/context_platform` |
| 2 | `DEEPSEEK_API_KEY` | str | 是 | - | DeepSeek API 密钥 | `sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| 3 | `DEEPSEEK_BASE_URL` | str | 否 | `https://api.deepseek.com` | DeepSeek API 基础 URL | `https://api.deepseek.com` |
| 4 | `SECRET_KEY` | str | 是 | - | JWT 签名密钥（至少 32 字符随机字符串） | 使用 `openssl rand -hex 32` 生成 |
| 5 | `ENVIRONMENT` | str | 是 | `development` | 运行环境 | `development` / `staging` / `production` |
| 6 | `RUNTIME_MODE` | str | 否 | `standalone` | 运行模式 | `standalone` / `embedded` |
| 7 | `TENANT_MODE` | str | 否 | `single` | 租户模式 | `single` / `multi` |
| 8 | `REDIS_URL` | str | 否 | - | Redis 连接字符串（不设置则使用内存降级） | `redis://redis:6379/0` |
| 9 | `QDRANT_URL` | str | 否 | `http://qdrant:6333` | Qdrant 连接字符串（Mem0 使用） | `http://qdrant:6333` |
| 10 | `LOG_LEVEL` | str | 否 | `INFO` | 日志级别 | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| 11 | `CORS_ORIGINS` | str | 否 | `http://localhost:3001,http://localhost:3002` | 允许跨域的前端域名（逗号分隔） | `http://localhost:3001,http://localhost:3002` |
| 12 | `BACKEND_PORT` | int | 否 | `8000` | 后端服务端口 | `8000` |
| 13 | `FEISHU_APP_ID` | str | 否 | - | 飞书应用 ID（启用飞书采集时必填） | `cli_xxxxxxxxxxxx` |
| 14 | `FEISHU_APP_SECRET` | str | 否 | - | 飞书应用密钥 | `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| 15 | `DOMAIN_NAME` | str | 否 | - | 域名（Phase 3 配置后自动启动 HTTPS） | `context-platform.example.com` |
| 16 | `SSL_ENABLED` | bool | 否 | `false` | 是否启用 SSL | `true` / `false` |
| 17 | `SSL_CERT_PATH` | str | 否 | - | SSL 证书路径 | `/etc/letsencrypt/live/example.com/fullchain.pem` |
| 18 | `SSL_KEY_PATH` | str | 否 | - | SSL 私钥路径 | `/etc/letsencrypt/live/example.com/privkey.pem` |

**关键提醒**：
- `SECRET_KEY` 生产环境必须更换为随机字符串，不得使用开发环境默认值
- `DEEPSEEK_API_KEY` 需要在 DeepSeek 平台注册并充值后才能使用
- 变量 6-9（运行模式相关）仅在嵌入部署时需要设置
- 变量 13-14（飞书相关）仅在启用飞书采集时需要设置
- 变量 15-18（域名和 SSL）仅在 Phase 3 需要对外提供服务时设置

### 6.2 系统配置初始化（数据库种子数据）

系统首次启动时，自动执行种子脚本，向 `system_configs` 表写入以下 8 个分组的默认配置。管理员后续可在 Web 管理端 `/admin/config` 页面修改。

#### 分组 1：可信度引擎（`confidence_engine`，10 项）

| 参数键 | 默认值 | 说明 |
|--------|--------|------|
| `decay_start_months` | 6 | 时效衰减起始月数。6 个月后开始衰减 |
| `decay_rate_per_month` | 0.03 | 每月衰减量（0.03 分/月） |
| `min_score_after_decay` | 0.20 | 衰减后最低分数 |
| `corroboration_weight_cap` | 0.15 | 单次多源印证最大提权权重 |
| `max_corroboration_boost` | 0.45 | 多源印证总提权上限 |
| `conflict_penalty` | 0.10 | 矛盾标记惩罚值 |
| `semantic_similarity_threshold` | 0.85 | 语义去重相似度阈值 |
| `corroboration_similarity_threshold` | 0.70 | 多源印证相似度判定阈值 |
| `manual_override_immunity_days` | 30 | 手动调级后免疫自动衰减天数 |
| `confidence_corroboration_decay_type_count` | 2 | 同类型来源重复印证递减阈值 |

#### 分组 2：初始可信度映射（`confidence_mapping`，16 组 × 2 项 = 32 项）

16 种来源类型到初始可信度 (level, score) 的映射。主要默认值：

| 来源类型 | 等级 | 分数 |
|---------|------|------|
| contract | L5 | 0.98 |
| official_doc | L5 | 0.97 |
| expert_verified | L4 | 0.93 |
| financial_report | L4 | 0.92 |
| meeting_minutes | L4 | 0.90 |
| email | L4 | 0.88 |
| project_kb | L3 | 0.78 |
| ai_extract_verified | L3 | 0.78 |
| manual_entry | L3 | 0.75 |
| memory_md | L2 | 0.65 |
| ai_extract | L2 | 0.60 |
| web_scrape | L2 | 0.55 |
| verbal | L1 | 0.40 |
| unknown | L1 | 0.40 |
| competitor_rumor | L1 | 0.35 |

#### 分组 3：采集管道（`ingestion`，17 项）

| 参数键 | 默认值 | 说明 |
|--------|--------|------|
| `source.project_kb.enabled` | true | 启用项目知识库采集 |
| `source.project_kb.interval_hours` | 24 | 采集间隔（24 小时） |
| `source.project_kb.platforms` | ["ima","feishu_drive"] | 支持平台 |
| `source.memory_md.enabled` | true | 启用 Memory.md 导入 |
| `source.memory_md.scan_interval_hours` | 1 | 定时扫描间隔（1 小时） |
| `source.memory_md.watch_paths` | [".codebuddy/memory/"] | 监听目录 |
| `source.feishu_doc.enabled` | false | 飞书文档采集（默认关闭） |
| `source.feishu_group.enabled` | false | 飞书群消息采集（默认关闭） |
| `source.email.enabled` | false | 邮件采集（默认关闭） |
| `source.finance_api.enabled` | true | 财报自动抓取 |
| `ingestion.dedup.similarity_threshold` | 0.85 | 去重相似度阈值 |
| `ingestion.max_chunk_size` | 8000 | 大文本分块最大字符数 |
| `ingestion.max_items_per_batch` | 500 | 单次批量入库上限 |
| `ingestion.entity_match_threshold` | 0.75 | 实体模糊匹配阈值 |

#### 分组 4：搜索检索（`search`，10 项）

| 参数键 | 默认值 | 说明 |
|--------|--------|------|
| `hybrid.bm25_weight` | 0.3 | BM25 关键词权重 |
| `hybrid.vector_weight` | 0.4 | 向量语义权重 |
| `hybrid.graph_weight` | 0.3 | 图谱关系权重 |
| `graph.max_depth` | 2 | 图谱遍历最大跳数 |
| `search.default_page_size` | 20 | 默认每页条数 |
| `search.max_page_size` | 100 | 最大每页条数 |
| `search.timeout_seconds` | 10 | 搜索超时时间 |

#### 分组 5：LLM 调用（`llm`，11 项）

| 参数键 | 默认值 | 说明 |
|--------|--------|------|
| `llm.model` | deepseek-chat | 模型名称 |
| `llm.temperature` | 0.3 | 温度参数 |
| `llm.max_tokens` | 4096 | 最大输出 Token |
| `llm.max_retries` | 3 | 最大重试次数 |
| `llm.daily_token_budget` | 1000000 | 每日 Token 预算（100 万） |
| `embedding.model` | BGE-M3 | 本地嵌入模型 |
| `embedding.dimension` | 1024 | 向量维度 |
| `embedding.batch_size` | 32 | 嵌入批处理大小 |

#### 分组 6：权限安全（`security`，12 项）

| 参数键 | 默认值 | 说明 |
|--------|--------|------|
| `auth.access_token_ttl_minutes` | 30 | JWT Access Token 有效期（分钟） |
| `auth.refresh_token_ttl_days` | 7 | JWT Refresh Token 有效期（天） |
| `auth.password_min_length` | 8 | 密码最小长度 |
| `auth.max_login_attempts` | 5 | 最大登录失败次数 |
| `rate_limit.user_per_minute` | 100 | 普通用户 API 限流 |
| `rate_limit.agent_per_minute` | 300 | Agent API 限流 |
| `permission.cache_ttl_seconds` | 300 | 权限缓存 TTL（5 分钟） |
| `audit.retention_days` | 365 | 审计日志保留 1 年 |
| `audit.archive_retention_days` | 1825 | 归档上下文保留 5 年 |

#### 分组 7：生命周期（`lifecycle`，5 项）

| 参数键 | 默认值 | 说明 |
|--------|--------|------|
| `lifecycle.archive_after_project_end_days` | 730 | 项目结束 2 年后归档 |
| `lifecycle.decay_warning_days` | 30 | 衰减前 30 天预警 |
| `lifecycle.auto_archive_enabled` | true | 启用自动归档 |

#### 分组 8：组件集成（`integration`，10 项）

| 参数键 | 默认值 | 说明 |
|--------|--------|------|
| `integration.runtime_mode` | standalone | 运行模式 |
| `integration.tenant_mode` | single | 租户模式 |
| `integration.max_workspaces` | 50 | 最大工作区数 |
| `integration.default_workspace_quota.max_contexts` | 100000 | 默认上下文上限 |
| `integration.default_workspace_quota.max_api_calls_per_minute` | 500 | 默认 API 限流 |
| `integration.webhook.max_retries` | 5 | Webhook 最大重试次数 |
| `integration.webhook.timeout_seconds` | 10 | Webhook 请求超时 |
| `integration.external_api.rate_limit_per_minute` | 300 | 外部 API 总限流 |

默认配置完整清单见 `backend/config/defaults.yaml` 和数据库种子脚本 `backend/alembic/seeds/seed_system_configs.py`。

### 6.3 用户设置默认值

新用户注册时自动创建的默认设置：

| 设置项 | 默认值 | 说明 |
|--------|--------|------|
| 通知渠道 | 仅站内通知 `in_app` | 飞书Bot 和邮件默认关闭 |
| 接收的通知类型 | `["alert","review","update"]` | 告警、审核任务、上下文更新 |
| 免打扰 | 22:00 - 08:00 | 默认关闭，需手动启用 |
| 搜索默认视图 | 卡片视图 `card` |  |
| 搜索默认查询模式 | 精确查询 `exact` |  |
| 默认最低可信度 | 不限 `L0` |  |
| 界面语言 | 简体中文 `zh-CN` |  |
| 时区 | `Asia/Shanghai` |  |
| 日期格式 | `YYYY-MM-DD` |  |
| 图谱自动展开 | 启用 |  |
| 图谱动画 | 启用 |  |

---

## 7. 初始化步骤（快速启动指南）

### 7.1 前置检查

```bash
# 检查 Docker 是否可用
docker --version          # 应 >= 24.0
docker compose version    # 应 >= 2.20

# 检查 Python 版本
python3 --version         # 应 >= 3.12

# 检查 Node.js 版本
node --version            # 应 >= 20
npm --version             # 应 >= 10

# 检查 Git
git --version             # 应 >= 2.40
```

### 7.2 克隆项目（本地 Git 仓库）

```bash
# 从本地 Git 仓库克隆
git clone <local_repo_path> context-platform
cd context-platform
```

### 7.3 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件，至少填写以下必填项：
# - SECRET_KEY          （使用 openssl rand -hex 32 生成）
# - DEEPSEEK_API_KEY    （从 platform.deepseek.com 获取）
# - DATABASE_URL        （使用默认值即可，Docker Compose 内网通信）
# - ENVIRONMENT         （development / production）
```

### 7.4 启动基础设施（PostgreSQL + Qdrant + Redis）

```bash
# 启动数据库和中间件
docker compose up -d db qdrant redis

# 等待 PostgreSQL 就绪（约 10-15 秒）
docker compose exec db pg_isready -U admin
```

### 7.5 初始化后端

```bash
cd backend

# 创建 Python 虚拟环境
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt

# 运行数据库迁移（创建所有表 + 索引）
alembic upgrade head

# 执行种子数据（写入 8 组默认系统配置）
python -m alembic.seeds.seed_system_configs

# 启动后端服务
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

验证后端启动成功：
```bash
# 检查 API 文档
curl http://localhost:8000/docs

# 检查健康检查
curl http://localhost:8000/api/v1/external/health
```

### 7.6 初始化前端

```bash
# 管理端（Refine + shadcn/ui）
cd frontend/admin
npm install
npm run dev          # 启动在 http://localhost:3001

# 用户端（React + Cytoscape.js）
cd frontend/user
npm install
npm run dev          # 启动在 http://localhost:3002
```

### 7.7 首次访问

1. 管理端：浏览器打开 `http://localhost:3001`
2. 用户端：浏览器打开 `http://localhost:3002`
3. API 文档：浏览器打开 `http://localhost:8000/docs`

**首次登录**：使用数据库种子脚本创建的默认管理员账户登录（用户名和密码见种子脚本 `seed_users.py`），登录后立即修改密码。

### 7.8 验证安装

```bash
# 验证 API 正常响应
curl http://localhost:8000/api/v1/health

# 验证数据库连接
docker compose exec db psql -U admin -d context_platform -c "SELECT count(*) FROM system_configs;"
# 应返回 100+ 条配置项

# 验证 pgvector 扩展
docker compose exec db psql -U admin -d context_platform -c "SELECT * FROM pg_extension WHERE extname='vector';"
# 应返回 vector 扩展记录

# 验证搜索引擎
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your_jwt_token>" \
  -d '{"query": "测试", "mode": "hybrid"}'
```

---

## 8. 初始化后检查清单

完成上述步骤后，按此清单逐项验证系统就绪：

### 8.1 基础设施

- [ ] PostgreSQL 数据库可连接，所有表（23 张）已创建
- [ ] pgvector 扩展已启用，`content_vector` 列的 IVFFlat 索引已建立
- [ ] pg_bestmatch 扩展已启用，全文搜索 GIN 索引已建立
- [ ] Redis 可连接（如已安装），或确认已降级为内存缓存
- [ ] Qdrant 可连接（如已安装），Mem0 集成可用
- [ ] Docker 数据卷 `pgdata` 正确挂载

### 8.2 种子数据

- [ ] `system_configs` 表已写入 8 个分组共 100+ 条默认配置
- [ ] 默认管理员账户已创建
- [ ] 默认 workspace 已创建（如多租户模式）
- [ ] 默认 API Key 已生成（如嵌入模式）

### 8.3 服务端点

- [ ] FastAPI 后端 `/api/v1/contexts` CRUD 端点可访问
- [ ] 混合搜索 `/api/v1/search` 端点可访问
- [ ] 实体管理 `/api/v1/entities` 端点可访问
- [ ] 审核队列 `/api/v1/review/queue` 端点可访问
- [ ] 系统配置 `/api/v1/admin/config` 端点可访问
- [ ] 用户设置 `/api/v1/settings` 端点可访问
- [ ] 健康检查 `/api/v1/external/health` 返回 healthy
- [ ] Prometheus 指标 `/api/v1/external/health/metrics` 可访问
- [ ] WebSocket `/ws` 端点可连接（如需要实时推送）
- [ ] OpenAPI 文档 `/docs` 可访问

### 8.4 前端应用

- [ ] 管理端 `http://localhost:3001` 可正常加载和登录
- [ ] 用户端 `http://localhost:3002` 可正常加载和登录
- [ ] 管理端系统配置页面 `/admin/config` 显示正确的 8 个配置分组
- [ ] 管理端用户管理页面可创建/编辑用户
- [ ] 用户端搜索页面可执行搜索
- [ ] 用户端图谱页面可正常渲染
- [ ] JWT Token 登录流程正常（access_token 过期后可刷新）

### 8.5 外部依赖

- [ ] DeepSeek API 密钥有效（可通过 LLM 调用配置 Tab 测试连通性）
- [ ] BGE-M3 模型已下载并加载成功（检查首次嵌入调用是否正常）
- [ ] 飞书应用凭证已配置（如启用飞书采集）
- [ ] 项目知识库 API 可连接（如启用项目知识库采集）
- [ ] Memory.md 监听目录存在且可读（如启用 Memory.md 导入）

### 8.6 安全配置

- [ ] SECRET_KEY 已更换为非默认值
- [ ] 默认管理员密码已修改
- [ ] CORS 白名单已配置（仅允许前端域名）
- [ ] 生产环境 `ENVIRONMENT=production`，`LOG_LEVEL=WARNING`
- [ ] API 限流参数已按需调整

---

## 9. 关键注意事项

### 9.1 BGE-M3 嵌入模型首次加载

BGE-M3 模型首次运行时需要从 Hugging Face 下载约 2 GB 模型文件。如网络受限，可提前下载模型文件放置于本地目录，并通过环境变量指定模型路径。加载需要 2-4 GB 内存。首次启动后端时可能因模型下载而延迟 2-5 分钟。

### 9.2 pg_bestmatch BM25 扩展

pg_bestmatch 是 PostgreSQL 中文全文检索扩展，需在 PostgreSQL 16 镜像中额外编译安装。如安装遇困难，Phase 1 可暂时使用 PostgreSQL 内置 `pg_trgm` + `tsvector` 替代，检索质量略降但功能可用。

### 9.3 内存降级机制

Redis 为可选依赖。如未安装 Redis，系统自动降级为内存 LRU 缓存（最大 10,000 条目），适用于开发和小规模部署。生产环境推荐安装 Redis 以获得更好的缓存一致性和多进程共享能力。

### 9.4 租户模式切换

单租户模式（`TENANT_MODE=single`）与多租户模式（`TENANT_MODE=multi`）在初始化后**不可动态切换**。`workspace_id` 列的 NOT NULL 约束和数据填充策略不同。请在首次部署时确定模式。

### 9.5 飞书采集的额外配置

如启用飞书文档/群消息采集，除了环境变量中的 `FEISHU_APP_ID` 和 `FEISHU_APP_SECRET`，还需在飞书开放平台完成以下配置：
- 应用权限：获取「文档读写」「消息读取」权限
- 事件订阅：配置 Webhook 回调 URL `https://<domain>/api/v1/webhooks/feishu`
- Bot 消息：配置飞书 Bot 消息卡片模板

### 9.6 配置热生效

大部分系统配置修改后在 **1 秒内** 生效（通过 ConfigService 内存缓存刷新）。以下配置有生效延迟：
- 采集管道参数：下一个采集周期生效（最长 24 小时）
- JWT Token TTL 变更：新签发的 Token 使用新 TTL，已有 Token 不受影响
- 生命周期参数：下一个 Prefect 定时任务周期生效
- 权限缓存 TTL：下一个缓存过期周期生效（最长 5 分钟）

### 9.7 备份验证

请在初始化完成后立即执行一次全量备份并验证恢复流程：
```bash
# 全量备份
docker compose exec db pg_dump -U admin context_platform > backup_$(date +%Y%m%d).sql

# WAL 归档确认
docker compose exec db psql -U admin -c "SELECT * FROM pg_stat_archiver;"
```

---

## 10. 故障排查

| 问题 | 可能原因 | 检查步骤 |
|------|---------|---------|
| `connection refused` 连接 PostgreSQL | PostgreSQL 容器未启动或端口冲突 | `docker compose ps db`，`lsof -i :5432` |
| Alembic 迁移失败 | 数据库未就绪或已有旧数据 | `docker compose exec db pg_isready`，检查 `alembic history` |
| BGE-M3 嵌入失败 | 模型未下载或内存不足 | 检查日志中 Hugging Face 下载进度，确认内存 > 4 GB |
| DeepSeek API 超时 | API Key 无效或网络不通 | `curl -H "Authorization: Bearer $DEEPSEEK_API_KEY" https://api.deepseek.com/v1/models` |
| 前端 `npm install` 失败 | Node.js 版本不兼容或网络问题 | 确认 `node --version` >= 20，尝试 `npm install --legacy-peer-deps` |
| 端口冲突 | 8000/3001/3002/5432 被占用 | `lsof -i :<port>` 查看占用进程，修改 `.env` 中对应端口 |
| pgvector 扩展未找到 | pgvector 未安装在 PostgreSQL 中 | `docker compose exec db psql -U admin -c "CREATE EXTENSION IF NOT EXISTS vector;"` |

如基础检查无法解决问题，查看详细日志：
```bash
# 后端日志
docker compose logs backend --tail 100 -f

# 数据库日志
docker compose logs db --tail 50

# 前端构建日志
cd frontend/admin && npm run build
```

---

## 11. 版本记录

| 版本 | 日期 | 变更说明 |
|------|------|---------|
| v1.0 | 2026-06-23 | 第一版，基于 01_product_design 至 09_interface_design 全部 9 份设计文档汇总而成；涵盖环境要求、工具链、部署、资源、配置、初始化步骤和验证清单 |

---

## 参考设计文档

1. [产品设计方案](01_product_design.md) — 功能模块、业务规则、优先级矩阵
2. [UI/UX 详细设计](02_ui_ux_design.md) — 前端设计系统、色彩、字体、组件库
3. [数据架构与数据库设计](03_database_design.md) — 23 张表结构、索引、备份策略
4. [应用架构设计](04_app_architecture.md) — 五层架构、API 端点、安全设计
5. [技术实施方案](05_tech_implementation.md) — 技术栈选型、实施路线图、工时估算
6. [配置管理详细设计](08_configuration_management.md) — 三层配置体系、全部参数清单
7. [组件化接口设计](09_interface_design.md) — 外部 API、事件系统、UI 嵌入、多租户
