[README.md](https://github.com/user-attachments/files/29241627/README.md)
# Context Platform — 统一上下文管理中心

> **Context-as-a-Service** — 让公司积累的每一条上下文都能被 AI Agent 和团队成员在需要时精准获取、可信消费、持续保鲜。

---

## 为什么需要 Context Platform？

企业信息碎片化是 AI 落地的头号障碍：

- 客户关键信息散落在飞书群消息中无法检索
- 项目决策记录在个人笔记里随人员流动丢失
- AI Agent 执行诊断时缺乏结构化的上下文支撑
- 管理者无法快速了解所有客户/项目的最新状态

Context Platform 将这些信息 **统一采集 → 结构化存储 → 可信度评估 → 生命周期管理**，成为公司级的上下文基础设施。

---

## 核心特性

### 🔍 混合检索引擎

三种检索模式融合排序，覆盖从精确匹配到跨实体联想的全部场景：

| 模式 | 机制 | 权重 |
|------|------|------|
| 关键词 | BM25 精确匹配（客户名/项目名/日期） | 0.3 |
| 向量语义 | pgvector 近似匹配 + 跨实体联想 | 0.4 |
| 图谱遍历 | LightRAG 2 跳关系 | 0.3 |

支持五种查询模式：精确查询、语义查询、关联查询、时间线查询、矛盾查询。

### 🏷️ 六级可信度引擎

自研核心组件，每条上下文都有可追溯的可信度评级：

| 层级 | 名称 | 分数区间 | Agent 引用规则 |
|------|------|---------|---------------|
| L5 | 权威验证 | [0.95, 1.00] | 自由引用 |
| L4 | 高可信 | [0.85, 0.95) | 标注来源后引用 |
| L3 | 中等可信 | [0.70, 0.85) | 需交叉验证 |
| L2 | 待验证 | [0.50, 0.70) | 不可引用，仅辅助参考 |
| L1 | 低可信 | [0.30, 0.50) | 不可引用 |
| L0 | 不可用 | [0.00, 0.30) | 已过期/矛盾 |

可信度由四个子算法驱动：
- **初始置信度映射** — 15 种来源类型对应不同初始等级（合同 L5 → 口述 L1）
- **多源印证提权** — 多源不矛盾时逐步提升置信度（上限 +0.45）
- **时效衰减** — 6 个月后线性衰减（每月 -0.03）
- **矛盾惩罚** — 冲突标记时双方降分（-0.10）

### 🛡️ 三层权限模型

自研权限引擎，逐层收紧，最严格规则胜出：

```
Layer 1: RBAC（角色权限矩阵） → Layer 2: 实体边界（数据隔离） → Layer 3: 敏感度（四级分类）
```

- **RBAC**：5 种角色（admin / partner / senior_consultant / consultant / agent）× 12 种操作
- **实体边界**：用户仅可访问被分配的客户/项目上下文
- **敏感度**：public / internal / confidential / top_secret 四级，Agent 不可读 top_secret

### 🕸️ 知识关系图谱

7 种关系类型建模跨实体语义关联：`drives` / `threatens` / `depends_on` / `contradicts` / `supersedes` / `informs` / `part_of`

支持 1-2 跳关系遍历、路径分析、子图导出，图谱可视化按域/可信度着色。

### 🔄 全生命周期管理

状态机覆盖从创建到归档的完整链路：

```
创建 → 待验证 → 活跃 → 衰减 / 被替代 / 矛盾 / 归档
```

- 已确认上下文 **不可变**（仅追加新版本，不修改历史）—— 借鉴 Manus 上下文工程"Read-Before-Decide"原则
- 衰减自动触发（6 月未更新 → 衰减标记，置信度降级）
- 矛盾自动检测 + 人工裁决流程

### 📡 多源采集管道

自动 + 人工双通道采集，覆盖企业全数据源：

| 来源 | 优先级 | 机制 |
|------|--------|------|
| 项目知识库（IMA/飞书云盘） | P0 | API 全量/增量同步 |
| Memory.md 文件 | P1 | 文件监听 + LLM 解析导入 |
| 飞书文档 | P1 | 飞书开放平台 API |
| 飞书群消息 | P1 | Bot Webhook + 关词触发 |
| 邮件 | P2 | IMAP + 规则引擎 |
| 上市公司财报 | P2 | 公开 API 自动抓取 |
| 人工洞察录入 | P0 | Web 审核队列 |

采集管道七步处理：去重 → 自动分类 → 实体抽取 → 关系识别 → 可信度初评 → 冲突检测 → 入库待验证。

### 🤖 MCP Server（Agent 接口）

8 个 MCP Tools 对外暴露，Agent 查询结果自动附带 **消费指引（consumption_guidance）**：

```json
{
  "usage_advice": "标注来源后引用",
  "advice_reason": "该上下文来自官方财报，可信度L4",
  "related_higher_confidence_hint": "同实体下存在2条L4+关联上下文，建议一并检索",
  "is_lesson_learned": false,
  "cross_validation_suggestion": "关联条目'XX审计报告'(L5)可能包含更可靠信息"
}
```

| Tool | 用途 |
|------|------|
| `search_context` | Agent 诊断检索 |
| `get_context_detail` | 获取单条上下文详情 |
| `get_entity_graph` | 实体关系图谱 |
| `get_context_timeline` | 时间线分析 |
| `get_contradictions` | 矛盾查询 |
| `submit_context` | Agent 提交上下文（标记 L2） |
| `check_confidence` | 可信度验证 |
| `submit_correction` | Agent 纠错建议 |

---

## 架构概览

五层架构 + 集成适配层，Phase 1-3 采用 Modular Monolith：

```
┌─ 消费层 ─────────────────────────────────────┐
│  MCP Tool (Agent) | SDK调用 | Web前端        │
├─ 集成适配层 ─────────────────────────────────┤
│  Auth Adapter | Workspace Middleware | Webhook│
│  Quota Service | UI Adapter                  │
├─ API 网关层 ─────────────────────────────────┤
│  FastAPI + JWT/API Key + RBAC + 限流 + 审计  │
├─ 业务服务层 ─────────────────────────────────┤
│  Context | Ingestion | Search | Distribution │
│  Conflict | Permission | Report | Config     │
│  Guidance | Sync                              │
├─ 数据访问层 ─────────────────────────────────┤
│  SQLAlchemy ORM | pgvector | LightRAG | Mem0 │
├─ 存储层 ─────────────────────────────────────┤
│  PostgreSQL 16 + pgvector | Qdrant (Mem0)    │
│  文件系统 (iCloud)                           │
└───────────────────────────────────────────────┘
```

**架构决策**：小团队（<10 人）+ 强数据耦合 + 图谱查询需跨表 JOIN → 单体应用优先，模块间 Python 接口通信而非 HTTP。瓶颈时将 Ingestion/Search 独立为微服务。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端框架 | **FastAPI** (Python) |
| 数据库 | **PostgreSQL 16** + pgvector + pg_bestmatch |
| 向量数据库 | **Qdrant** (Mem0) |
| 知识图谱 | **LightRAG** |
| ORM | **SQLAlchemy** + Alembic 迁移 |
| 认证 | JWT (access 30min / refresh 7d) + API Key |
| 限流 | SlowAPI |
| 任务调度 | **Prefect** |
| LLM | DeepSeek (分类/实体抽取/上下文提取) |
| 嵌入模型 | BGE-M3 |
| 前端-管理端 | **Refine** + shadcn/ui |
| 前端-用户端 | React + shadcn/ui + Cytoscape.js |
| Agent 接口 | **MCP Server** (FastMCP) |
| 客户端 SDK | Python + TypeScript |
| 缓存 | Redis (权限缓存, 5min TTL) |
| 容器化 | Docker Compose |

---

## 项目结构

```
context-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI 入口
│   │   ├── config.py               # 配置管理
│   │   ├── api/v1/                 # 内部 API 路由
│   │   │   ├── context.py          # /api/v1/contexts
│   │   │   ├── search.py           # /api/v1/search
│   │   │   ├── entities.py         # /api/v1/entities
│   │   │   ├── relations.py        # /api/v1/relations
│   │   │   ├── review.py           # /api/v1/review
│   │   │   ├── permissions.py      # /api/v1/permissions
│   │   │   └── ...
│   │   ├── api/external/           # 外部 API（组件化接口）
│   │   ├── api/mcp/                # MCP Server 端点
│   │   ├── core/                   # 安全 + RBAC + 审计 + 限流
│   │   ├── services/               # 业务服务层（10+ Service）
│   │   │   ├── confidence_service.py   # ⭐ 可信度引擎
│   │   │   ├── permission_service.py   # ⭐ 三层权限模型
│   │   │   ├── search_service.py       # 混合检索
│   │   │   ├── ingestion_service.py    # 采集管道
│   │   │   ├── guidance_service.py     # Agent 消费指引
│   │   │   └── ...
│   │   ├── integrations/           # 外部系统集成
│   │   │   ├── adapter.py          # 集成适配层入口
│   │   │   ├── auth/               # 认证适配器
│   │   │   ├── workspace/          # 多租户管理
│   │   │   ├── feishu_client.py    # 飞书
│   │   │   ├── mem0_client.py      # Mem0
│   │   │   └── ...
│   │   ├── models/                 # SQLAlchemy ORM
│   │   ├── schemas/                # Pydantic 模型
│   │   └── pipelines/              # Prefect 采集管道
│   ├── alembic/                    # 数据库迁移
│   ├── tests/                      # 单元 + 集成测试
│   └── requirements.txt
│
├── frontend/
│   ├── admin/                      # 管理端 (Refine + shadcn/ui)
│   └── user/                       # 用户端 (React + Cytoscape.js)
│
├── sdk/
│   ├── python/                     # Python 客户端 SDK
│   └── typescript/                 # TypeScript 客户端 SDK
│
├── plugin-manifest.json            # 组件清单
├── docker-compose.yml
└── Makefile
```

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16 (with pgvector extension)

### 本地开发

```bash
# 1. 克隆仓库
git clone https://github.com/your-org/context-platform.git
cd context-platform

# 2. 启动基础设施（PostgreSQL + Qdrant）
docker compose up db qdrant -d

# 3. 配置环境变量
cp backend/.env.example backend/.env
# 编辑 .env 填入 DATABASE_URL, DEEPSEEK_API_KEY 等

# 4. 安装后端依赖
cd backend
pip install -r requirements.txt

# 5. 数据库迁移
alembic upgrade head

# 6. 启动后端服务
uvicorn app.main:app --reload --port 8000

# 7. 安装前端依赖并启动
cd ../frontend/admin
npm install && npm run dev    # 管理端 :3001

cd ../frontend/user
npm install && npm run dev    # 用户端 :3002
```

### Docker Compose 一键启动

```bash
docker compose up -d
# 后端 :8000 | 管理端 :3001 | 用户端 :3002 | Qdrant :6333
```

---

## API 概览

### 内部 API (`/api/v1/`)

| 端点 | 说明 |
|------|------|
| `GET/POST /contexts` | 上下文列表/创建 |
| `POST /search` | 统一混合搜索入口 |
| `GET/POST /entities` | 实体管理 |
| `GET /entities/{id}/graph` | 实体关系图谱 |
| `GET/POST /relations` | 关系管理 |
| `GET/POST /review/queue` | 审核队列 |
| `GET /metrics/overview` | 全局指标概览 |

### 外部 API (`/api/v1/external/`)

组件化接口，供父产品通过 SDK 集成调用，支持 API Key / JWT 委托 / 自定义 Token 三种认证方式。

### MCP Tools

Agent 通过 MCP 协议调用 `search_context` / `get_entity_graph` / `submit_context` 等 8 个工具。

---

## 核心算法速览

### 可信度计算示例

```
# L2(0.60) 被 L4(0.90) 印证
corroboration_weight = min(0.15, (0.90-0.5)*0.3) = 0.12
new_score = 0.60 + (1.0-0.60) * 0.12 = 0.648 → 仍为 L2

# L4(0.90) 12 个月未更新
effective = 0.90 - 0.03*6 = 0.72 → 降为 L3

# 矛盾惩罚
penalized = max(current_score - 0.10, 0.10)
```

### 权限检查流程

```
用户请求 → Layer1 RBAC(拒绝则403) → Layer2 实体边界(拒绝则403) → Layer3 敏感度(拒绝则403) → 200
```

---

## 上下文分类体系

四大域覆盖企业全景上下文：

| 域 | 覆盖范围 |
|----|---------|
| **客户域** | 基本概况 / 组织架构 / 业务模式 / 财务指标 |
| **项目域** | 售前 / 合同范围 / 交付 / 财经 |
| **运营域** | 产品创新 / 能力建设 / 业务管理 / 知识资产 |
| **外部环境域** | 行业政策 / 竞品动态 / 技术趋势 / 生态伙伴 |

---

## Memory.md 推荐模板

为最大程度利用采集管道的智能提取能力，推荐团队按以下结构维护 Memory.md：

```markdown
# Memory.md

## 1. 目标 (Goal)        → context_role="goal", 不可变
## 2. 进度与阶段 (Phases) → context_role="progress", Checkbox 自动解析
## 3. 关键发现 (Findings) → context_role="finding", 自动关联实体
## 4. 经验教训 (Lessons)  → context_role="lesson_learned", 可信度自动升为 L3
```

经验教训章节价值极高——将团队试错经验转化为可检索、可引用的知识资产，Agent 检索时自动高亮标记"经验库"。

---

## 贡献指南

欢迎贡献！请遵循以下流程：

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/your-feature`)
3. 提交变更 (`git commit -m 'Add your feature'`)
4. 推送分支 (`git push origin feature/your-feature`)
5. 创建 Pull Request

### 开发规范

- 后端：遵循 FastAPI 项目结构，Service 层纯业务逻辑，IO 操作由调用方负责
- 前端：shadcn/ui 组件库 + React hooks 模式
- 测试：每个 Service 必须有单元测试，API 端点必须有集成测试
- 数据库变更：通过 Alembic 迁移，禁止手动改表

---

## License

Apache License 2.0 — 详见 [LICENSE](LICENSE) 文件。

---

> *"RAG 的尽头是知识图谱"* — Context Platform 不只是检索增强，更是企业上下文的结构化基础设施。
