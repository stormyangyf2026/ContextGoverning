# 统一上下文管理中心 (Context Platform)

> 企业级统一上下文生命周期管理平台 — 多源采集、六级可信度评估、知识图谱、混合检索、三层权限、人工审核、Agent消费指引

## 项目概述

Context Platform 是一个公司级统一上下文管理与消费平台，核心功能包括：

- **多源上下文自动采集**：Memory.md 文件解析、飞书文档/消息、知识库同步、邮件、财报
- **六级可信度评估引擎**：多源印证算法 + 时效衰减算法 + 矛盾惩罚 + 人工审核干预
- **知识图谱构建与可视化**：实体关系建模、2跳遍历、LightRAG 集成
- **混合检索**：BM25 全文 + 向量语义 + 图谱遍历 + 融合排序
- **三层权限模型**：RBAC + 实体边界 + 敏感度
- **人工审核工作流**：审核队列、驳回、裁决、批量操作
- **Agent 消费指引**：L0-L5 逐级引用建议 + 交叉验证提示 + 经验库标记
- **组件化集成**：API Key / JWT / Custom Token 三种认证、Webhook 事件系统、Python/TypeScript SDK

## 技术栈

| 层次 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI (Python) | 0.115+ |
| 数据库 | PostgreSQL + pgvector | 18 |
| ORM | SQLAlchemy | 2.0+ |
| 向量嵌入 | BGE-M3 | 1024维 |
| LLM | DeepSeek | deepseek-chat |
| 知识图谱 | LightRAG | - |
| Agent记忆 | Mem0 | - |
| 限流 | slowapi | - |
| 前端 | React + TypeScript + Vite | 18 |
| UI框架 | shadcn/ui + Tailwind CSS | - |
| 图可视化 | Cytoscape.js | - |

## 项目结构

```
context-platform/
├── backend/
│   ├── app/
│   │   ├── api/          # API路由（v1 42端点 + external 27端点 + MCP 8 Tools）
│   │   ├── core/         # 核心基础设施（JWT认证、RBAC、审计、限流）
│   │   ├── models/       # 数据模型（17张表）
│   │   ├── services/     # 业务服务（30+服务模块）
│   │   ├── pipelines/    # 数据采集管道
│   │   ├── schemas/      # Pydantic Schema
│   │   └── tests/        # 单元测试（308 tests passed）
│   ├── alembic/          # 数据库迁移
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/
│   ├── admin/            # 管理端（Vite + React + TypeScript）
│   └── user/             # 用户端（Vite + React + TypeScript）
├── sdk/
│   ├── python/           # Python SDK
│   └── typescript/       # TypeScript SDK + React Hooks
├── deploy/               # 部署配置
│   ├── docker-compose.prod.yml
│   └── .env.production
├── design/               # 设计文档（13份）
├── lessons/              # 经验教训库
└── README.md
```

## 快速开始

### 前置条件

- Python 3.11+
- Node.js 20+
- PostgreSQL 18 + pgvector 扩展
- Redis 7

### 后端启动

```bash
cd backend

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入数据库密码等配置

# 数据库迁移
alembic upgrade head

# 启动开发服务器
python -m uvicorn app.main:app --reload --port 8000
```

### 前端启动

```bash
# 管理端 (端口 3001)
cd frontend/admin
npm install
npm run dev

# 用户端 (端口 3002)
cd frontend/user
npm install
npm run dev
```

### Docker Compose 启动

```bash
cd deploy
cp .env.production .env
# 编辑 .env 修改密码和密钥
docker compose -f docker-compose.prod.yml up -d
```

## API 端点

| 类别 | 端点数量 | 前缀 |
|------|---------|------|
| 内部 API v1 | 42 | `/api/v1` |
| 外部 API | 27 | `/api/v1/external` |
| MCP Server | 8 Tools | MCP Protocol |
| 健康检查 | 2 | `/health`, `/` |

### 核心端点

```
GET  /api/v1/contexts                  # 上下文列表
POST /api/v1/contexts                  # 创建上下文
GET  /api/v1/contexts/{id}             # 上下文详情
PUT  /api/v1/contexts/{id}             # 更新上下文
PATCH /api/v1/contexts/{id}/status     # 状态变更
PATCH /api/v1/contexts/{id}/confidence # 可信度调整
DELETE /api/v1/contexts/{id}           # 软删除

POST /api/v1/search                   # 混合搜索（6种模式）
GET  /api/v1/entities                  # 实体管理
GET  /api/v1/entities/graph            # 知识图谱
GET  /api/v1/metrics/overview          # KPI概览
GET  /api/v1/metrics/coverage          # 领域覆盖
GET  /api/v1/metrics/freshness         # 数据新鲜度
GET  /api/v1/metrics/confidence-trends # 可信度趋势
```

### MCP Tools (Agent 调用)

| Tool | 功能 |
|------|------|
| `search_context` | 搜索上下文（含消费指引） |
| `get_context_detail` | 获取完整上下文详情 |
| `get_entity_graph` | 获取实体知识图谱子图 |
| `get_context_timeline` | 获取时间线上下文 |
| `get_contradictions` | 获取矛盾上下文 |
| `submit_context` | Agent 提交新上下文 |
| `check_confidence` | 检查上下文可信度 |
| `submit_correction` | 提交修正建议 |

## SDK 使用

### Python

```python
from context_platform_client import ContextPlatformClient

client = ContextPlatformClient("http://localhost:8000", api_key="cp_xxx")
results = client.search("查询文本", mode="hybrid")
ctx = client.get_context("ctx_abc123")
```

### TypeScript

```typescript
import { ContextPlatformClient, useSearch } from '@context-platform/typescript-sdk';

const client = new ContextPlatformClient('http://localhost:8000', 'cp_xxx');
const results = await client.search('query', 'hybrid');

// React Hooks
const { results, loading, search } = useSearch('query');
```

## 测试

```bash
cd backend
# 运行全部测试 (308 tests)
python -m pytest app/tests/ -v

# 端点验证
bash verify_endpoints.sh
```

测试环境：PostgreSQL 18 + pgvector，数据库 `context_platform_test`

## 设计文档

13份设计文档位于 `design/` 目录：

| 编号 | 文档 | 内容 |
|------|------|------|
| 01 | 产品设计 | 功能模块、用户画像、业务流程、KPI |
| 02 | UI/UX 设计 | 设计系统、组件规范、页面布局 |
| 03 | 数据库设计 | 17张表DDL、索引、约束 |
| 04 | 应用架构 | 五层架构、目录结构、API端点 |
| 05 | 技术实现 | 技术栈选型、CI/CD、风险 |
| 06 | 安全设计 | 等保合规、加密、审计 |
| 07 | 监控运维 | Prometheus + Grafana + Loki |
| 08 | 配置管理 | 120+ 系统参数、热生效 |
| 09 | 接口设计 | 组件化集成、SDK、Webhook |
| 10 | 初始化手册 | 8步初始化流程 |

## 许可

内部项目 — 公司级使用
