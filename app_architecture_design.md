# 统一上下文管理中心 — 应用架构设计 v1.0

> 设计阶段: Phase 1 初始设计
> 依赖文档: 《基础设施设计-v1.0 §15 工程架构设计》

---

## 1. 整体应用架构

### 1.1 五层架构（含组件集成适配层）

```
┌─────────────────────────────────────────────────────────────────┐
│                   消费层 (Consumption Layer)                      │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │ MCP Tool │  │ 父产品后端│  │ 父产品 UI │  │ Web前端      │   │
│  │ (Agent)  │  │ (SDK调用) │  │ (iframe/  │  │ (用户/管理)  │   │
│  │          │  │           │  │  WebComp)  │  │              │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────┬───────┘   │
│       └──────────────┴────────────┴───────────────┘            │
│                          │                                      │
├──────────────────────────┼──────────────────────────────────────┤
│                          ▼                                      │
│             集成适配层 (Integration Adapter Layer) [新增]        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  ├─ Auth Adapter     (API Key / JWT委托 / 自定义Token)  │  │
│  │  ├─ Workspace Middleware (多租户解析 + 数据隔离)         │  │
│  │  ├─ Webhook Emitter  (事件推送 + 签名 + 重试)           │  │
│  │  ├─ Quota Service    (配额管理 + 限流)                  │  │
│  │  └─ UI Adapter       (iframe / WebComponent / SDK)      │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
├──────────────────────────┼──────────────────────────────────────┤
│                          ▼                                      │
│              API网关层 (API Gateway Layer)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  FastAPI Application                                     │  │
│  │  ├─ 认证中间件 (JWT + API Key)                           │  │
│  │  ├─ RBAC权限中间件                                       │  │
│  │  ├─ 请求限流 (SlowAPI)                                   │  │
│  │  ├─ 审计日志拦截器                                       │  │
│  │  └─ CORS中间件                                           │  │
│  └──────────────────────────────────────────────────────────┘  │
│                          │                                      │
├──────────────────────────┼──────────────────────────────────────┤
│                          ▼                                      │
│                   业务服务层 (Service Layer)                     │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐     │
│  │ Context  │ │ Ingestion│ │ Search   │ │ Distribution │     │
│  │ Service  │ │ Service  │ │ Service  │ │ Service      │     │
│  │          │ │         │ │          │ │              │     │
│  │ CRUD     │ │1.去重   │ │ 混合检索 │ │ Push引擎     │     │
│  │ 可信度   │ │2.分类   │ │ 图谱查询 │ │ 规则匹配     │     │
│  │ 生命周期 │ │3.实体抽取│ │ 结果融合 │ │ 消息通知     │     │
│  │ 分类管理 │ │4.关系识别│ │ 权限过滤 │ │ 记忆同步     │     │
│  │          │ │5.可信度  │ │(含entity │ │              │     │
│  │          │ │6.冲突检测│ │ 级聚合)  │ │              │     │
│  │          │ │7.入库   │ │          │ │              │     │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘     │
│       │            │            │              │              │
│  ┌────┴─────┐ ┌────┴─────┐ ┌────┴──────────────┴───────┐     │
│  │Conflict  │ │Permission│ │       Report Service      │     │
│  │Service   │ │Service   │ │  模板填充+上下文注入       │     │
│  │冲突检测  │ │          │ └───────────────────────────┘     │
│  │裁决流程  │ │ RBAC     │                                    │
│  └──────────┘ │ 实体边界 │                                    │
│               │ 敏感度   │                                    │
│               └──────────┘                                    │
│                          │                                      │
├──────────────────────────┼──────────────────────────────────────┤
│                          ▼                                      │
│                   数据访问层 (Data Access Layer)                  │
│                                                                 │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────────┐     │
│  │ SQLAlchemy│ │ pgvector │ │ LightRAG │ │ Mem0 Client  │     │
│  │ ORM      │ │ Client  │ │ Client   │ │              │     │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └──────┬───────┘     │
│       └─────────────┴───────────┴──────────────┘              │
│                          │                                      │
├──────────────────────────┼──────────────────────────────────────┤
│                          ▼                                      │
│                    存储层 (Storage Layer)                        │
│  ┌────────────────┐  ┌────────────┐  ┌───────────────────┐    │
│  │ PostgreSQL 16  │  │  Qdrant    │  │ 文件系统 (iCloud) │    │
│  │ + pgvector     │  │  (Mem0)    │  │ 附件/MEMORY.md    │    │
│  │ + pg_bestmatch │  └────────────┘  └───────────────────┘    │
│  └────────────────┘                                            │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 架构决策：为什么选单体而非微服务

| 考量维度 | 单体应用 | 微服务 |
|---------|---------|--------|
| 团队规模 | 小团队（<10人）✅ | 多团队 |
| 数据耦合 | 强关联（图谱查询需跨表JOIN）✅ | 松耦合 |
| 部署复杂度 | 简单（单进程）✅ | 复杂 |
| 开发效率 | 高（Phase 1-3）✅ | 初期低 |
| 扩展需求 | 可垂直扩展 | 水平扩展 |
| 未来演进 | 可逐步拆分为微服务 | - |

**决策**：Phase 1-3 采用单体应用（Modular Monolith），模块间通过明确的Python接口通信而非HTTP。当用户数或数据量级增长到单体瓶颈时，将采集服务（Ingestion Service）和检索服务（Search Service）独立为微服务。组件化接口通过**新增集成适配层 (Integration Adapter Layer)** 实现，该层位于 API 网关层之上，负责将外部父产品的调用适配到内部服务层。

---

## 2. 项目目录结构

```
context-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI 应用入口
│   │   ├── config.py                  # 配置管理（环境变量/文件）
│   │   ├── dependencies.py            # FastAPI 依赖注入
│   │   │
│   │   ├── api/                       # API路由层
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── router.py          # v1路由聚合
│   │   │   │   ├── context.py         # /api/v1/contexts
│   │   │   │   ├── search.py          # /api/v1/search
│   │   │   │   ├── entities.py        # /api/v1/entities
│   │   │   │   ├── relations.py       # /api/v1/relations
│   │   │   │   ├── users.py           # /api/v1/users
│   │   │   │   ├── permissions.py     # /api/v1/permissions
│   │   │   │   ├── review.py          # /api/v1/review [增强:结构化反馈/智能队列]
│   │   │   │   ├── feedback.py        # /api/v1/feedback (RLHF反馈管理) [新增]
│   │   │   │   ├── classification_rules.py # /api/v1/classification-rules (分类规则管理) [新增]
│   │   │   │   ├── rlhf.py            # /api/v1/rlhf (RLHF管道控制) [新增]
│   │   │   │   ├── reports.py         # /api/v1/reports
│   │   │   │   ├── metrics.py         # /api/v1/metrics
│   │   │   │   ├── webhooks.py        # /api/v1/webhooks
│   │   │   │   ├── config.py          # /api/v1/admin/config（系统配置管理）
│   │   │   │   └── settings.py        # /api/v1/settings（用户设置管理）
│   │   │   ├── external/              # 外部API路由（组件化接口）[新增]
│   │   │   │   ├── router.py         # 外部API路由聚合
│   │   │   │   ├── auth.py           # 认证端点（API Key/JWT/自定义Token）
│   │   │   │   ├── contexts.py       # 外部上下文CRUD端点
│   │   │   │   ├── search.py         # 外部搜索端点
│   │   │   │   ├── entities.py       # 外部实体管理端点
│   │   │   │   ├── workspaces.py     # 工作区管理端点
│   │   │   │   └── health.py         # 健康检查端点
│   │   │   └── mcp/                   # MCP Server端点
│   │   │       ├── server.py          # MCP Server注册
│   │   │       └── tools/
│   │   │           ├── search_context.py
│   │   │           ├── get_entity_graph.py
│   │   │           └── submit_context.py
│   │   │
│   │   ├── core/                      # 核心基础设施
│   │   │   ├── security.py            # JWT认证+密码哈希
│   │   │   ├── rbac.py               # RBAC权限检查
│   │   │   ├── audit.py              # 审计日志
│   │   │   └── rate_limit.py         # 请求限流
│   │   │
│   │   ├── services/                  # 业务服务层
│   │   │   ├── context_service.py     # 上下文CRUD+状态管理
│   │   │   ├── ingestion_service.py   # 采集管道
│   │   │   ├── classification_service.py  # 自动分类
│   │   │   ├── entity_service.py      # 实体抽取和管理
│   │   │   ├── relation_service.py    # 关系建模
│   │   │   ├── confidence_service.py  # 可信度评估
│   │   │   ├── lifecycle_service.py   # 生命周期状态机
│   │   │   ├── search_service.py      # 混合检索
│   │   │   ├── graph_service.py       # 图谱查询
│   │   │   ├── conflict_service.py    # 冲突检测与裁决
│   │   │   ├── distribution_service.py# Push/Pull分发
│   │   │   ├── permission_service.py  # 权限计算
│   │   │   ├── report_service.py      # 报告生成
│   │   │   ├── metrics_service.py     # 指标采集
│   │   │   ├── config_service.py      # 配置管理（系统配置+用户设置+缓存+热生效）
│   │   │   ├── guidance_service.py    # Agent消费指引生成（引用建议+交叉验证提示+经验库标记）
│   │   │   ├── sync_service.py        # 记忆同步
│   │   │   ├── feedback_service.py    # RLHF:反馈收集/聚合/统计/审核员画像/异常检测 [新增]
│   │   │   ├── classification_learning_service.py # RLHF:规则学习/权重更新/关键词发现/效果评估 [新增]
│   │   │   └── confidence_calibration_service.py  # RLHF:可信度校准/加权评分/漂移检测 [新增]
│   │   │
│   │   ├── integrations/              # 外部系统集成
│   │   │   ├── adapter.py             # 集成适配层入口（组件化接口核心）[新增]
│   │   │   ├── auth/                   # 认证适配器 [新增]
│   │   │   │   ├── api_key_auth.py    # API Key 认证
│   │   │   │   ├── jwt_delegation.py  # JWT 委托认证
│   │   │   │   └── custom_token_auth.py # 自定义Token回调认证
│   │   │   ├── workspace/              # 工作区/多租户管理 [新增]
│   │   │   │   ├── workspace_service.py
│   │   │   │   ├── quota_service.py
│   │   │   │   └── workspace_middleware.py
│   │   │   ├── event_emitter.py       # Webhook事件发射器 [新增]
│   │   │   ├── project_kb_client.py   # 项目知识库API（IMA/飞书云盘/其他云盘）
│   │   │   ├── memory_md_parser.py    # Memory.md文件解析器（项目/客户识别+上下文提取）
│   │   │   ├── feishu_client.py       # 飞书API
│   │   │   ├── feishu_bot.py          # 飞书Bot
│   │   │   ├── email_client.py        # 邮件
│   │   │   ├── finance_client.py      # 财报API
│   │   │   └── mem0_client.py         # Mem0
│   │   │
│   │   ├── models/                    # SQLAlchemy ORM模型
│   │   │   ├── base.py
│   │   │   ├── context.py
│   │   │   ├── entity.py
│   │   │   ├── relation.py
│   │   │   ├── user.py
│   │   │   ├── permission.py
│   │   │   ├── audit.py
│   │   │   ├── push_rule.py
│   │   │   ├── notification.py
│   │   │   ├── system_config.py       # 系统配置表ORM
│   │   │   ├── user_setting.py        # 用户设置表ORM
│   │   │   ├── workspace.py           # 工作区/租户表ORM [新增]
│   │   │   ├── api_key.py             # API Key表ORM [新增]
│   │   │   └── jwt_config.py          # JWT配置表ORM [新增]
│   │   │
│   │   ├── schemas/                   # Pydantic请求/响应模型
│   │   │   ├── context.py
│   │   │   ├── search.py
│   │   │   ├── entity.py
│   │   │   ├── user.py
│   │   │   └── ...
│   │   │
│   │   └── pipelines/                 # 采集管道（Prefect Flow）
│   │       ├── project_kb_pipeline.py
│   │       ├── memory_md_pipeline.py   # Memory.md文件监听+解析导入管道
│   │       ├── feishu_pipeline.py
│   │       └── dedup_pipeline.py
│   │
│   ├── alembic/                       # 数据库迁移
│   │   ├── versions/
│   │   └── env.py
│   │
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── conftest.py
│   │
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pyproject.toml
│
├── frontend/
│   ├── admin/                         # 管理端（Refine + shadcn/ui）
│   │   ├── src/
│   │   │   ├── App.tsx
│   │   │   ├── authProvider.ts
│   │   │   ├── dataProvider.ts
│   │   │   ├── accessControlProvider.ts
│   │   │   ├── pages/
│   │   │   │   ├── dashboard/
│   │   │   │   ├── contexts/
│   │   │   │   ├── review/
│   │   │   │   ├── users/
│   │   │   │   ├── metrics/
│   │   │   │   └── settings/
│   │   │   └── components/
│   │   └── package.json
│   │
│   └── user/                          # 用户端（自定义React + shadcn/ui + Cytoscape.js）
│       ├── src/
│       │   ├── App.tsx
│       │   ├── pages/
│       │   │   ├── SearchPage.tsx
│       │   │   ├── GraphPage.tsx
│       │   │   ├── ContextDetailPage.tsx
│       │   │   ├── WorkspacePage.tsx
│       │   │   └── NotificationsPage.tsx
│       │   ├── components/
│       │   │   ├── graph/
│       │   │   │   ├── GraphCanvas.tsx     # Cytoscape.js封装
│       │   │   │   ├── GraphSidebar.tsx
│       │   │   │   └── GraphLegend.tsx
│       │   │   ├── search/
│       │   │   │   ├── SearchBar.tsx
│       │   │   │   ├── SearchFilters.tsx
│       │   │   │   └── ContextCard.tsx
│       │   │   ├── context/
│       │   │   │   ├── ConfidenceBadge.tsx
│       │   │   │   ├── LifecycleTimeline.tsx
│       │   │   │   └── RelationList.tsx
│       │   │   └── shared/
│       │   └── hooks/
│       │       ├── useSearch.ts
│       │       ├── useGraph.ts
│       │       └── useWebSocket.ts
│       └── package.json
│
├── sdk/                              # 客户端SDK（独立发布给父产品使用）[新增]
│   ├── python/
│   │   ├── context_platform_client/
│   │   │   ├── __init__.py
│   │   │   ├── client.py
│   │   │   ├── models.py
│   │   │   └── events.py
│   │   └── pyproject.toml
│   └── typescript/
│       ├── src/
│       │   ├── index.ts
│       │   ├── client.ts
│       │   ├── types.ts
│       │   └── events.ts
│       └── package.json
│
├── plugin-manifest.json              # 组件清单文件 [新增]
├── docker-compose.yml
├── Makefile
└── README.md
```

---

## 3. RESTful API 设计

### 3.1 API 版本与基础路径

- 基础路径: `/api/v1`
- 认证方式: Bearer JWT Token
- 请求格式: JSON
- 响应格式: `{ "data": ..., "meta": { "total": ..., "page": ..., "page_size": ... }, "error": null }`
- 错误格式: `{ "data": null, "error": { "code": "...", "message": "..." } }`

### 3.2 核心API端点

#### 上下文管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/contexts` | 列表查询（分页+筛选） | 按角色 |
| POST | `/api/v1/contexts` | 创建上下文 | senior+ |
| GET | `/api/v1/contexts/{id}` | 获取详情 | 按角色+边界 |
| PUT | `/api/v1/contexts/{id}` | 更新上下文 | senior+ |
| DELETE | `/api/v1/contexts/{id}` | 软删除 | admin+ |
| PATCH | `/api/v1/contexts/{id}/status` | 变更生命周期状态 | admin+ |
| PATCH | `/api/v1/contexts/{id}/confidence` | 变更可信度 | admin+ |

#### 混合检索

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/search` | 统一搜索入口 |

请求体示例：
```json
{
    "query": "利欧泵业中东市场哥伦布项目",
    "mode": "hybrid",
    "filters": {
        "domain": ["customer", "external"],
        "confidence_min": "L3",
        "date_from": "2026-01-01",
        "date_to": "2026-06-30",
        "status": ["active"],
        "entities": ["利欧泵业", "哥伦布项目"]
    },
    "page": 1,
    "page_size": 20,
    "include_relations": true
}
```

#### 实体与关系

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/entities` | 实体列表 |
| POST | `/api/v1/entities` | 创建实体 |
| GET | `/api/v1/entities/{id}/graph` | 获取实体关联图谱（2跳） |
| GET | `/api/v1/relations` | 关系列表 |
| POST | `/api/v1/relations` | 创建关系 |
| DELETE | `/api/v1/relations/{id}` | 删除关系 |

#### 审核队列

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/review/queue` | 获取审核队列 | admin+partner+senior_consultant |
| GET | `/api/v1/review/queue/smart` | 智能排序审核队列 | admin+partner+senior_consultant |
| POST | `/api/v1/review/{id}/decide` | 结构化审核决策（含分类纠正/可信度评分/质量评分） | admin+partner+senior_consultant |
| POST | `/api/v1/review/{id}/approve` | [兼容] 审核通过 | admin+partner+senior_consultant |
| POST | `/api/v1/review/{id}/reject` | [兼容] 审核驳回 | admin+partner+senior_consultant |
| GET | `/api/v1/review/stats` | 审核统计 | admin+partner+senior_consultant |
| GET | `/api/v1/review/history` | 审核历史 | admin+partner+senior_consultant |
| POST | `/api/v1/review/batch` | 批量审核 | admin+partner |
| POST | `/api/v1/review/resolve-conflict` | 裁决冲突 | admin+partner |

#### RLHF 反馈管理 [新增]

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/feedback/labels` | 提交分类标注 | admin+partner+senior_consultant+consultant |
| GET | `/api/v1/feedback/labels` | 查询标注列表 | admin+partner+senior_consultant |
| GET | `/api/v1/feedback/stats` | 反馈统计 | admin+partner+senior_consultant |
| GET | `/api/v1/feedback/reviewer/{id}` | 审核员画像 | admin+partner+senior_consultant |
| GET | `/api/v1/feedback/anomalies` | 异常反馈检测 | admin+partner |
| GET | `/api/v1/feedback/golden-samples` | 金标准样本列表 | admin+partner+senior_consultant |
| POST | `/api/v1/feedback/golden-samples/{id}` | 标记金标准样本 | admin+partner |

#### RLHF 分类规则管理 [新增]

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/classification-rules` | 规则列表（支持按权重/domain/status筛选） | admin+partner+senior_consultant |
| POST | `/api/v1/classification-rules` | 手动创建规则 | admin+partner |
| PUT | `/api/v1/classification-rules/{id}` | 更新规则（权重/状态） | admin+partner |
| DELETE | `/api/v1/classification-rules/{id}` | 删除规则 | admin |
| GET | `/api/v1/classification-rules/evaluate` | 评估当前规则效果 | admin+partner |
| GET | `/api/v1/classification-rules/suggestions` | 系统建议的规则调整 | admin+partner |
| POST | `/api/v1/classification-rules/apply-suggestions` | 批量应用建议规则 | admin+partner |
| GET | `/api/v1/classification-rules/keywords/discover` | 发现候选关键词 | admin+partner |

#### RLHF 管道控制 [新增]

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/rlhf/status` | RLHF 管道状态概览 | admin+partner+senior_consultant |
| POST | `/api/v1/rlhf/datasets/build` | 构建反馈数据集 | admin+partner |
| GET | `/api/v1/rlhf/datasets` | 数据集列表 | admin+partner+senior_consultant |
| POST | `/api/v1/rlhf/learn` | 触发规则学习 | admin+partner |
| GET | `/api/v1/rlhf/learn/logs` | 学习日志列表 | admin+partner+senior_consultant |
| POST | `/api/v1/rlhf/learn/rollback/{id}` | 回滚学习结果 | admin |
| GET | `/api/v1/rlhf/learn/preview` | 预览学习效果（dry run） | admin+partner |
| POST | `/api/v1/rlhf/calibrate` | 触发可信度校准 | admin+partner |
| GET | `/api/v1/rlhf/metrics` | RLHF 效果指标 | admin+partner+senior_consultant |

#### 用户与权限

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/users` | 用户列表 | admin |
| POST | `/api/v1/users` | 创建用户 | admin |
| PUT | `/api/v1/users/{id}` | 更新用户 | admin |
| GET | `/api/v1/permissions/check` | 检查权限 | 所有 |
| PUT | `/api/v1/permissions/{context_id}` | 修改权限 | admin+partner |

#### 指标

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/metrics/overview` | 全局指标概览 |
| GET | `/api/v1/metrics/coverage` | 覆盖率详情 |
| GET | `/api/v1/metrics/freshness` | 新鲜度详情 |

#### 系统配置（管理端）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/admin/config` | 获取全部系统配置（按分组） | admin |
| GET | `/api/v1/admin/config/{section}` | 获取指定分组配置 | admin |
| PUT | `/api/v1/admin/config/{section}` | 批量更新指定分组配置 | admin |
| PUT | `/api/v1/admin/config/{section}/{key}` | 更新单个配置项 | admin |
| POST | `/api/v1/admin/config/{section}/reset` | 重置指定分组为默认值 | admin |
| POST | `/api/v1/admin/config/reset-all` | 重置全部配置为默认值 | admin |
| GET | `/api/v1/admin/config/env` | 获取环境变量列表（只读展示） | admin |
| GET | `/api/v1/admin/config/changes` | 获取配置变更日志（分页） | admin |

#### 用户设置

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/settings` | 获取当前用户全部设置 | 登录用户 |
| GET | `/api/v1/settings/{section}` | 获取当前用户指定分组设置 | 登录用户 |
| PUT | `/api/v1/settings/{section}` | 批量更新当前用户指定分组设置 | 登录用户 |
| PUT | `/api/v1/settings/{section}/{key}` | 更新当前用户单个设置项 | 登录用户 |
| PUT | `/api/v1/admin/users/{id}/settings/{section}` | 管理员更新指定用户设置 | admin |

#### 外部API（组件化接口）

> 完整外部API设计见《组件化接口设计》(09_interface_design.md)。本节仅列出端点概要。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/external/health` | 健康检查 | 无 |
| GET | `/api/v1/external/health/metrics` | Prometheus指标 | 无 |
| POST | `/api/v1/external/auth/verify-api-key` | 验证API Key | 无 |
| GET | `/api/v1/external/auth/whoami` | 当前身份信息 | 外部认证 |
| POST | `/api/v1/external/auth/api-keys` | 创建API Key | system_admin |
| GET | `/api/v1/external/auth/api-keys` | 列出API Key | system_admin |
| DELETE | `/api/v1/external/auth/api-keys/{id}` | 撤销API Key | system_admin |
| PUT | `/api/v1/external/auth/jwt-config` | 配置JWT委托认证 | system_admin |
| PUT | `/api/v1/external/auth/custom-config` | 配置自定义Token认证 | system_admin |
| POST | `/api/v1/external/workspaces` | 创建工作区 | system_admin |
| GET | `/api/v1/external/workspaces` | 工作区列表 | system_admin |
| GET | `/api/v1/external/workspaces/{id}` | 工作区详情 | workspace_admin |
| PUT | `/api/v1/external/workspaces/{id}` | 更新工作区 | system_admin |
| DELETE | `/api/v1/external/workspaces/{id}` | 删除工作区 | system_admin |
| GET | `/api/v1/external/contexts` | 上下文列表 | context:read |
| POST | `/api/v1/external/contexts` | 创建上下文 | context:write |
| GET | `/api/v1/external/contexts/{id}` | 上下文详情 | context:read |
| PUT | `/api/v1/external/contexts/{id}` | 更新上下文 | context:write |
| DELETE | `/api/v1/external/contexts/{id}` | 软删除 | context:delete |
| POST | `/api/v1/external/contexts/batch` | 批量导入 | context:write |
| POST | `/api/v1/external/search` | 混合搜索 | search:execute |
| GET | `/api/v1/external/search/suggestions` | 搜索建议 | search:execute |
| GET | `/api/v1/external/entities` | 实体列表 | 外部认证 |
| POST | `/api/v1/external/entities` | 创建/更新实体 | 外部认证 |
| GET | `/api/v1/external/entities/{id}` | 实体详情 | 外部认证 |
| GET | `/api/v1/external/entities/{id}/graph` | 实体图谱 | 外部认证 |

#### Webhooks

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/webhooks/feishu` | 飞书事件回调 |

---

## 4. WebSocket 实时通信

### 4.1 连接管理

```
ws://host/ws?token={jwt_token}
```

### 4.2 消息类型

**服务端→客户端（Push）**：

| 事件类型 | 数据 | 触发条件 |
|---------|------|---------|
| `context.updated` | context_id + changes | 上下文被修改 |
| `context.conflict` | context_id + conflict_detail | 检测到矛盾 |
| `context.expiring` | context_id + days_remaining | 即将衰减（30天内） |
| `review.new_task` | task_id + context_summary | 新的审核任务 |
| `alert.push` | alert_detail | 规则触发的告警 |
| `metrics.updated` | metric_name + value | 指标变化 |

**客户端→服务端**：

| 事件类型 | 数据 |
|---------|------|
| `subscribe` | `{ channels: ["context.{id}", "review"] }` |
| `unsubscribe` | `{ channels: ["context.{id}"] }` |
| `ping` | 心跳 |

---

## 5. MCP Server 接口设计

### 5.1 工具定义

Context Platform MCP Server 对外暴露以下8个Tools供Agent（问登）调用。每个查询类Tool的返回结果中自动附带消费指引（`consumption_guidance`）字段，帮助Agent做出正确的引用决策。

**消费指引的设计目的**：借鉴 Manus 上下文工程"Read-Before-Decide"原则——Agent 在做出关键决策前应充分理解上下文的可信度和关联性。消费指引字段自动生成以下内容：(1) 根据可信度等级给出引用建议（自由引用/标注来源/需验证/不可引用）；(2) 当同一实体存在更高可信度的关联上下文时，主动提示 Agent 一并检索；(3) 当上下文标记为"经验教训"类型时，提示 Agent 优先参考。

| Tool名 | 参数 | 返回 | 用途 |
|--------|------|------|------|
| `search_context` | query, mode, filters | 上下文列表 + consumption_guidance | Agent诊断检索 |
| `get_context_detail` | context_id | 上下文完整详情 + consumption_guidance | 获取单条上下文 |
| `get_entity_graph` | entity_name, depth | 实体级聚合子图JSON | 获取实体关系图谱（entity级聚合，非context级） |
| `get_context_timeline` | entity_name, date_range | 时间线上下文 | 时间序列分析 |
| `get_contradictions` | entity_name | 矛盾上下文列表 | 矛盾查询 |
| `submit_context` | title, content, source | context_id | Agent自动提交上下文（标记L2） |
| `check_confidence` | context_id | 可信度详情+溯源链 | 可信度验证 |
| `submit_correction` | context_id, correction | result | Agent提交纠错建议 |

**消费指引（consumption_guidance）字段结构**：

```json
{
  "usage_advice": "自由引用|标注来源后引用|需交叉验证|不可引用",
  "advice_reason": "该上下文来自官方财报，可信度L4，可标注来源后直接引用",
  "related_higher_confidence_count": 2,
  "related_higher_confidence_hint": "同实体下存在2条L4+可信度的关联上下文，建议一并检索",
  "is_lesson_learned": false,
  "cross_validation_suggestion": "该上下文可信度L2，关联条目'利欧泵业Q1审计报告'(L5)可能包含更可靠的同主题信息"
}
```

**consumption_guidance 生成规则**：

| 条件 | usage_advice | 附加行为 |
|------|-------------|---------|
| L5 (权威验证) | "自由引用" | 不附加提示 |
| L4 (高可信) | "标注来源后引用" | 提示标注来源系统 |
| L3 (中等可信) | "需交叉验证" | 检查同实体下是否有L4+同主题上下文，有则提示 |
| L2 (待验证) | "不可引用，仅辅助参考" | 同上，且额外提示交叉验证建议 |
| L1 (低可信) | "不可引用" | 标记仅作参考 |
| L0 (不可用) | "不可引用" | 标记已过期/存在矛盾 |
| context_subtype="lesson_learned" | 自动升一级建议 | 优先展示，标注"经验库" |

### 5.2 MCP Server注册

```python
# app/api/mcp/server.py（伪代码）
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Context Platform")

@mcp.tool()
async def search_context(
    query: str,
    mode: str = "hybrid",
    filters: dict = None
) -> dict:
    """搜索上下文，支持关键词/语义/图谱/混合模式。
    返回结果包含 items（上下文列表）和 consumption_guidance（消费指引），
    帮助Agent根据可信度等级和关联性做出正确的引用决策。
    """
    result = await search_service.search(query, mode, filters)
    guidance = await guidance_service.generate_search_guidance(result.items)
    return {"items": result.items, "total": result.total, "consumption_guidance": guidance}

@mcp.tool()
async def get_context_detail(context_id: str) -> dict:
    """获取单条上下文完整详情，附带消费指引。
    指引包括：该上下文的引用建议、同实体下可交叉验证的高可信度关联上下文提示、
    若为经验教训类型则标注'经验库'并优先展示。
    """
    context = await context_service.get_detail(context_id)
    guidance = await guidance_service.generate_detail_guidance(context)
    return {"context": context, "consumption_guidance": guidance}

@mcp.tool()
async def get_entity_graph(
    entity_name: str,
    depth: int = 2
) -> GraphData:
    """获取指定实体的关联图谱，depth控制跳数"""
    return await graph_service.get_subgraph(entity_name, depth)
```

---

## 6. 部署架构

### 6.1 开发环境（Docker Compose）

```yaml
# docker-compose.yml
services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: context_platform
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports: ["5432:5432"]
    volumes: ["pgdata:/var/lib/postgresql/data"]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      DATABASE_URL: postgresql://admin:${DB_PASSWORD}@db:5432/context_platform
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
    depends_on: [db]

  qdrant:
    image: qdrant/qdrant
    ports: ["6333:6333"]
    volumes: ["qdrant_data:/qdrant/storage"]

  frontend-admin:
    build: ./frontend/admin
    ports: ["3001:3000"]

  frontend-user:
    build: ./frontend/user
    ports: ["3002:3000"]
```

### 6.2 生产环境（待定 [待决策]）

推荐方案：使用 Dokploy 或 Coolify 进行单机部署（适合小团队），Phase 3后再评估是否需要迁移到K8s。

---

## 7. 安全设计

### 7.1 认证

- JWT Token（access_token: 30分钟, refresh_token: 7天）
- API Key（用于Agent/MCP Server，无限期）
- 飞书OAuth（可选，用于飞书Bot认证）

### 7.2 三层权限模型（PermissionService 接口规范）

`permission_service.py` 是自研核心组件，实现三层权限模型的全部逻辑。以下接口定义可直接用于生成代码。

#### 7.2.1 数据类定义

```python
from enum import StrEnum
from dataclasses import dataclass, field
from typing import Optional, List, Set, Tuple
from uuid import UUID
from datetime import datetime, timedelta
import hashlib
import json

class Role(StrEnum):
    ADMIN = "admin"
    PARTNER = "partner"
    SENIOR_CONSULTANT = "senior_consultant"
    CONSULTANT = "consultant"
    AGENT = "agent"

class Visibility(StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    TOP_SECRET = "top_secret"

class Action(StrEnum):
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    CHANGE_STATUS = "change_status"
    CHANGE_CONFIDENCE = "change_confidence"
    SUBMIT_CORRECTION = "submit_correction"
    APPROVE_CORRECTION = "approve_correction"
    MANAGE_USERS = "manage_users"
    MANAGE_RULES = "manage_rules"
    VIEW_TOP_SECRET = "view_top_secret"
    VIEW_CONFIDENTIAL = "view_confidential"

@dataclass
class AccessResult:
    allowed: bool
    reason: str
    denied_layer: Optional[int] = None  # 1=RBAC, 2=EntityBoundary, 3=Sensitivity

@dataclass
class EffectiveFilters:
    allowed_entity_ids: List[UUID]
    max_sensitivity: Visibility
    excluded_statuses: List[str] = field(default_factory=list)
    is_admin: bool = False
```

#### 7.2.2 角色权限矩阵常量

```python
ROLE_ACTION_MATRIX: dict[Role, Set[Action]] = {
    Role.ADMIN: {
        Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE,
        Action.CHANGE_STATUS, Action.CHANGE_CONFIDENCE,
        Action.SUBMIT_CORRECTION, Action.APPROVE_CORRECTION,
        Action.MANAGE_USERS, Action.MANAGE_RULES,
        Action.VIEW_TOP_SECRET, Action.VIEW_CONFIDENTIAL,
    },
    Role.PARTNER: {
        Action.CREATE, Action.READ, Action.UPDATE, Action.DELETE,
        Action.CHANGE_STATUS, Action.CHANGE_CONFIDENCE,
        Action.SUBMIT_CORRECTION, Action.APPROVE_CORRECTION,
        Action.VIEW_TOP_SECRET, Action.VIEW_CONFIDENTIAL,
    },
    Role.SENIOR_CONSULTANT: {
        Action.CREATE, Action.READ, Action.UPDATE,
        Action.SUBMIT_CORRECTION, Action.VIEW_CONFIDENTIAL,
    },
    Role.CONSULTANT: {
        Action.CREATE, Action.READ, Action.UPDATE,
        Action.SUBMIT_CORRECTION, Action.VIEW_CONFIDENTIAL,
    },
    Role.AGENT: {
        Action.CREATE, Action.READ, Action.UPDATE,
        Action.SUBMIT_CORRECTION, Action.VIEW_CONFIDENTIAL,
    },
}
```

#### 7.2.3 敏感度访问矩阵常量

```python
SENSITIVITY_ROLE_MATRIX: dict[Visibility, Set[Role]] = {
    Visibility.PUBLIC:      {Role.ADMIN, Role.PARTNER, Role.SENIOR_CONSULTANT, Role.CONSULTANT, Role.AGENT},
    Visibility.INTERNAL:    {Role.ADMIN, Role.PARTNER, Role.SENIOR_CONSULTANT, Role.CONSULTANT, Role.AGENT},
    Visibility.CONFIDENTIAL: {Role.ADMIN, Role.PARTNER, Role.SENIOR_CONSULTANT, Role.CONSULTANT, Role.AGENT},
    Visibility.TOP_SECRET:  {Role.ADMIN, Role.PARTNER},
}
```

#### 7.2.4 PermissionService 类定义

```python
class PermissionService:
    """三层权限模型引擎。通过 FastAPI 依赖注入使用，单例模式。"""

    CACHE_TTL_SECONDS: int = 300
    CACHE_MAX_ENTRIES: int = 10000

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._local_cache: dict[str, tuple[AccessResult, float]] = {}

    # ========== 入口方法 ==========

    async def check_access(
        self, user_id: UUID, context_id: UUID, action: Action,
        is_agent: bool = False
    ) -> AccessResult:
        """三层权限检查入口：Layer1 → Layer2 → Layer3，含缓存。

        Args:
            user_id: 用户ID
            context_id: 上下文ID
            action: 请求的操作
            is_agent: 是否为Agent请求（通过API Key认证的标记）

        Returns:
            AccessResult(allowed, reason, denied_layer)
        """
        cache_key = self._build_cache_key(user_id, context_id, action)
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        # 获取用户信息（含角色、全局标记、实体分配）
        user = await self._get_user_with_role(user_id)
        context = await self._get_context_with_permissions(context_id)

        # Layer 1: RBAC
        result = self._check_layer1_rbac(user["role"], action, is_agent)
        if not result.allowed:
            await self._cache_set(cache_key, result)
            return result

        # Layer 2: Entity Boundary
        result = await self._check_layer2_entity_boundary(
            user_id, user["role"], user.get("partner_scope"), context_id, is_agent
        )
        if not result.allowed:
            await self._cache_set(cache_key, result)
            return result

        # Layer 3: Sensitivity
        result = self._check_layer3_sensitivity(
            user["role"], context["sensitivity"], is_agent
        )
        await self._cache_set(cache_key, result)
        return result

    # ========== Layer 1: RBAC ==========

    def _check_layer1_rbac(
        self, role: str, action: Action, is_agent: bool = False
    ) -> AccessResult:
        """角色权限检查。直接匹配矩阵，纯函数无IO。"""
        role_enum = Role(role)
        allowed_actions = ROLE_ACTION_MATRIX.get(role_enum, set())
        if action not in allowed_actions:
            return AccessResult(
                allowed=False,
                reason=f"role {role} lacks action {action.value}",
                denied_layer=1
            )
        return AccessResult(allowed=True, reason="rbac_passed")

    # ========== Layer 2: Entity Boundary ==========

    async def _check_layer2_entity_boundary(
        self, user_id: UUID, role: str, partner_scope: str,
        context_id: UUID, is_agent: bool = False
    ) -> AccessResult:
        """实体边界检查。

        跳过条件:
        - role == admin
        - role == partner && partner_scope == 'global'
        - is_agent == True
        """
        if role == Role.ADMIN:
            return AccessResult(allowed=True, reason="admin_global")
        if role == Role.PARTNER and partner_scope == "global":
            return AccessResult(allowed=True, reason="partner_global")
        if is_agent:
            return AccessResult(allowed=True, reason="agent_skip_entity_boundary")

        context_entity_ids = await self._get_context_entity_ids(context_id)
        user_entity_ids = await self.get_user_entities(user_id)

        if not set(context_entity_ids) & set(user_entity_ids):
            return AccessResult(
                allowed=False,
                reason="no_common_entity",
                denied_layer=2
            )
        return AccessResult(allowed=True, reason="entity_boundary_passed")

    # ========== Layer 3: Sensitivity ==========

    def _check_layer3_sensitivity(
        self, role: str, sensitivity: str, is_agent: bool = False
    ) -> AccessResult:
        """敏感度检查。纯函数无IO。"""
        role_enum = Role(role)
        vis = Visibility(sensitivity)

        # Agent 特殊拦截: top_secret 不可见
        if is_agent and vis == Visibility.TOP_SECRET:
            return AccessResult(
                allowed=False,
                reason="agent_blocked_top_secret",
                denied_layer=3
            )

        allowed_roles = SENSITIVITY_ROLE_MATRIX.get(vis, set())
        if role_enum not in allowed_roles:
            return AccessResult(
                allowed=False,
                reason=f"role {role} cannot access {sensitivity}",
                denied_layer=3
            )
        return AccessResult(allowed=True, reason="sensitivity_passed")

    # ========== 查询辅助方法 ==========

    async def get_user_entities(self, user_id: UUID) -> List[UUID]:
        """获取用户分配的实体列表（含缓存）。"""
        cache_key = f"user_entities:{user_id}"
        cached = await self._cache_get(cache_key)
        if cached is not None:
            return cached

        rows = await db.fetch_all(
            "SELECT entity_id FROM user_entity_assignments WHERE user_id = $1",
            user_id
        )
        result = [r["entity_id"] for r in rows]
        await self._cache_set(cache_key, result, ttl=600)
        return result

    async def get_effective_filters(
        self, user_id: UUID, role: str, partner_scope: str = "specific"
    ) -> EffectiveFilters:
        """获取用户的有效查询过滤器，用于SQL层预过滤。

        Returns:
            EffectiveFilters: 包含allowed_entity_ids, max_sensitivity等，
            可直接拼入 WHERE 子句。
        """
        role_enum = Role(role)
        is_admin = (role_enum == Role.ADMIN)

        if is_admin or (role_enum == Role.PARTNER and partner_scope == "global"):
            return EffectiveFilters(
                allowed_entity_ids=[],
                max_sensitivity=Visibility.TOP_SECRET,
                is_admin=True
            )

        if role_enum == Role.AGENT:
            return EffectiveFilters(
                allowed_entity_ids=[],
                max_sensitivity=Visibility.CONFIDENTIAL,
                is_admin=False
            )

        entities = await self.get_user_entities(user_id)
        return EffectiveFilters(
            allowed_entity_ids=entities,
            max_sensitivity=Visibility.CONFIDENTIAL,
            is_admin=False
        )

    async def get_accessible_contexts(
        self, user_id: UUID, role: str, partner_scope: str = "specific",
        domain: Optional[str] = None, limit: int = 50, offset: int = 0
    ) -> Tuple[List[UUID], int]:
        """获取用户可见的上下文ID列表（带分页），用于列表页。

        利用 get_effective_filters 在SQL层预过滤，避免逐条权限检查。
        """
        filters = await self.get_effective_filters(user_id, role, partner_scope)

        conditions = ["p.sensitivity <= $max_sensitivity"]
        params = {"max_sensitivity": filters.max_sensitivity}

        if not filters.is_admin and filters.allowed_entity_ids:
            conditions.append(
                "c.id IN (SELECT cem.context_id FROM context_entities_map cem "
                "WHERE cem.entity_id = ANY($entity_ids))"
            )
            params["entity_ids"] = filters.allowed_entity_ids

        if domain:
            conditions.append("c.domain = $domain")
            params["domain"] = domain

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT c.id FROM context_items c
            JOIN permissions p ON c.id = p.context_id
            WHERE {where_clause}
            ORDER BY c.created_at DESC
            LIMIT $limit OFFSET $offset
        """
        params["limit"] = limit
        params["offset"] = offset
        rows = await db.fetch_all(query, params)

        # Total count
        count_query = f"""
            SELECT COUNT(*) FROM context_items c
            JOIN permissions p ON c.id = p.context_id
            WHERE {where_clause}
        """
        total = await db.fetch_val(count_query, params)
        return [r["id"] for r in rows], total

    # ========== 实体分配管理 ==========

    async def assign_user_to_entity(
        self, user_id: UUID, entity_id: UUID, assigned_by: UUID
    ) -> None:
        await db.execute(
            """INSERT INTO user_entity_assignments (user_id, entity_id, assigned_by)
               VALUES ($1, $2, $3)
               ON CONFLICT (user_id, entity_id) DO NOTHING""",
            user_id, entity_id, assigned_by
        )
        await self.invalidate_user_cache(user_id)

    async def unassign_user_from_entity(
        self, user_id: UUID, entity_id: UUID
    ) -> None:
        await db.execute(
            "DELETE FROM user_entity_assignments WHERE user_id=$1 AND entity_id=$2",
            user_id, entity_id
        )
        await self.invalidate_user_cache(user_id)

    async def auto_assign_creator_to_entity(
        self, user_id: UUID, entity_id: UUID
    ) -> None:
        """自动分配：创建者自动获得新实体的边界权限。"""
        await db.execute(
            """INSERT INTO user_entity_assignments (user_id, entity_id, assigned_by)
               VALUES ($1, $2, $1)
               ON CONFLICT (user_id, entity_id) DO NOTHING""",
            user_id, entity_id
        )
        await self.invalidate_user_cache(user_id)

    # ========== 默认权限生成 ==========

    async def create_default_permissions(
        self, context_id: UUID, sensitivity: str = "internal",
        creator_id: Optional[UUID] = None
    ) -> dict:
        """为新创建的上下文生成默认权限记录。"""
        allowed_roles_map = {
            "top_secret":    ["admin", "partner"],
            "confidential":  ["admin", "partner", "senior_consultant", "consultant"],
            "internal":      ["admin", "partner", "senior_consultant", "consultant"],
            "public":        ["admin", "partner", "senior_consultant", "consultant"],
        }
        allowed_roles = allowed_roles_map.get(sensitivity, allowed_roles_map["internal"])

        allowed_entities = []
        if creator_id:
            allowed_entities = await self.get_user_entities(creator_id)

        await db.execute(
            """INSERT INTO permissions (context_id, visibility, allowed_roles, allowed_entities)
               VALUES ($1, $2, $3, $4)""",
            context_id, sensitivity, allowed_roles, allowed_entities
        )
        return {
            "context_id": context_id,
            "visibility": sensitivity,
            "allowed_roles": allowed_roles,
            "allowed_entities": allowed_entities,
        }

    # ========== Agent MCP Tool层拦截 ==========

    async def agent_mcp_check_before_write(
        self, context_id: UUID, action: Action
    ) -> AccessResult:
        """Agent写入前检查（在MCP Tool调用前执行）。

        禁止规则:
        - 禁止修改 L4/L5 上下文
        - 禁止覆盖人工裁决结果（lifecycle_status=resolved 且裁决方式=manual）
        - 仅允许写入 L2/L3 级别
        """
        context = await self._get_context_with_permissions(context_id)

        # 检查1: 禁止修改高可信度上下文
        if context["confidence_level"] in ("L4", "L5"):
            return AccessResult(
                allowed=False,
                reason=f"agent_cannot_modify_{context['confidence_level']}",
                denied_layer=3
            )

        # 检查2: 禁止覆盖人工裁决
        if context.get("resolution_type") == "manual":
            return AccessResult(
                allowed=False,
                reason="agent_cannot_override_manual_resolution",
                denied_layer=3
            )

        # 检查3: 仅允许写入 L2/L3
        if context["confidence_level"] not in ("L2", "L3"):
            return AccessResult(
                allowed=False,
                reason="agent_write_limited_to_l2_l3",
                denied_layer=3
            )

        return AccessResult(allowed=True, reason="agent_write_allowed")

    async def agent_mcp_check_before_send(
        self, context_id: UUID, target: str
    ) -> AccessResult:
        """Agent对外发送前检查（在MCP Tool调用前执行）。

        target 取值: 'feishu_group', 'external_api', 'internal_api', 'web_ui'
        禁止规则: confidential/top_secret 内容禁止发送到 feishu_group/external_api
        """
        if target in ("internal_api", "web_ui"):
            return AccessResult(allowed=True, reason="internal_target_allowed")

        context = await self._get_context_with_permissions(context_id)

        if context["sensitivity"] in (Visibility.CONFIDENTIAL, Visibility.TOP_SECRET):
            return AccessResult(
                allowed=False,
                reason=f"cannot_send_{context['sensitivity']}_to_{target}"
            )

        return AccessResult(allowed=True, reason="send_allowed")

    # ========== 缓存管理 ==========

    def _build_cache_key(self, user_id: UUID, context_id: UUID, action: Action) -> str:
        raw = f"perm:{user_id}:{context_id}:{action.value}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]

    async def _cache_get(self, key: str):
        if self._redis:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
        else:
            entry = self._local_cache.get(key)
            if entry:
                result, expires = entry
                if time.time() < expires:
                    return result
                del self._local_cache[key]
        return None

    async def _cache_set(self, key: str, value, ttl: int = None):
        ttl = ttl or self.CACHE_TTL_SECONDS
        if self._redis:
            await self._redis.setex(key, ttl, json.dumps(value))
        else:
            self._local_cache[key] = (value, time.time() + ttl)
            if len(self._local_cache) > self.CACHE_MAX_ENTRIES:
                oldest = min(self._local_cache, key=lambda k: self._local_cache[k][1])
                del self._local_cache[oldest]

    async def invalidate_user_cache(self, user_id: UUID):
        """清除指定用户的所有权限缓存。"""
        prefix = f"perm:{user_id}:"
        if self._redis:
            keys = await self._redis.keys(f"{prefix}*")
            if keys:
                await self._redis.delete(*keys)
        else:
            to_delete = [k for k in self._local_cache if k.startswith(prefix)]
            for k in to_delete:
                del self._local_cache[k]

    # ========== 数据库查询辅助 ==========

    async def _get_user_with_role(self, user_id: UUID) -> dict:
        row = await db.fetch_one(
            """SELECT u.id, u.role, u.partner_scope
               FROM users u WHERE u.id = $1""",
            user_id
        )
        if not row:
            raise ValueError(f"User {user_id} not found")
        return dict(row)

    async def _get_context_with_permissions(self, context_id: UUID) -> dict:
        row = await db.fetch_one(
            """SELECT c.id, c.confidence_level, c.lifecycle_status,
                      p.visibility AS sensitivity, p.allowed_roles,
                      c.resolution_type
               FROM context_items c
               JOIN permissions p ON c.id = p.context_id
               WHERE c.id = $1""",
            context_id
        )
        if not row:
            raise ValueError(f"Context {context_id} not found")
        return dict(row)

    async def _get_context_entity_ids(self, context_id: UUID) -> List[UUID]:
        rows = await db.fetch_all(
            "SELECT entity_id FROM context_entities_map WHERE context_id = $1",
            context_id
        )
        return [r["entity_id"] for r in rows]
```

### 7.3 可信度引擎（ConfidenceService 接口规范）

`confidence_service.py` 是自研核心组件，实现 §3.4 定义的全部可信度算法。以下接口定义可直接用于生成代码。

#### 7.3.1 常量与枚举

```python
from enum import StrEnum
from dataclasses import dataclass
from typing import Tuple, Optional
from datetime import datetime, date

class ConfidenceLevel(StrEnum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"

class ConfidenceSourceType(StrEnum):
    CONTRACT = "contract"
    OFFICIAL_DOC = "official_doc"
    EXPERT_VERIFIED = "expert_verified"
    FINANCIAL_REPORT = "financial_report"
    MEETING_MINUTES = "meeting_minutes"
    EMAIL = "email"
    PROJECT_KB = "project_kb"
    AI_EXTRACT_VERIFIED = "ai_extract_verified"
    MANUAL_ENTRY = "manual_entry"
    MEMORY_MD = "memory_md"
    AI_EXTRACT = "ai_extract"
    WEB_SCRAPE = "web_scrape"
    VERBAL = "verbal"
    UNKNOWN = "unknown"
    COMPETITOR_RUMOR = "competitor_rumor"

@dataclass
class ConfidenceResult:
    level: ConfidenceLevel
    score: float
    source_type: ConfidenceSourceType
    corroboration_count: int
    last_updated: datetime
    decay_applied: bool
    reason: str
```

#### 7.3.2 初始置信度映射

```python
INITIAL_CONFIDENCE_MAP: dict[ConfidenceSourceType, Tuple[ConfidenceLevel, float]] = {
    ConfidenceSourceType.CONTRACT:            (ConfidenceLevel.L5, 0.98),
    ConfidenceSourceType.OFFICIAL_DOC:        (ConfidenceLevel.L5, 0.97),
    ConfidenceSourceType.EXPERT_VERIFIED:     (ConfidenceLevel.L4, 0.93),
    ConfidenceSourceType.FINANCIAL_REPORT:    (ConfidenceLevel.L4, 0.92),
    ConfidenceSourceType.MEETING_MINUTES:     (ConfidenceLevel.L4, 0.90),
    ConfidenceSourceType.EMAIL:               (ConfidenceLevel.L4, 0.88),
    ConfidenceSourceType.PROJECT_KB:          (ConfidenceLevel.L3, 0.78),
    ConfidenceSourceType.AI_EXTRACT_VERIFIED: (ConfidenceLevel.L3, 0.78),
    ConfidenceSourceType.MANUAL_ENTRY:        (ConfidenceLevel.L3, 0.75),
    ConfidenceSourceType.MEMORY_MD:           (ConfidenceLevel.L2, 0.65),
    ConfidenceSourceType.AI_EXTRACT:          (ConfidenceLevel.L2, 0.60),
    ConfidenceSourceType.WEB_SCRAPE:          (ConfidenceLevel.L2, 0.55),
    ConfidenceSourceType.VERBAL:              (ConfidenceLevel.L1, 0.40),
    ConfidenceSourceType.UNKNOWN:             (ConfidenceLevel.L1, 0.40),
    ConfidenceSourceType.COMPETITOR_RUMOR:    (ConfidenceLevel.L1, 0.35),
}
```

#### 7.3.3 ConfidenceService 类定义

```python
class ConfidenceService:
    """可信度引擎。纯计算服务，不直接操作数据库（由调用方负责写库）。"""

    DECAY_START_MONTHS: int = 6
    DECAY_RATE_PER_MONTH: float = 0.03
    MIN_SCORE_AFTER_DECAY: float = 0.20
    CORROBORATION_WEIGHT_CAP: float = 0.15
    MAX_CORROBORATION_BOOST: float = 0.45
    CONFLICT_PENALTY: float = 0.10
    SEMANTIC_SIMILARITY_THRESHOLD: float = 0.85

    # ========== 核心算法 ==========

    @staticmethod
    def get_initial_confidence(
        source_type: ConfidenceSourceType
    ) -> Tuple[ConfidenceLevel, float]:
        """根据来源类型返回初始可信度等级和分数。

        Args:
            source_type: 来源类型枚举值

        Returns:
            (level, score)

        Raises:
            KeyError: 未知来源类型（应通过 UNKNOWN 兜底）
        """
        return INITIAL_CONFIDENCE_MAP.get(
            source_type,
            (ConfidenceLevel.L1, 0.40)  # unknown fallback
        )

    @staticmethod
    def calculate_corroboration_boost(
        existing_score: float,
        new_source_score: float,
        existing_corroboration_count: int,
        new_source_type: ConfidenceSourceType,
        existing_source_types: list[ConfidenceSourceType]
    ) -> Tuple[float, str]:
        """多源印证：计算新来源对已有条目置信度的提升值。

        Args:
            existing_score: A的当前分数
            new_source_score: B的来源初始分数
            existing_corroboration_count: A的当前印证次数
            new_source_type: B的来源类型
            existing_source_types: A的所有已有印证来源类型列表

        Returns:
            (new_total_score, reason_description)

        Rules:
        - 印证权重上限 0.15
        - 总提权上限 0.45
        - 同类型来源第3次及以后 weight 减半
        """
        # 计算基础印证权重
        base_weight = min(
            ConfidenceService.CORROBORATION_WEIGHT_CAP,
            max(0, (new_source_score - 0.5) * 0.3)
        )

        # 同类型来源递减
        same_type_count = sum(
            1 for t in existing_source_types if t == new_source_type
        )
        if same_type_count >= 2:
            base_weight *= 0.5

        # 计算总提权上限
        current_boost = existing_score - ConfidenceService._get_initial_score_of_level(
            ConfidenceService.resolve_level(existing_score)
        )
        remaining_boost = ConfidenceService.MAX_CORROBORATION_BOOST - current_boost
        effective_weight = min(base_weight, max(0, remaining_boost))

        if effective_weight <= 0:
            return (existing_score, f"corroboration_capped: boost={effective_weight:.3f}")

        new_score = existing_score + (1.0 - existing_score) * effective_weight
        new_score = min(new_score, 1.0)
        return (new_score, f"corroboration: +{new_score - existing_score:.3f} (weight={effective_weight:.3f})")

    @staticmethod
    def apply_time_decay(
        score: float,
        last_updated: datetime,
        current_time: Optional[datetime] = None
    ) -> Tuple[float, bool, str]:
        """时效衰减：计算衰减后的有效分数。

        Args:
            score: 原始分数
            last_updated: 最后更新时间
            current_time: 当前时间（None则用now()）

        Returns:
            (effective_score, decay_applied, reason)
        """
        now = current_time or datetime.utcnow()
        months_since = (now - last_updated).days / 30.0

        if months_since <= ConfidenceService.DECAY_START_MONTHS:
            return (score, False, f"no_decay: {months_since:.1f} months since update")

        decay_months = months_since - ConfidenceService.DECAY_START_MONTHS
        decay_amount = ConfidenceService.DECAY_RATE_PER_MONTH * decay_months
        effective = max(
            score - decay_amount,
            ConfidenceService.MIN_SCORE_AFTER_DECAY
        )
        return (round(effective, 4), True, f"decay: -{decay_amount:.3f} over {decay_months:.1f} months")

    @staticmethod
    def resolve_level(score: float) -> ConfidenceLevel:
        """根据分数确定可信度等级。纯函数，无IO。"""
        if score >= 0.95: return ConfidenceLevel.L5
        if score >= 0.85: return ConfidenceLevel.L4
        if score >= 0.70: return ConfidenceLevel.L3
        if score >= 0.50: return ConfidenceLevel.L2
        if score >= 0.30: return ConfidenceLevel.L1
        return ConfidenceLevel.L0

    @staticmethod
    def level_to_median(level: ConfidenceLevel) -> float:
        """等级→分数中值（用于展示和等级比较）。"""
        return {
            ConfidenceLevel.L5: 0.975,
            ConfidenceLevel.L4: 0.90,
            ConfidenceLevel.L3: 0.775,
            ConfidenceLevel.L2: 0.60,
            ConfidenceLevel.L1: 0.40,
            ConfidenceLevel.L0: 0.15,
        }[level]

    @staticmethod
    def apply_conflict_penalty(score: float) -> Tuple[float, str]:
        """矛盾惩罚：标记矛盾时降低分数。"""
        penalized = max(score - ConfidenceService.CONFLICT_PENALTY, 0.10)
        return (penalized, f"conflict_penalty: {score:.3f} → {penalized:.3f}")

    @staticmethod
    def calculate_manual_review_result(
        current_score: float,
        decision: str,  # "approve" | "reject" | "downgrade" | "upgrade"
        reviewer_role: str,
        target_level: Optional[str] = None
    ) -> Tuple[ConfidenceLevel, float, str]:
        """人工审核结果计算。

        Args:
            current_score: 当前分数
            decision: approve/reject/downgrade/upgrade
            reviewer_role: 审核人角色（admin/partner/senior_consultant）
            target_level: upgrade/downgrade的目标等级（可选）

        Returns:
            (new_level, new_score, reason)
        """
        if decision == "approve":
            # L2→L3: score设为0.78
            new_score = 0.78
            return (ConfidenceLevel.L3, new_score, "manual_approve: L2→L3")

        elif decision == "reject":
            return (
                ConfidenceService.resolve_level(current_score),
                current_score,
                "manual_reject: preserved current score"
            )

        elif decision == "upgrade" and target_level:
            # admin 手动提升到指定等级
            new_score = ConfidenceService.level_to_median(ConfidenceLevel(target_level))
            return (
                ConfidenceLevel(target_level),
                new_score,
                f"manual_upgrade: → {target_level}"
            )

        elif decision == "downgrade" and target_level:
            new_score = ConfidenceService.level_to_median(ConfidenceLevel(target_level))
            return (
                ConfidenceLevel(target_level),
                new_score,
                f"manual_downgrade: → {target_level}"
            )

        else:
            raise ValueError(f"Unknown decision: {decision}")

    @staticmethod
    def can_agent_reference(level: ConfidenceLevel) -> Tuple[bool, str]:
        """Agent引用决策。纯函数。"""
        rules = {
            ConfidenceLevel.L5: (True, "自由引用，建议保留原始出处链接"),
            ConfidenceLevel.L4: (True, "引用时请标注来源"),
            ConfidenceLevel.L3: (True, "引用时请提示此信息来源于AI提取，建议人工复核"),
            ConfidenceLevel.L2: (False, "此信息尚未经人工审核，不可直接引用"),
            ConfidenceLevel.L1: (False, "信息可信度较低，仅作参考"),
            ConfidenceLevel.L0: (False, "信息已过期或存在矛盾，不可引用"),
        }
        return rules.get(level, (False, "未知可信度等级"))

    # ========== 辅助方法 ==========

    @staticmethod
    def _get_initial_score_of_level(level: ConfidenceLevel) -> float:
        """获取某等级的最低分数阈值（用于核对印证上限）。"""
        thresholds = {
            ConfidenceLevel.L5: 0.95, ConfidenceLevel.L4: 0.85,
            ConfidenceLevel.L3: 0.70, ConfidenceLevel.L2: 0.50,
            ConfidenceLevel.L1: 0.30, ConfidenceLevel.L0: 0.00,
        }
        return thresholds[level]

    @staticmethod
    def get_level_thresholds() -> dict[str, Tuple[float, float]]:
        """返回所有等级的分数区间，供前端展示。"""
        return {
            "L5": (0.95, 1.00), "L4": (0.85, 0.95),
            "L3": (0.70, 0.85), "L2": (0.50, 0.70),
            "L1": (0.30, 0.50), "L0": (0.00, 0.30),
        }

    @staticmethod
    def validate_score(score: float) -> bool:
        """验证分数是否在有效范围 [0.0, 1.0]。"""
        return 0.0 <= score <= 1.0
```

---

### 7.4 配置管理服务（ConfigService 接口规范）

`config_service.py` 统一管理三层配置（系统配置/用户设置/环境变量），提供缓存、热生效和变更广播能力。详见《配置管理详细设计》(08_configuration_management.md)。

```python
class ConfigService:
    """配置服务单例。通过 FastAPI 依赖注入使用。"""

    def __init__(self, redis_client=None, ws_manager=None):
        self._redis = redis_client
        self._ws_manager = ws_manager
        self._system_cache: dict[str, Any] = {}
        self._user_cache: dict[str, dict] = {}
        self._cache_timestamp: float = 0.0
        self._cache_ttl: float = 60.0  # 缓存过期时间（秒）

    # -------- 系统配置 --------
    async def get_system_config(self, section: str) -> dict:
        """获取指定分组的系统配置。缓存未命中时从DB读取。"""

    async def get_system_value(self, section: str, key: str, default: Any = None) -> Any:
        """获取单个系统配置值。供各Service在运行时读取。"""

    async def get_all_system_configs(self) -> dict[str, list]:
        """获取全部系统配置（管理端配置页面用）。"""

    async def update_system_config(self, section: str, key: str, value: Any, changed_by: str, reason: str) -> None:
        """更新单个系统配置项。写DB → 清缓存 → 记录日志 → WebSocket广播。"""

    async def batch_update_system_config(self, section: str, updates: dict, changed_by: str, reason: str) -> None:
        """批量更新某分组的配置项。"""

    async def reset_section_to_default(self, section: str, changed_by: str) -> None:
        """将指定分组恢复为默认值。"""

    async def reset_all_to_default(self, changed_by: str) -> None:
        """将所有配置恢复为默认值（危险操作）。"""

    # -------- 用户设置 --------
    async def get_user_settings(self, user_id: UUID) -> dict:
        """获取用户全部设置（按section聚合返回）。"""

    async def get_user_settings_section(self, user_id: UUID, section: str) -> dict:
        """获取用户指定分组的设置。"""

    async def update_user_settings(self, user_id: UUID, section: str, settings: dict) -> None:
        """批量更新用户指定分组的设置。"""

    async def get_user_setting_value(self, user_id: UUID, section: str, key: str, default: Any = None) -> Any:
        """获取用户单个设置值。供各Service在运行时读取。"""

    # -------- 环境变量 --------
    @staticmethod
    def get_env(key: str, default: Any = None) -> str:
        """读取环境变量（只读）。优先级: os.environ > .env文件。"""

    @staticmethod
    def list_env_vars() -> list[dict]:
        """返回所有已知环境变量的元数据列表（供管理端展示）。"""

    # -------- 缓存管理 --------
    async def _refresh_system_cache(self) -> None:
        """从DB全量刷新系统配置缓存。"""

    async def invalidate_system_cache(self, section: str = None):
        """使系统配置缓存失效。section=None时清空全部。"""

    async def invalidate_user_cache(self, user_id: UUID):
        """使指定用户的设置缓存失效。"""

    # -------- 变更广播 --------
    async def _broadcast_config_change(self, section: str, changed_by: str, changes: list):
        """通过WebSocket向管理端广播配置变更事件。"""

    # -------- 默认值初始化 --------
    async def ensure_defaults_initialized(self) -> None:
        """系统启动时检查并初始化缺失的默认配置项。"""
```

---

## 8. 待决策问题

1. **[已决策] 生产部署方案**：已确定 Phase 1-2 用 IP+端口，Phase 3 前配置域名+Nginx+证书。

2. **[待决策] API版本策略**：URL版本（/api/v1/）vs Header版本？推荐：URL版本，简单直观。

3. **[待决策] 日志与监控**：自建ELK vs 使用云服务日志？推荐：初期用Docker logs + Grafana Loki。
