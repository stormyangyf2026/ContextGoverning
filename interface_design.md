[09_interface_design.md](https://github.com/user-attachments/files/29242152/09_interface_design.md)
# 统一上下文管理中心 — 组件化接口设计 v1.0

> 设计阶段：生产级详细设计 | 用途：使本产品可作为组件/插件嵌入到更大的本体产品中


---

## 1. 设计原则与目标

### 1.1 核心目标

使统一上下文管理中心（以下简称「本产品」或「Context Platform」）能够作为独立的、可嵌入的组件，接入任何本体产品（以下简称「父产品」或「Host Application」），成为父产品的上下文管理基础设施。

### 1.2 设计原则

**零侵入原则**：本产品不修改父产品的代码、数据库或认证体系。所有集成通过标准协议完成。

**自包含原则**：本产品可独立运行（standalone模式），也可嵌入运行（embedded模式）。两种模式下核心功能完全一致。

**协议先行原则**：所有外部接口通过明确的协议定义（OpenAPI 3.1、JSON Schema、gRPC proto），父产品无需关心本产品内部实现。

**渐进集成原则**：提供多级集成深度——从最轻量的 API 调用，到 UI 嵌入，到深度数据融合——父产品可按需选择。

**安全隔离原则**：当多个父产品或多个租户共享同一部署实例时，数据严格隔离，权限独立管理。

**可观测原则**：所有外部调用均有审计日志、性能指标和健康检查端点。

**界面友好原则**：所有用户操作界面（管理端配置页、工作区创建、认证配置、Webhook 配置等）均不允许要求用户直接输入 JSON、正则表达式、数学公式或程序化表达式。如需配置结构化数据，一律通过表单控件（文本输入框、下拉框、勾选框、数字输入框、颜色选择器、搜索选择器、键值对逐行添加等）将结构化数据拆解为信息/数据录入 + 系统自动组装的方式实现。

### 1.3 集成模式概览

父产品可通过以下四种模式之一集成 Context Platform：

| 模式 | 集成深度 | 适用场景 | 所需工作量 |
|------|---------|---------|-----------|
| **API模式** | 仅调用 REST API | 父产品有自己的 UI，只需要上下文数据和检索能力 | 低 |
| **事件驱动模式** | API + Webhook/WebSocket | 父产品需要实时接收上下文变更事件 | 中 |
| **嵌入UI模式** | API + iframe/Web Component 嵌入前端 | 父产品希望直接使用本产品的管理/搜索界面 | 中 |
| **全集成模式** | 以上全部 + SDK + 深度数据融合 | 父产品将上下文作为核心基础设施，深度定制 | 高 |

---

## 2. 接口架构总览

### 2.1 接口分层

```
┌──────────────────────────────────────────────────────────────────────┐
│                        父产品 (Host Application)                       │
│                                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │ 父产品UI  │  │ 父产品后端│  │ 父产品网关│  │ 父产品事件总线   │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │
│       │             │             │                   │              │
└───────┼─────────────┼─────────────┼───────────────────┼──────────────┘
        │             │             │                   │
        │  (iframe/   │  (REST/gRPC │  (Auth Token      │  (Webhook
        │   WebComp)  │   SDK调用)  │   Passthrough)    │   Event)
        │             │             │                   │
┌───────┼─────────────┼─────────────┼───────────────────┼──────────────┐
│       ▼             ▼             ▼                   ▼              │
│                     Context Platform 组件边界                        │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    集成适配层 (Integration Adapter Layer)      │  │
│  │                                                                │  │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────┐ │  │
│  │  │ Auth       │  │ Tenant     │  │ Webhook    │  │ UI      │ │  │
│  │  │ Adapter    │  │ Resolver   │  │ Emitter    │  │ Adapter │ │  │
│  │  │            │  │            │  │            │  │         │ │  │
│  │  │ JWT委托    │  │ tenant_id  │  │ 事件序列化 │  │ iframe  │ │  │
│  │  │ API Key    │  │ 解析       │  │ 重试/退避  │  │ SDK     │ │  │
│  │  │ OAuth2     │  │ 数据隔离   │  │ 签名验证   │  │ WebComp │ │  │
│  │  │ 自定义Header│  │ 配额管理    │  │ 批量发送   │  │ 主题适配 │ │  │
│  │  └────────────┘  └────────────┘  └────────────┘  └─────────┘ │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                               │                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    核心业务层（不变）                           │  │
│  │  Context | Ingestion | Search | Confidence | Permission | ...  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                               │                                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    数据存储层（不变）                           │  │
│  │  PostgreSQL + pgvector + LightRAG + Mem0                      │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

### 2.2 关键概念

**App Instance**：一次部署 = 一个 App Instance，拥有唯一的 `app_instance_id`。一个 App Instance 可以服务一个父产品（dedicated mode）或多个父产品（multi-tenant mode）。

**Workspace（租户/工作区）**：在多租户模式下，每个父产品拥有一个独立的 Workspace，由 `workspace_id` 标识。Workspace 之间的数据完全隔离。

**Integration Profile**：描述本产品如何与父产品集成的配置集合，包含认证方式、事件回调 URL、UI 嵌入参数等。

### 2.3 运行模式

```python
# backend/app/core/runtime_mode.py

from enum import StrEnum

class RuntimeMode(StrEnum):
    STANDALONE = "standalone"    # 独立运行：使用内置认证、内置UI
    EMBEDDED = "embedded"        # 嵌入运行：使用外部认证、可嵌入UI

class TenantMode(StrEnum):
    SINGLE = "single"            # 单租户：一个 App Instance 服务一个父产品
    MULTI = "multi"              # 多租户：一个 App Instance 服务多个父产品

# 运行模式由环境变量 RUNTIME_MODE 和 TENANT_MODE 控制
# 开发环境默认: RUNTIME_MODE=standalone, TENANT_MODE=single
# 嵌入部署时: RUNTIME_MODE=embedded, TENANT_MODE=multi
```

---

## 3. 外部 API (Inbound) — 父产品调用本产品

### 3.1 外部 API 端点总览

所有外部 API 路径以 `/api/v1/external/` 为前缀，与内部 API 物理同服务但逻辑分离，通过独立的中间件链处理。

| 分组 | 说明 | 端点数量 |
|------|------|---------|
| 认证 | Token 校验、身份委托 | 3 |
| 工作区管理 | 租户 CRUD（多租户模式） | 5 |
| 上下文管理 | 上下文 CRUD（外部视角） | 6 |
| 搜索检索 | 混合搜索（外部视角） | 2 |
| 实体管理 | 实体 CRUD | 4 |
| 图谱查询 | 实体关系查询 | 2 |
| 推送通知 | 向父产品推送上下文变更 | 1（父产品注册 webhook） |
| 配置管理 | 组件级配置读写 | 3 |
| 健康检查 | 可用性和性能指标 | 2 |

### 3.2 外部 API 详细设计

#### 3.2.1 通用约定

**认证方式**：所有外部 API 请求必须携带认证凭证，支持以下三种方式之一：

```http
# 方式1: API Key（推荐简单集成）
Authorization: Bearer cpk_live_xxxxxxxxxxxxxxxxxxxx

# 方式2: JWT Token（父产品签发，本产品验证）
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...

# 方式3: 自定义 Token（通过Header传递，本产品回调父产品验证）
X-Context-Platform-Token: <token>
X-Context-Platform-Tenant: <workspace_id>  # 多租户模式必须
```

**多租户 Header**（多租户模式必须）：

```http
X-CP-Workspace-Id: ws_xxxxxxxxxxxx
```

**请求/响应格式**：沿用内部 API 的统一包装格式：

```json
{
  "data": { ... },
  "meta": { "total": 100, "page": 1, "page_size": 20 },
  "error": null
}
```

**幂等性**：`POST` / `PUT` 请求支持幂等键（可选）：

```http
Idempotency-Key: ik_xxxxxxxxxxxx
```

#### 3.2.2 认证与身份委托

本产品支持三种认证集成模式，父产品按需选择：

**模式 A：API Key 认证（最简单）**

父产品在管理控制台生成 API Key，所有请求携带此 Key。本产品将 API Key 映射到预配置的角色和权限范围。

```json
// POST /api/v1/external/auth/verify-api-key
// 请求（本产品内部验证，父产品调用时直接使用）
// 父产品只需要在请求中携带 API Key 即可

// GET /api/v1/external/auth/whoami
// 响应
{
  "data": {
    "workspace_id": "ws_abc123",
    "role": "admin",
    "permissions": ["context:read", "context:write", "search:execute"],
    "entity_scope": ["customer:利欧泵业", "customer:YY科技"],
    "expires_at": "2027-06-23T00:00:00Z"
  }
}
```

**API Key 管理端点**：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/external/auth/api-keys` | 创建 API Key |
| GET | `/api/v1/external/auth/api-keys` | 列出所有 API Key |
| DELETE | `/api/v1/external/auth/api-keys/{id}` | 撤销 API Key |

```json
// POST /api/v1/external/auth/api-keys 请求
{
  "name": "production-integration",
  "role": "admin",
  "entity_scope": ["customer:*", "project:*"],  // * 表示全部
  "expires_in_days": 365,
  "allowed_ips": ["10.0.0.0/8"]  // 可选，IP白名单
}

// 响应
{
  "data": {
    "id": "apk_abc123",
    "key": "cpk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  // 仅创建时返回
    "name": "production-integration",
    "created_at": "2026-06-23T12:00:00Z",
    "expires_at": "2027-06-23T12:00:00Z"
  }
}
```

**模式 B：JWT 委托认证**

父产品签发 JWT Token，本产品验证 Token 的签名和有效性。父产品需向本产品注册其 JWKS（JSON Web Key Set）端点。

**界面友好原则**：管理员不需要手写任何 JSON 或程序化表达式。所有配置通过表单控件完成，系统自动组装为 API 请求数据。

**JWT 配置管理界面**（管理端 `/admin/integration/jwt` 页面）：

```
┌─ JWT 委托认证配置 ─────────────────────────────────────────────────┐
│                                                                     │
│ 基本连接信息（文本输入框）                                            │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 签发者 (issuer)     [https://parent-product.example.com    ] │   │
│ │ JWKS 地址           [https://parent-product.example.com/   ] │   │
│ │                     .well-known/jwks.json                   ] │   │
│ │ 受众 (audience)      [context-platform                    ] │   │
│ │ Token 刷新地址       [https://parent-product.example.com/   ] │   │
│ │ (选填)               oauth/token                          ] │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 声明映射 — 将 JWT 中的字段映射到本系统的用户属性（下拉框选择）        │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 标准声明映射:                                                  │   │
│ │ JWT 声明                         映射为 本系统字段             │   │
│ │ ┌─────────────────────────┐     ┌────────────────────────┐   │   │
│ │ │ sub                   ▾ │  →  │ 用户标识 (user_id)   ▾ │   │   │
│ │ │ ─────────────────────── │     │ ────────────────────── │   │   │
│ │ │ sub  (JWT主题)          │     │ 用户标识  (user_id)     │   │   │
│ │ │ email                   │     │ 邮箱      (email)       │   │   │
│ │ │ preferred_username      │     │ 用户名    (username)    │   │   │
│ │ └─────────────────────────┘     └────────────────────────┘   │   │
│ │                                                               │   │
│ │ 自定义声明映射（点击 [+ 添加一行] 按钮逐行添加）:               │   │
│ │ ┌─────────────────────────┬───────────────────────────────┐  │   │
│ │ │ 1. JWT字段 [custom:tenant▾] → 本系统字段 [workspace_id▾]│  │   │
│ │ │                                   [✕ 删除]               │  │   │
│ │ │ 2. JWT字段 [custom:role  ▾] → 本系统字段 [role        ▾]│  │   │
│ │ │                                   [✕ 删除]               │  │   │
│ │ └─────────────────────────┴───────────────────────────────┘  │   │
│ │                                            [+ 添加自定义映射] │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 默认角色（当 JWT 中没有角色声明时使用，下拉框选择）                    │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 默认角色: [consultant ▾]                                      │   │
│ │ → 可选: admin / partner / senior_consultant / consultant      │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                                              [测试连接] [保存配置]   │
└─────────────────────────────────────────────────────────────────────┘
```

**API 接口**（前端自动组装请求体，用户无需关心）：

```json
// PUT /api/v1/external/auth/jwt-config 请求（前端自动生成）
{
  "issuer": "https://parent-product.example.com",
  "jwks_url": "https://parent-product.example.com/.well-known/jwks.json",
  "audience": "context-platform",
  "claim_mapping": {
    "sub": "user_id",
    "custom:tenant": "workspace_id",
    "custom:role": "role"
  },
  "default_role": "consultant",
  "token_refresh_url": "https://parent-product.example.com/oauth/token"
}

// 响应
{
  "data": {
    "jwt_config_id": "jwt_abc123",
    "status": "active",
    "last_verified_at": "2026-06-23T12:00:00Z"
  }
}
```

**说明**：
- JWT 标准声明（sub / email / preferred_username）通过**下拉框选择**映射目标字段，不需要输入任何程序化表达式
- 自定义声明通过 **「+ 添加一行」按钮** 逐行添加，每行输入 JWT 字段名（文本框）+ 选择目标字段（下拉框），系统自动组装 `claim_mapping`
- 「测试连接」按钮发送验证请求，确认 JWKS 可访问且签名有效
- `token_refresh_url` 可选，父产品提供时本产品可代理刷新 Token

**模式 C：自定义 Token 回调验证**

父产品使用自定义 Token 格式，本产品将 Token 发送到父产品的验证端点进行验证。

**界面友好原则**：管理员不需要手写 JSON 模板或 JSONPath 表达式。请求参数通过勾选和键值对录入，响应字段通过下拉框逐字段映射，系统自动生成 `request_template` 和 `response_mapping`。

**自定义 Token 配置管理界面**（管理端 `/admin/integration/custom-token` 页面）：

```
┌─ 自定义 Token 回调验证配置 ─────────────────────────────────────────┐
│                                                                     │
│ 回调基本信息（文本输入框）                                            │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 验证端点 URL        [https://parent-product.example.com/ap ] │   │
│ │                     i/verify-token                         ] │   │
│ │ 请求方法             [POST ▾]   (GET / POST)                 │   │
│ │ 缓存有效期（秒）      [300      ]  (建议 60-3600)             │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 请求 Headers（点击 [+ 添加 Header] 逐行添加）                        │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ Header 名称                        Header 值                  │   │
│ │ ┌──────────────────────────────┐ ┌────────────────────────┐  │   │
│ │ │ X-Internal-Secret            │ │ shared-secret-xxx      │  │   │
│ │ └──────────────────────────────┘ └────────────────────────┘  │   │
│ │                                                   [✕ 删除]   │   │
│ │                                        [+ 添加 Header]       │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 请求参数（勾选需要发送给父产品的参数）                                │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 发送以下参数到验证端点（勾选即启用，系统自动组装为请求体）:      │   │
│ │ [✓] Token 值         → 参数名 [token       ]                │   │
│ │ [✓] 工作区 ID        → 参数名 [workspace_id]                │   │
│ │ [ ] 用户 IP 地址      → 参数名 [client_ip   ]               │   │
│ │ [ ] 请求 User-Agent  → 参数名 [user_agent  ]               │   │
│ │                                              [+ 添加自定义参数] │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 响应字段映射（将父产品返回的 JSON 字段映射到本系统属性）              │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 系统已自动识别父产品返回 JSON 中的字段路径，请选择映射关系:     │   │
│ │                                                               │   │
│ │ 用户标识            → 对应返回字段 [data.user_id     ▾]       │   │
│ │ 角色                → 对应返回字段 [data.role        ▾]       │   │
│ │ 权限列表             → 对应返回字段 [data.permissions ▾]       │   │
│ │ 实体边界（选填）     → 对应返回字段 [data.entity_boundaries▾]  │   │
│ │ 有效性标记（选填）    → 对应返回字段 [data.valid       ▾]       │   │
│ │                                                               │   │
│ │ 字段选择器说明：每个下拉框中列出的是从父产品示例返回 JSON 中     │   │
│ │ 自动提取的可用字段路径（点号分隔），如 data.user_id。            │   │
│ │                                  [从返回示例自动提取字段列表]   │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 父产品返回示例（JSON）— 粘贴一份父产品验证端点的实际返回示例          │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ {                                                             │   │
│ │   "data": {                                                   │   │
│ │     "user_id": "user_123",                                    │   │
│ │     "role": "senior_consultant",                              │   │
│ │     "permissions": ["context:read","context:write",...],      │   │
│ │     "entity_boundaries": ["ent_001","ent_002"],               │   │
│ │     "valid": true                                             │   │
│ │   }                                                           │   │
│ │ }                                                             │   │
│ │                                                               │   │
│ │ → 粘贴后系统自动解析 JSON 结构，在下拉框中列出所有字段路径       │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                                              [测试连接] [保存配置]   │
└─────────────────────────────────────────────────────────────────────┘
```

**API 接口**（前端自动组装请求体，用户无需关心）：

```json
// PUT /api/v1/external/auth/custom-config 请求（前端自动生成）
{
  "verification_url": "https://parent-product.example.com/api/verify-token",
  "verification_method": "POST",
  "verification_headers": {
    "X-Internal-Secret": "shared-secret-xxx"
  },
  "request_template": {
    "token": "{{token}}",
    "workspace_id": "{{workspace_id}}"
  },
  "response_mapping": {
    "user_id": "$.data.user_id",
    "role": "$.data.role",
    "permissions": "$.data.permissions"
  },
  "cache_ttl_seconds": 300
}
```

本产品将向 `verification_url` 发送如下请求：

```json
// POST https://parent-product.example.com/api/verify-token
{
  "token": "<从X-CP-Token header获取>",
  "workspace_id": "ws_abc123"
}

// 父产品应返回：
{
  "data": {
    "user_id": "user_123",
    "role": "senior_consultant",
    "permissions": ["context:read", "context:write", "search:execute"],
    "entity_boundaries": ["ent_001", "ent_002"],
    "valid": true
  }
}
```

**说明**：
- 请求参数通过**勾选框 + 参数名字段**录入，系统自动生成 `request_template`
- 响应字段映射通过**下拉框选择**（从粘贴的示例返回 JSON 自动提取字段路径），系统自动生成 `response_mapping` 和 JSONPath
- 用户只需粘贴一份父产品返回的 JSON 示例，系统自动解析出全部可用字段，无需手写 JSONPath
- 「测试连接」按钮发送验证请求，确认回调端点可达

#### 3.2.3 工作区管理（多租户模式）

仅在多租户模式下可用。管理不同的父产品/工作区。

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/v1/external/workspaces` | 创建新工作区 | system_admin |
| GET | `/api/v1/external/workspaces` | 列出所有工作区 | system_admin |
| GET | `/api/v1/external/workspaces/{id}` | 获取工作区详情 | system_admin + workspace_admin |
| PUT | `/api/v1/external/workspaces/{id}` | 更新工作区配置 | system_admin |
| DELETE | `/api/v1/external/workspaces/{id}` | 删除工作区（软删除） | system_admin |

**界面友好原则**：创建工作区时，管理员不需要手写任何嵌套 JSON。所有配置通过分组的表单控件完成（文本输入、勾选框、数字输入、下拉框、颜色选择器），系统自动组装为 API 请求数据。

**创建工作区管理界面**（管理端 `/admin/workspaces/create` 页面）：

```
┌─ 创建工作区 ───────────────────────────────────────────────────────┐
│                                                                     │
│ 基本信息                                                             │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 工作区名称    [父产品-A                                  ]   │   │
│ │ 唯一标识(slug) [parent-a                                  ]   │   │
│ │ 描述          [A产品的上下文管理                          ]   │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 认证方式                                                             │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 认证模式: (●) API Key  ( ) JWT 委托  ( ) 自定义 Token        │   │
│ │                                                               │   │
│ │ → 选择 API Key 模式：创建后自动生成初始 API Key（仅创建时显示）│   │
│ │ → 选择 JWT 委托 / 自定义 Token：需分别填写对应的认证配置表单   │   │
│ │   （配置表单见 §3.2.2 模式 B 和模式 C 的表单设计）             │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 功能开关（勾选启用）                                                  │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ [✓] 采集管道 (ingestion_enabled) — 启用各渠道上下文自动采集   │   │
│ │ [✓] 知识图谱 (graph_enabled) — 启用实体关系图谱构建和查询     │   │
│ │ [ ] Push 推送 (push_enabled) — 启用向父产品推送上下文变更事件 │   │
│ │ [✓] 数据导出 (export_enabled) — 启用 CSV/JSON/PDF 导出       │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 配额限制（数字输入框）                                                │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 上下文数量上限       [ 100000 ] 条                            │   │
│ │ 实体数量上限         [  10000 ] 个                            │   │
│ │ API 限流             [    500 ] 次/分钟                       │   │
│ │ 存储上限             [     50 ] GB                            │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ Webhook 事件回调（选填）                                              │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 回调 URL      [https://parent-product.example.com/hooks/co ] │   │
│ │               ntext-events                                  ] │   │
│ │ Webhook Secret [点击生成随机密钥  ]                           │   │
│ │ → 事件类型和过滤规则在创建后单独配置（见 §4.6 事件过滤管理界面）│   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ UI 嵌入外观（选填）                                                   │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 允许嵌入的域名 (allowed_origins)                              │   │
│ │ [https://parent-product.example.com               ] [✕ 删除] │   │
│ │                                             [+ 添加域名]      │   │
│ │                                                               │   │
│ │ 主题色 (primary_color)                                        │   │
│ │ [🎨 #2563EB]  (颜色选择器)                                    │   │
│ │                                                               │   │
│ │ Logo 图片 URL (logo_url)                                      │   │
│ │ [https://parent-product.example.com/logo.png            ]     │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                                         [取消]    [创建工作区]       │
└─────────────────────────────────────────────────────────────────────┘
```

**API 接口**（前端自动组装请求体，用户无需关心）：

```json
// POST /api/v1/external/workspaces 请求（前端自动生成）
{
  "name": "父产品-A",
  "slug": "parent-a",
  "description": "A产品的上下文管理",
  "auth_config": {
    "mode": "api_key",
    "jwt_config": {}
  },
  "features": {
    "ingestion_enabled": true,
    "graph_enabled": true,
    "push_enabled": false,
    "export_enabled": true
  },
  "quotas": {
    "max_contexts": 100000,
    "max_entities": 10000,
    "max_api_calls_per_minute": 500,
    "max_storage_gb": 50
  },
  "webhook_url": "https://parent-product.example.com/hooks/context-events",
  "webhook_secret": "whsec_xxxxxxxxxx",
  "ui_embedding": {
    "allowed_origins": ["https://parent-product.example.com"],
    "theme": {
      "primary_color": "#2563EB",
      "logo_url": "https://parent-product.example.com/logo.png"
    }
  }
}

// 响应
{
  "data": {
    "id": "ws_abc123",
    "name": "父产品-A",
    "slug": "parent-a",
    "api_key": "cpk_live_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",  // 初始API Key
    "created_at": "2026-06-23T12:00:00Z",
    "status": "active"
  }
}
```

#### 3.2.4 上下文管理（外部API）

与内部 `/api/v1/contexts` 功能一致，但通过外部认证中间件处理，返回结果已按工作区隔离。

| 方法 | 路径 | 说明 | 权限校验 |
|------|------|------|---------|
| GET | `/api/v1/external/contexts` | 列表查询（分页+筛选） | context:read |
| POST | `/api/v1/external/contexts` | 创建上下文 | context:write |
| GET | `/api/v1/external/contexts/{id}` | 获取上下文详情 | context:read |
| PUT | `/api/v1/external/contexts/{id}` | 更新上下文 | context:write |
| DELETE | `/api/v1/external/contexts/{id}` | 软删除上下文 | context:delete |
| POST | `/api/v1/external/contexts/batch` | 批量导入上下文 | context:write |

**请求示例**：

```json
// POST /api/v1/external/contexts 请求
{
  "title": "利欧泵业2026年Q2中东市场哥伦布项目进展",
  "content": "哥伦布项目Q2里程碑：已完成ERP系统选型（SAP S/4HANA），预计7月启动实施。关键风险：当地数据合规要求需要额外3个月准备时间。",
  "domain": "project",
  "sub_category": "milestone",
  "entities": [
    {"name": "利欧泵业", "type": "customer"},
    {"name": "哥伦布项目", "type": "project"}
  ],
  "confidence_source_type": "manual_entry",
  "confidence_level": "L3",
  "confidence_score": 0.75,
  "tags": ["里程碑", "Q2", "SAP"],
  "source_system": "parent_platform",
  "source_url": "https://parent-product.example.com/projects/columbus/updates/2026-q2",
  "idempotency_key": "ik_parent_2026_q2_update_001"
}

// 响应
{
  "data": {
    "id": "ctx_abc123",
    "context_id": "ctx_liou_pump_columbus_q2_2026",
    "title": "利欧泵业2026年Q2中东市场哥伦布项目进展",
    "lifecycle_status": "pending_review",
    "confidence_level": "L3",
    "confidence_score": 0.75,
    "created_at": "2026-06-23T12:00:00Z"
  }
}
```

```json
// GET /api/v1/external/contexts?domain=customer&confidence_min=L3&page=1&page_size=20&sort=updated_at:desc
// 响应
{
  "data": [
    {
      "id": "ctx_abc123",
      "title": "...",
      "content": "...",
      "domain": "customer",
      "confidence": { "level": "L4", "score": 0.92 },
      "entities": [
        {"id": "ent_001", "name": "利欧泵业", "type": "customer"}
      ],
      "lifecycle_status": "active",
      "updated_at": "2026-06-20T08:00:00Z"
    }
  ],
  "meta": { "total": 245, "page": 1, "page_size": 20 }
}
```

#### 3.2.5 搜索检索（外部API）

```json
// POST /api/v1/external/search 请求
{
  "query": "利欧泵业中东市场哥伦布项目进展",
  "mode": "hybrid",              // hybrid / exact / semantic / relation / timeline / contradiction
  "filters": {
    "domain": ["customer", "project"],
    "confidence_min": "L3",
    "date_from": "2026-01-01",
    "date_to": "2026-06-30",
    "status": ["active"],
    "entities": ["利欧泵业", "哥伦布项目"]
  },
  "page": 1,
  "page_size": 20,
  "include_relations": true,     // 是否附带关系图谱
  "include_confidence_detail": true  // 是否附带可信度溯源详情
}

// 响应
{
  "data": [
    {
      "id": "ctx_abc123",
      "title": "...",
      "content": "...",
      "score": 0.892,            // 综合匹配分数
      "score_breakdown": {
        "bm25": 0.85,
        "vector": 0.91,
        "graph": 0.90
      },
      "confidence": {
        "level": "L4",
        "score": 0.92,
        "can_agent_reference": true,
        "reference_hint": "引用时请标注来源"
      },
      "relations": [
        {
          "type": "depends_on",
          "target_title": "SAP S/4HANA选型决策",
          "target_id": "ctx_def456"
        }
      ]
    }
  ],
  "meta": { "total": 12, "page": 1, "page_size": 20, "query_time_ms": 234 }
}
```

#### 3.2.6 实体管理（外部API）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/external/entities` | 实体列表（分页+筛选） |
| POST | `/api/v1/external/entities` | 创建/更新实体（upsert） |
| GET | `/api/v1/external/entities/{id}` | 获取实体详情 |
| GET | `/api/v1/external/entities/{id}/graph` | 获取实体关联图谱 |

```json
// POST /api/v1/external/entities 请求（upsert模式）
{
  "name": "利欧泵业",
  "type": "customer",
  "domain": "customer",
  "aliases": ["利欧", "LEO"],
  "metadata": {
    "industry": "泵业制造",
    "annual_revenue_cny": "50亿",
    "employees": 5000,
    "region": "华东"
  },
  "upsert": true  // 名称+类型匹配时更新，不匹配时创建
}

// 响应
{
  "data": {
    "id": "ent_001",
    "name": "利欧泵业",
    "type": "customer",
    "operation": "updated",  // created / updated / unchanged
    "context_count": 47
  }
}
```

#### 3.2.7 图谱查询（外部API）

```json
// GET /api/v1/external/entities/{id}/graph?depth=2&relation_types=depends_on,drives,threatens
// 响应
{
  "data": {
    "center_entity": {"id": "ent_001", "name": "利欧泵业"},
    "nodes": [
      {"id": "ent_001", "name": "利欧泵业", "type": "customer"},
      {"id": "ent_002", "name": "哥伦布项目", "type": "project"},
      {"id": "ent_003", "name": "SAP S/4HANA", "type": "offering"}
    ],
    "edges": [
      {"source": "ent_002", "target": "ent_001", "type": "part_of", "label": "属于"},
      {"source": "ent_002", "target": "ent_003", "type": "depends_on", "label": "依赖"}
    ],
    "depth": 2
  }
}
```

#### 3.2.8 健康检查

```json
// GET /api/v1/external/health
// 响应
{
  "data": {
    "status": "healthy",           // healthy / degraded / unhealthy
    "version": "1.2.0",
    "runtime_mode": "embedded",
    "tenant_mode": "multi",
    "uptime_seconds": 86400,
    "components": {
      "database": {"status": "healthy", "latency_ms": 12},
      "vector_index": {"status": "healthy", "index_size": 15420},
      "graph_engine": {"status": "healthy", "node_count": 3847},
      "llm_service": {"status": "healthy", "latency_ms": 340},
      "redis": {"status": "healthy", "latency_ms": 3}
    }
  }
}

// GET /api/v1/external/health/metrics
// 响应：Prometheus 格式的性能指标
```

---

## 4. 事件系统 (Outbound) — 本产品通知父产品

### 4.1 事件通知模式

本产品通过两种方式向父产品推送事件：

| 方式 | 协议 | 实时性 | 可靠性 | 适用场景 |
|------|------|--------|--------|---------|
| Webhook | HTTPS POST | 近实时（<5秒） | at-least-once（含重试） | 上下文创建/更新/状态变更等业务事件 |
| WebSocket | WSS | 实时（<1秒） | best-effort | 管理端实时同步、流式通知 |

### 4.2 Webhook 事件类型

| 事件类型 | 触发条件 | 关键字段 |
|---------|---------|---------|
| `context.created` | 新上下文入库 | context_id, title, domain, confidence_level |
| `context.updated` | 上下文内容被修改 | context_id, changed_fields[] |
| `context.status_changed` | 生命周期状态变更 | context_id, old_status, new_status |
| `context.confidence_changed` | 可信度分数/等级变更 | context_id, old_score, new_score, reason |
| `context.conflict_detected` | 检测到矛盾 | context_id_a, context_id_b, conflict_type |
| `context.conflict_resolved` | 矛盾被裁决 | context_id, resolution, resolved_by |
| `context.decaying` | 衰减预警（衰减前N天） | context_id, days_until_decay |
| `context.archived` | 上下文归档 | context_id, archive_reason |
| `entity.created` | 新实体创建 | entity_id, name, type |
| `entity.updated` | 实体信息更新 | entity_id, changed_fields[] |
| `review.task_created` | 新的审核任务 | task_id, context_id, task_type |
| `review.task_completed` | 审核任务完成 | task_id, decision, reviewer |
| `alert.triggered` | 告警触发 | alert_type, severity, message |
| `metrics.threshold_breached` | 指标超阈值 | metric_name, current_value, threshold |

### 4.3 Webhook 协议细节

```json
// POST <webhook_url>（父产品注册的URL）
// Headers:
//   Content-Type: application/json
//   X-CP-Event-Type: context.created
//   X-CP-Event-Id: evt_abc123def456
//   X-CP-Workspace-Id: ws_abc123
//   X-CP-Delivery-Id: dly_001
//   X-CP-Signature: sha256=xxxxxxxxxx
//   X-CP-Timestamp: 2026-06-23T12:30:00Z

{
  "event_id": "evt_abc123def456",
  "event_type": "context.created",
  "workspace_id": "ws_abc123",
  "timestamp": "2026-06-23T12:30:00Z",
  "data": {
    "context_id": "ctx_abc123",
    "title": "利欧泵业2026年Q2中东市场哥伦布项目进展",
    "domain": "project",
    "confidence_level": "L3",
    "lifecycle_status": "pending_review",
    "entities": [
      {"id": "ent_001", "name": "利欧泵业", "type": "customer"},
      {"id": "ent_002", "name": "哥伦布项目", "type": "project"}
    ],
    "created_by": "parent_user_123",
    "url": "https://context-platform.example.com/api/v1/external/contexts/ctx_abc123"
  }
}
```

**父产品应返回**：HTTP 2xx（200-299），否则本产品将重试。

### 4.4 Webhook 签名验证

父产品可用 `X-CP-Signature` Header 验证 Webhook 来源：

```python
# 父产品验证签名（伪代码）
import hmac, hashlib

def verify_signature(payload: bytes, signature_header: str, secret: str) -> bool:
    """验证 Webhook 签名。secret 是创建工作区时返回的 webhook_secret。"""
    computed = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    expected = f"sha256={computed}"
    return hmac.compare_digest(expected, signature_header)
```

### 4.5 Webhook 重试策略

| 状态码 | 行为 |
|--------|------|
| 200-299 | 成功，不重试 |
| 301/302/307/308 | 跟随重定向（最多3次） |
| 400-499（不含429） | 不重试（客户端错误），记录失败日志 |
| 429 | 指数退避重试（最多5次，首次等1分钟） |
| 500-599 | 线性退避重试（最多5次，间隔1/2/4/8/16分钟） |
| 网络错误/超时 | 线性退避重试（最多3次） |

### 4.6 事件过滤

父产品可注册事件过滤器，仅接收感兴趣的事件。

**界面友好原则**：管理员不需要手写 JSON 过滤规则。所有过滤条件通过勾选框、下拉框和搜索选择器完成，系统自动组装 `filter_rules` 和 `event_types`。

**Webhook 事件过滤管理界面**（管理端 `/admin/workspaces/{id}/webhook` 页面）：

```
┌─ Webhook 事件过滤配置 ─────────────────────────────────────────────┐
│                                                                     │
│ 回调地址与安全                                                       │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 回调 URL       [https://parent-product.example.com/hooks/co ] │   │
│ │                ntext-events                                  ] │   │
│ │ Webhook Secret  [whsec_new_secret_xxx                  ]     │   │
│ │                [重新生成]   (点击生成新的随机密钥)             │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 接收的事件类型（勾选关心的事件）                                       │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 上下文事件:                                                     │   │
│ │ [✓] context.created         — 新上下文入库                     │   │
│ │ [✓] context.updated         — 上下文内容被修改                 │   │
│ │ [✓] context.status_changed  — 生命周期状态变更                 │   │
│ │ [ ] context.confidence_changed — 可信度变更                   │   │
│ │ [✓] context.conflict_detected — 检测到矛盾                    │   │
│ │ [ ] context.conflict_resolved — 矛盾被裁决                     │   │
│ │ [ ] context.decaying        — 衰减预警                         │   │
│ │ [ ] context.archived        — 上下文归档                       │   │
│ │                                                               │   │
│ │ 实体事件:                                                       │   │
│ │ [ ] entity.created          — 新实体创建                       │   │
│ │ [ ] entity.updated          — 实体信息更新                     │   │
│ │                                                               │   │
│ │ 审核与告警事件:                                                  │   │
│ │ [ ] review.task_created     — 新的审核任务                     │   │
│ │ [ ] review.task_completed   — 审核任务完成                     │   │
│ │ [✓] alert.triggered         — 告警触发                         │   │
│ │ [ ] metrics.threshold_breached — 指标超阈值                    │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 内容过滤规则（以下过滤条件均为"与"关系，全部满足才推送）               │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 最低可信度等级: [L2 ▾]                                        │   │
│ │ → 仅推送不低于此等级上下文的事件。可选: L0/L1/L2/L3/L4/L5      │   │
│ │                                                               │   │
│ │ 限定域:                                                        │   │
│ │ [✓] customer  (客户域)                                        │   │
│ │ [✓] project   (项目域)                                        │   │
│ │ [ ] operations (运营域)                                       │   │
│ │ [ ] external   (外部环境域)                                   │   │
│ │ → 仅推送属于勾选域的上下文事件                                  │   │
│ │                                                               │   │
│ │ 限定实体（选填，留空表示不过滤）:                               │   │
│ │ 已选实体: [利欧泵业 ✕] [YY科技 ✕]                              │   │
│ │ 搜索添加实体: [                            ] 🔍              │   │
│ │ → 仅推送关联这些实体的上下文事件。支持模糊搜索选择。             │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│ 频率控制                                                             │
│ ┌──────────────────────────────────────────────────────────────┐   │
│ │ 每分钟最多推送 [  60 ] 条事件                                 │   │
│ │ 同类型事件合并窗口 [  10 ] 秒（窗口内的同类型事件合并为一条）   │   │
│ └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│                                              [测试推送] [保存配置]   │
└─────────────────────────────────────────────────────────────────────┘
```

**API 接口**（前端自动组装请求体，用户无需关心）：

```json
// PUT /api/v1/external/workspaces/{id}/webhook-config 请求（前端自动生成）
{
  "url": "https://parent-product.example.com/hooks/context-events",
  "secret": "whsec_new_secret_xxx",
  "event_types": [
    "context.created",
    "context.status_changed",
    "context.conflict_detected",
    "alert.triggered"
  ],
  "filter_rules": {
    "confidence_min": "L2",
    "domains": ["customer", "project"],
    "entities": ["利欧泵业", "YY科技"]
  },
  "max_events_per_minute": 60,
  "batch_window_seconds": 10
}
```

**说明**：
- 事件类型通过**勾选框**选择，14 种事件类型按分组展示，无需记忆事件名
- 过滤规则的 `domains` 通过**多选勾选框**、`confidence_min` 通过**下拉框**、`entities` 通过**搜索选择器**完成
- 系统自动将勾选的事件类型组装为 `event_types` 数组，将表单过滤条件组装为 `filter_rules` JSON 对象
- 「测试推送」按钮发送一条测试事件到 Webhook URL，用于验证连接和签名

---

## 5. UI 嵌入方案

### 5.1 嵌入模式选择

| 模式 | 集成难度 | 隔离性 | 样式自定义 | 通信能力 |
|------|---------|--------|-----------|---------|
| iframe | 低 | 天然隔离 | 通过postMessage主题配置 | postMessage API |
| Web Component | 中 | Shadow DOM隔离 | 通过CSS变量+属性 | DOM事件+属性 |
| React SDK | 中高 | 共享React上下文 | 完全自定义 | 直接API调用 |

### 5.2 iframe 嵌入

父产品通过 iframe 嵌入本产品的指定页面：

```html
<!-- 父产品页面 -->
<iframe
  id="context-platform-iframe"
  src="https://context-platform.example.com/embed/search?workspace_id=ws_abc123&token=xxx&theme=light&lang=zh-CN"
  width="100%"
  height="800px"
  allow="clipboard-write"
  sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
></iframe>
```

**URL 参数**：
| 参数 | 必填 | 说明 |
|------|------|------|
| `workspace_id` | 是（多租户） | 工作区ID |
| `token` | 是 | 临时访问Token（JWT，TTL=5分钟） |
| `page` | 否 | 嵌入的页面：search / graph / workspace / notifications |
| `theme` | 否 | light / dark / auto |
| `lang` | 否 | zh-CN / en |
| `primary_color` | 否 | 主题色（hex色值） |
| `hide_header` | 否 | 是否隐藏顶部导航栏（true/false） |
| `hide_sidebar` | 否 | 是否隐藏侧边栏（true/false） |
| `entity_filter` | 否 | 初始实体筛选（逗号分隔） |

**postMessage 通信协议**：

```typescript
// 父产品 → 本产品（iframe）
// 导航到指定页面
iframe.contentWindow.postMessage({
  type: "CP_NAVIGATE",
  payload: { page: "detail", contextId: "ctx_abc123" }
}, "https://context-platform.example.com");

// 应用筛选条件
iframe.contentWindow.postMessage({
  type: "CP_APPLY_FILTER",
  payload: { domain: "customer", entity: "利欧泵业" }
}, "https://context-platform.example.com");

// 更新主题
iframe.contentWindow.postMessage({
  type: "CP_SET_THEME",
  payload: { theme: "dark", primary_color: "#7C3AED" }
}, "https://context-platform.example.com");

// 本产品 → 父产品
// 上下文被选中
window.parent.postMessage({
  type: "CP_CONTEXT_SELECTED",
  payload: {
    contextId: "ctx_abc123",
    title: "利欧泵业2026年Q2...",
    domain: "project",
    confidence: { level: "L3", score: 0.78 }
  }
}, "https://parent-product.example.com");

// 搜索完成
window.parent.postMessage({
  type: "CP_SEARCH_COMPLETED",
  payload: { query: "利欧泵业", resultCount: 12, queryTimeMs: 234 }
}, "https://parent-product.example.com");

// iframe 高度变化（自适应高度）
window.parent.postMessage({
  type: "CP_RESIZE",
  payload: { height: 1200 }
}, "https://parent-product.example.com");
```

### 5.3 Web Component 嵌入

```typescript
// 父产品页面使用
<context-platform-search
  workspace-id="ws_abc123"
  token="eyJhbGci..."
  theme="light"
  primary-color="#2563EB"
  language="zh-CN"
  hide-header="true"
  initial-query="利欧泵业"
  initial-domain="customer"
></context-platform-search>

<script>
  const widget = document.querySelector('context-platform-search');
  
  // 监听事件
  widget.addEventListener('cp-context-selected', (e) => {
    console.log('Selected context:', e.detail);
    // { contextId: "ctx_abc123", title: "...", ... }
  });
  
  widget.addEventListener('cp-search-completed', (e) => {
    console.log('Search completed:', e.detail);
  });
  
  // 调用方法
  widget.navigateToContext('ctx_abc123');
  widget.applyFilter({ entity: '利欧泵业' });
  widget.setTheme({ theme: 'dark', primaryColor: '#7C3AED' });
</script>
```

**Web Component 提供的组件**：

| 组件名 | 用途 |
|--------|------|
| `<context-platform-search>` | 搜索引擎页 |
| `<context-platform-graph>` | 知识图谱页 |
| `<context-platform-detail>` | 上下文详情页（指定context_id） |
| `<context-platform-timeline>` | 上下文时间线（指定entity） |
| `<context-platform-workspace>` | 工作区总览 |

### 5.4 React SDK（TypeScript）

供父产品（如果是 React 应用）深度集成：

```typescript
// 父产品安装: npm install @context-platform/sdk-react

import { 
  ContextPlatformProvider, 
  SearchWidget, 
  GraphWidget,
  useContextPlatform 
} from '@context-platform/sdk-react';

function ParentApp() {
  return (
    <ContextPlatformProvider
      config={{
        baseUrl: 'https://context-platform.example.com',
        workspaceId: 'ws_abc123',
        apiKey: 'cpk_live_xxx',           // 或使用 token/tokenProvider
        theme: {
          primaryColor: '#2563EB',
          mode: 'auto'
        },
        locale: 'zh-CN',
        onEvent: (event) => {
          console.log('CP Event:', event.type, event.data);
        }
      }}
    >
      <div className="parent-layout">
        <Sidebar />
        <main>
          {/* 嵌入式搜索组件 */}
          <SearchWidget
            initialQuery="利欧泵业"
            onContextSelect={(ctx) => {
              // 父产品处理上下文选择
              openDetailPanel(ctx.id);
            }}
            style={{ height: '600px', borderRadius: '8px' }}
          />
        </main>
      </div>
    </ContextPlatformProvider>
  );
}

// 或使用 hook 直接调用 API
function MyComponent() {
  const { search, createContext, getEntityGraph } = useContextPlatform();
  
  const handleSearch = async () => {
    const result = await search({
      query: '利欧泵业哥伦布项目',
      mode: 'hybrid',
      filters: { confidence_min: 'L3' }
    });
    // result.items: 上下文列表
    // result.total: 总数
    // result.consumption_guidance: 消费指引（引用建议+交叉验证提示+经验库标记）
    console.log(result.items, result.total, result.consumption_guidance);
    
    // 消费指引示例:
    // {
    //   usage_advice: "需交叉验证",
    //   advice_reason: "该上下文可信度L3",
    //   related_higher_confidence_count: 1,
    //   related_higher_confidence_hint: "同实体下存在1条L4+关联上下文",
    //   is_lesson_learned: false,
    //   cross_validation_suggestion: "建议一并检索'利欧泵业Q1审计报告'(L5)"
    // }
  };
  
  return <button onClick={handleSearch}>搜索上下文</button>;
}
```

---

## 6. 数据隔离与多租户

### 6.1 隔离策略

```
┌─────────────────────────────────────────────────────────────────┐
│                     PostgreSQL 单实例                             │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                   数据行级隔离                              │   │
│  │                                                           │   │
│  │  context_items 表:                                        │   │
│  │  ┌──────┬───────────────────┬──────────────┬─────────┐  │   │
│  │  │  id  │  title            │ workspace_id  │  ...    │  │   │
│  │  ├──────┼───────────────────┼──────────────┼─────────┤  │   │
│  │  │ 001  │ 利欧泵业Q2进展    │ ws_parent_a   │  ...    │  │   │
│  │  │ 002  │ YY科技供应链      │ ws_parent_a   │  ...    │  │   │
│  │  │ 003  │ 竞品动态-ABC公司  │ ws_parent_b   │  ...    │  │   │
│  │  └──────┴───────────────────┴──────────────┴─────────┘  │   │
│  │                                                           │   │
│  │  所有查询自动附加 WHERE workspace_id = current_workspace  │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                  独立 Schema（可选）                       │   │
│  │                                                           │   │
│  │  对于高安全要求场景，可为每个 workspace 创建独立 Schema     │   │
│  │  ws_parent_a.context_items, ws_parent_b.context_items...  │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 6.2 数据库变更

在核心表中增加 `workspace_id` 字段：

```sql
-- 工作区表
CREATE TABLE workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    VARCHAR(32) NOT NULL UNIQUE,   -- 可读ID: ws_abc123
    name            VARCHAR(256) NOT NULL,
    slug            VARCHAR(128) NOT NULL UNIQUE,
    description     TEXT,
    auth_config     JSONB NOT NULL DEFAULT '{}',  -- 认证配置
    features        JSONB NOT NULL DEFAULT '{}',  -- 功能开关
    quotas          JSONB NOT NULL DEFAULT '{}',  -- 配额限制
    webhook_config  JSONB,                        -- 事件回调配置
    ui_config       JSONB,                        -- UI嵌入配置
    status          VARCHAR(16) NOT NULL DEFAULT 'active',  -- active/suspended/deleted
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workspaces_slug ON workspaces(slug);
CREATE INDEX idx_workspaces_status ON workspaces(status);

-- API Key 表
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            VARCHAR(256) NOT NULL,
    key_hash        VARCHAR(128) NOT NULL,         -- bcrypt hash of the key
    key_prefix      VARCHAR(8) NOT NULL,           -- cpk_live (前8字符)
    role            VARCHAR(32) NOT NULL DEFAULT 'admin',
    entity_scope    TEXT[] DEFAULT '{}',           -- 实体范围限制
    allowed_ips     TEXT[],                        -- IP白名单
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_revoked      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_workspace ON api_keys(workspace_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);

-- JWT 配置表
CREATE TABLE jwt_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE UNIQUE,
    issuer          VARCHAR(512) NOT NULL,
    jwks_url        VARCHAR(1024),
    audience        VARCHAR(256),
    claim_mapping   JSONB NOT NULL DEFAULT '{}',
    default_role    VARCHAR(32) NOT NULL DEFAULT 'consultant',
    token_refresh_url VARCHAR(1024),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_verified_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 在已有核心表中增加 workspace_id
ALTER TABLE context_items ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE entities ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE relations ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE users ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE permissions ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE notifications ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE push_rules ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE system_configs ADD COLUMN workspace_id UUID REFERENCES workspaces(id);  -- NULL = 全局配置

-- 索引
CREATE INDEX idx_context_items_workspace ON context_items(workspace_id);
CREATE INDEX idx_entities_workspace ON entities(workspace_id);
```

### 6.3 SQL 查询层自动过滤

在 SQLAlchemy 层面实现自动 workspace 过滤：

```python
# backend/app/core/workspace_mixin.py

from sqlalchemy import Column, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import declared_attr

class WorkspaceMixin:
    """所有需要 workspace 隔离的表 Mixin。"""
    
    @declared_attr
    def workspace_id(cls) -> Column:
        return Column(UUID(as_uuid=True), ForeignKey("workspaces.id"), nullable=True, index=True)

# backend/app/core/workspace_filter.py

from contextvars import ContextVar

current_workspace_id: ContextVar[str] = ContextVar("current_workspace_id", default=None)

class WorkspaceFilteredQuery:
    """自动在查询中附加 workspace_id 过滤条件。
    
    使用方式:
    class ContextService:
        def list_contexts(self, filters):
            query = select(ContextItem)
            query = apply_workspace_filter(query, ContextItem)  # 自动加 WHERE workspace_id = ...
            return await db.execute(query)
    """

def apply_workspace_filter(query, model):
    ws_id = current_workspace_id.get()
    if ws_id and hasattr(model, 'workspace_id'):
        query = query.where(model.workspace_id == ws_id)
    return query

# 中间件：从请求中解析 workspace_id
class WorkspaceResolutionMiddleware:
    """FastAPI 中间件：解析并设置当前请求的 workspace_id。
    
    优先级:
    1. X-CP-Workspace-Id header
    2. API Key 关联的 workspace
    3. JWT claim 中的 workspace
    """
    
    async def __call__(self, request, call_next):
        workspace_id = await self._resolve_workspace(request)
        token = current_workspace_id.set(workspace_id)
        try:
            return await call_next(request)
        finally:
            current_workspace_id.reset(token)
```

---

## 7. 组件清单（Plugin Manifest）

### 7.1 Manifest 文件

本产品在部署时自动生成 `plugin-manifest.json`，父产品可通过此文件了解组件的全部接口。

```json
{
  "manifest_version": "1.0.0",
  "plugin": {
    "id": "context-platform",
    "name": "统一上下文管理中心",
    "name_en": "Unified Context Management Platform",
    "version": "1.2.0",
    "description": "提供上下文采集、存储、检索、可信度评估、生命周期管理的企业级基础设施组件",
    "vendor": {
      "name": "Celnet",
      "url": "https://celnet.example.com"
    },
    "icon_url": "https://context-platform.example.com/static/plugin-icon.svg",
    "license": "Proprietary"
  },
  
  "runtime": {
    "mode": "embedded",
    "tenant_mode": "multi",
    "base_url": "https://context-platform.example.com",
    "api_prefix": "/api/v1/external",
    "docs_url": "https://context-platform.example.com/api/docs",
    "health_check_url": "https://context-platform.example.com/api/v1/external/health"
  },
  
  "authentication": {
    "supported_methods": ["api_key", "jwt", "custom"],
    "require_workspace_id": true
  },
  
  "apis": {
    "rest": {
      "spec_url": "https://context-platform.example.com/api/v1/external/openapi.json",
      "version": "v1",
      "endpoint_groups": [
        {
          "name": "上下文管理",
          "prefix": "/api/v1/external/contexts",
          "endpoints": [
            {"method": "GET", "path": "", "description": "列表查询", "required_permission": "context:read"},
            {"method": "POST", "path": "", "description": "创建上下文", "required_permission": "context:write"},
            {"method": "GET", "path": "/{id}", "description": "获取上下文详情", "required_permission": "context:read"},
            {"method": "PUT", "path": "/{id}", "description": "更新上下文", "required_permission": "context:write"},
            {"method": "DELETE", "path": "/{id}", "description": "软删除上下文", "required_permission": "context:delete"},
            {"method": "POST", "path": "/batch", "description": "批量导入", "required_permission": "context:write"}
          ]
        },
        {
          "name": "搜索检索",
          "prefix": "/api/v1/external/search",
          "endpoints": [
            {"method": "POST", "path": "", "description": "混合搜索", "required_permission": "search:execute"},
            {"method": "GET", "path": "/suggestions", "description": "搜索建议", "required_permission": "search:execute"}
          ]
        },
        {
          "name": "实体管理",
          "prefix": "/api/v1/external/entities",
          "endpoints": [
            {"method": "GET", "path": "", "description": "实体列表"},
            {"method": "POST", "path": "", "description": "创建/更新实体(upsert)"},
            {"method": "GET", "path": "/{id}", "description": "实体详情"},
            {"method": "GET", "path": "/{id}/graph", "description": "实体关联图谱"}
          ]
        },
        {
          "name": "工作区管理",
          "prefix": "/api/v1/external/workspaces",
          "endpoints": [
            {"method": "POST", "path": "", "description": "创建工作区"},
            {"method": "GET", "path": "", "description": "工作区列表"},
            {"method": "GET", "path": "/{id}", "description": "工作区详情"},
            {"method": "PUT", "path": "/{id}", "description": "更新工作区"},
            {"method": "DELETE", "path": "/{id}", "description": "删除工作区"}
          ]
        },
        {
          "name": "健康检查",
          "prefix": "/api/v1/external/health",
          "endpoints": [
            {"method": "GET", "path": "", "description": "健康检查"},
            {"method": "GET", "path": "/metrics", "description": "性能指标(Prometheus格式)"}
          ]
        }
      ]
    }
  },
  
  "events": {
    "webhook": {
      "supported_event_types": [
        "context.created", "context.updated", "context.status_changed",
        "context.confidence_changed", "context.conflict_detected",
        "context.conflict_resolved", "context.decaying", "context.archived",
        "entity.created", "entity.updated",
        "review.task_created", "review.task_completed",
        "alert.triggered", "metrics.threshold_breached"
      ],
      "signature_algorithm": "HMAC-SHA256",
      "retry_policy": "exponential_backoff_max_5"
    },
    "websocket": {
      "url": "wss://context-platform.example.com/ws/external?workspace_id={workspace_id}&token={token}"
    }
  },
  
  "ui_embedding": {
    "supported_methods": ["iframe", "web_component", "react_sdk"],
    "pages": ["search", "graph", "detail", "timeline", "workspace"],
    "theming": {
      "supported_themes": ["light", "dark", "auto"],
      "customizable": ["primary_color", "logo_url", "font_family"]
    },
    "web_components": [
      "context-platform-search",
      "context-platform-graph",
      "context-platform-detail",
      "context-platform-timeline",
      "context-platform-workspace"
    ],
    "react_sdk_package": "@context-platform/sdk-react",
    "react_sdk_version": "^1.2.0"
  },
  
  "dependencies": {
    "requires": {
      "postgresql": ">=16.0",
      "redis": ">=7.0 (可选，用于缓存和事件广播)"
    },
    "optional": {
      "qdrant": "用于Mem0集成",
      "feishu_api": "用于飞书采集",
      "deepseek_api": "用于LLM功能"
    }
  },
  
  "monitoring": {
    "health_check_interval": "30s",
    "metrics_format": "prometheus",
    "alert_channels": ["webhook"]
  },
  
  "lifecycle": {
    "initialization": {
      "estimated_seconds": 30,
      "required_actions": ["database_migration", "seed_default_configs"]
    },
    "shutdown": {
      "grace_period_seconds": 10
    }
  }
}
```

---

## 8. 集成适配层实现（IntegrationAdapter）

### 8.1 集成适配层架构

```python
# backend/app/integrations/adapter.py
# 集成适配层：将所有外部请求适配到内部服务层

from fastapi import FastAPI, Request, Depends
from typing import Optional

class IntegrationAdapter:
    """集成适配层入口。
    
    职责：
    1. 认证：验证外部Token → 解析为内部用户身份
    2. 租户解析：从请求中提取 workspace_id
    3. 权限映射：外部权限 → 内部Action枚举
    4. 数据隔离：确保所有查询附加 workspace 过滤
    5. 审计：记录所有外部调用
    """

    def __init__(self, app: FastAPI):
        self.app = app
        self._register_middleware()
        self._register_routes()

    async def resolve_identity(self, request: Request) -> ResolvedIdentity:
        """从请求中解析调用者身份。
        
        依次尝试：
        1. API Key → 查 api_keys 表 → 获取 workspace + role
        2. JWT Token → 验证签名 → 从 claims 提取 identity
        3. 自定义Token → 回调父产品验证 → 获取 identity
        """
        ...

    async def resolve_workspace(self, request: Request, identity: ResolvedIdentity) -> Workspace:
        """确定当前请求的 workspace。
        
        多租户模式：
        - 从 X-CP-Workspace-Id header 获取
        - 从认证凭证关联的 workspace 获取
        
        单租户模式：
        - 返回唯一的默认 workspace
        """
        ...

    async def check_quota(self, workspace: Workspace, action: str) -> bool:
        """检查工作区配额是否超限。"""
        ...

    async def audit_external_call(self, workspace: Workspace, identity: ResolvedIdentity, 
                                   method: str, path: str, status_code: int, duration_ms: float):
        """记录外部API调用审计日志。"""
        ...

@dataclass
class ResolvedIdentity:
    user_id: str
    role: str
    permissions: list[str]
    workspace_id: str
    entity_boundaries: list[str]
    is_authenticated: bool
    auth_method: str  # api_key / jwt / custom

@dataclass
class Workspace:
    id: UUID
    workspace_id: str
    name: str
    features: dict
    quotas: dict
    status: str
```

### 8.2 外部API路由注册

```python
# backend/app/api/external/router.py

from fastapi import APIRouter, Depends
from app.integrations.adapter import IntegrationAdapter, ResolvedIdentity, Workspace

router = APIRouter(prefix="/api/v1/external", tags=["external"])

# 依赖注入
async def get_identity(request: Request) -> ResolvedIdentity:
    adapter: IntegrationAdapter = request.app.state.integration_adapter
    return await adapter.resolve_identity(request)

async def get_workspace(request: Request, identity: ResolvedIdentity = Depends(get_identity)) -> Workspace:
    adapter: IntegrationAdapter = request.app.state.integration_adapter
    return await adapter.resolve_workspace(request, identity)

# 上下文管理路由
@router.get("/contexts")
async def list_contexts(
    domain: str = None,
    confidence_min: str = None,
    status: str = None,
    page: int = 1,
    page_size: int = 20,
    workspace: Workspace = Depends(get_workspace),
    identity: ResolvedIdentity = Depends(get_identity),
):
    """外部上下文列表查询。自动按 workspace 隔离。"""
    return await context_service.list_external(
        workspace_id=workspace.id,
        filters={...},
        page=page,
        page_size=page_size
    )

@router.post("/search")
async def search(
    body: SearchRequest,
    workspace: Workspace = Depends(get_workspace),
    identity: ResolvedIdentity = Depends(get_identity),
):
    """外部搜索接口。自动按 workspace 隔离 + 权限过滤。"""
    result = await search_service.search_external(
        workspace_id=workspace.id,
        identity=identity,
        query=body.query,
        mode=body.mode,
        filters=body.filters,
        page=body.page,
        page_size=body.page_size,
    )
    return result
```

---

## 9. 生命周期管理

### 9.1 组件生命周期钩子

```python
# backend/app/lifecycle.py

class ComponentLifecycle:
    """组件生命周期管理器。提供标准的启动/停止/健康检查接口。"""

    async def on_init(self, config: dict) -> InitResult:
        """组件初始化阶段。
        
        在首次部署或重启时执行：
        1. 验证数据库连接
        2. 运行数据库迁移
        3. 初始化默认配置
        4. 加载已注册的 workspace
        """
        stages = [
            ("database_check", self._check_database),
            ("migration", self._run_migrations),
            ("seed_configs", self._seed_default_configs),
            ("load_workspaces", self._load_active_workspaces),
            ("start_services", self._start_background_services),
        ]
        results = {}
        for name, stage_fn in stages:
            try:
                results[name] = await stage_fn()
            except Exception as e:
                return InitResult(success=False, stage=name, error=str(e))
        return InitResult(success=True, stages=results)

    async def on_start(self) -> None:
        """组件启动后执。
        
        - 启动 WebSocket 服务
        - 启动定时任务调度器
        - 注册优雅关闭处理
        """
        ...

    async def on_shutdown(self, signal: str) -> None:
        """优雅关闭。
        
        1. 停止接收新请求
        2. 等待进行中的请求完成（grace_period）
        3. 关闭数据库连接池
        4. 关闭 Redis 连接
        5. 关闭后台任务
        """
        ...

    async def health_check(self) -> HealthStatus:
        """健康检查。
        
        Returns:
            HealthStatus with component-level status:
            - database: healthy/degraded/unhealthy
            - redis: healthy/degraded/unhealthy (optional)
            - graph_engine: healthy/degraded/unhealthy
            - llm_service: healthy/degraded/unhealthy
            - ingestion_pipeline: healthy/degraded/unhealthy
        """
        ...

@dataclass
class InitResult:
    success: bool
    stage: str | None = None
    error: str | None = None
    stages: dict[str, bool] | None = None
```

### 9.2 Docker Compose 集成示例

```yaml
# 父产品的 docker-compose.yml 集成示例
version: '3.8'

services:
  parent-app:
    build: .
    ports: ["3000:3000"]
    environment:
      CONTEXT_PLATFORM_URL: http://context-platform:8000
      CONTEXT_PLATFORM_API_KEY: cpk_live_xxx
    depends_on:
      context-platform:
        condition: service_healthy

  context-platform:
    image: celnet/context-platform:1.2.0
    ports: ["8001:8000"]
    environment:
      RUNTIME_MODE: embedded
      TENANT_MODE: multi
      DATABASE_URL: postgresql://admin:password@db:5432/context_platform
      DEEPSEEK_API_KEY: ${DEEPSEEK_API_KEY}
      SECRET_KEY: ${CONTEXT_PLATFORM_SECRET_KEY}
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_started
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/external/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: pgvector/pgvector:pg16
    volumes: ["pgdata:/var/lib/postgresql/data"]
    environment:
      POSTGRES_DB: context_platform
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: ${DB_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes: ["redis_data:/data"]

volumes:
  pgdata:
  redis_data:
```

---

## 10. SDK 设计（客户端库）

### 10.1 Python SDK

```python
# 父产品安装: pip install context-platform-client

from context_platform_client import ContextPlatformClient, models

# 初始化客户端
client = ContextPlatformClient(
    base_url="https://context-platform.example.com",
    api_key="cpk_live_xxx",
    workspace_id="ws_abc123"  # 多租户模式必须
)

# 搜索上下文
results = client.search(
    query="利欧泵业哥伦布项目",
    mode="hybrid",
    filters=models.SearchFilters(
        domain=["customer", "project"],
        confidence_min="L3"
    ),
    page=1,
    page_size=20
)
print(f"找到 {results.total} 条结果")
for item in results.items:
    print(f"  [{item.confidence.level}] {item.title}")

# 消费指引（帮助Agent做出正确的引用决策）
guidance = results.consumption_guidance
print(f"引用建议: {guidance.usage_advice}")          # 自由引用 / 标注来源后引用 / 需交叉验证 / 不可引用
print(f"建议原因: {guidance.advice_reason}")           # 具体解释
print(f"关联高可信度上下文: {guidance.related_higher_confidence_count} 条")
if guidance.related_higher_confidence_hint:
    print(f"提示: {guidance.related_higher_confidence_hint}")
if guidance.cross_validation_suggestion:
    print(f"交叉验证建议: {guidance.cross_validation_suggestion}")
if guidance.is_lesson_learned:
    print("经验库 — 此为经过实践验证的经验教训，优先参考")

# 创建上下文
ctx = client.create_context(models.CreateContextRequest(
    title="新客户需求确认",
    content="利欧泵业确认新增中东市场3个项目...",
    domain="customer",
    entities=[
        models.EntityRef(name="利欧泵业", type="customer")
    ],
    confidence_source_type="manual_entry"
))
print(f"上下文已创建: {ctx.id}")

# 获取实体图谱
graph = client.get_entity_graph("ent_001", depth=2)
print(f"图谱: {len(graph.nodes)} 个节点, {len(graph.edges)} 条边")

# 注册 Webhook 监听事件
with client.events() as events:
    events.on("context.created", lambda e: print(f"新上下文: {e.data['title']}"))
    events.on("alert.triggered", lambda e: print(f"告警: {e.data['message']}"))
    events.start()
    # ... 应用运行中 ...
```

### 10.2 TypeScript/JavaScript SDK

```typescript
// 父产品安装: npm install @context-platform/client

import { ContextPlatformClient, SearchFilters } from '@context-platform/client';

const client = new ContextPlatformClient({
  baseUrl: 'https://context-platform.example.com',
  apiKey: 'cpk_live_xxx',
  workspaceId: 'ws_abc123',
});

// 搜索上下文
const result = await client.search({
  query: '利欧泵业哥伦布项目',
  mode: 'hybrid',
  filters: {
    domain: ['customer', 'project'],
    confidenceMin: 'L3',
  },
  page: 1,
  pageSize: 20,
});
console.log(`找到 ${result.total} 条结果`);

// 创建上下文
const ctx = await client.createContext({
  title: '新客户需求确认',
  content: '利欧泵业确认新增中东市场3个项目...',
  domain: 'customer',
  entities: [{ name: '利欧泵业', type: 'customer' }],
  confidenceSourceType: 'manual_entry',
});
console.log(`上下文已创建: ${ctx.id}`);

// 监听事件（通过 WebSocket）
const unsub = client.events.on('context.created', (event) => {
  console.log(`新上下文: ${event.data.title}`);
});

// 或通过 Webhook 验证（父产品后端点）
app.post('/hooks/context-events', (req, res) => {
  const isValid = client.verifyWebhookSignature(
    JSON.stringify(req.body),
    req.headers['x-cp-signature'],
    'whsec_xxx'  // webhook secret
  );
  if (isValid) {
    console.log(`事件: ${req.body.event_type}`);
  }
  res.status(200).send('OK');
});
```

---

## 11. 对现有设计文档的影响

### 11.1 架构变更（04_app_architecture.md）

需要新增以下目录和文件：

```
backend/app/
├── integrations/                    # 新增集成适配层
│   ├── adapter.py                   # 集成适配层入口
│   ├── auth/                        # 认证适配
│   │   ├── api_key_auth.py          # API Key 认证
│   │   ├── jwt_delegation.py        # JWT 委托认证
│   │   └── custom_token_auth.py     # 自定义Token回调认证
│   ├── workspace/                   # 工作区管理
│   │   ├── workspace_service.py     # 工作区CRUD
│   │   ├── quota_service.py         # 配额管理
│   │   └── workspace_middleware.py   # 工作区解析中间件
│   └── event_emitter.py             # 事件发射器（Webhook + WebSocket）
├── api/
│   └── external/                    # 外部API路由
│       ├── router.py                # 外部API路由聚合
│       ├── auth.py                  # 认证端点
│       ├── contexts.py              # 上下文管理端点
│       ├── search.py                # 搜索端点
│       ├── entities.py              # 实体管理端点
│       ├── workspaces.py            # 工作区管理端点
│       └── health.py                # 健康检查端点
├── models/
│   ├── workspace.py                 # Workspace ORM
│   ├── api_key.py                   # API Key ORM
│   └── jwt_config.py                # JWT Config ORM
├── sdk/                             # 客户端SDK（独立发布）
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
└── plugin-manifest.json             # 组件清单文件
```

### 11.2 API 端点增加

在已有内部API基础上，新增以下外部API端点：

| 分组 | 新增端点数量 |
|------|------------|
| 认证管理 | 6 |
| 工作区管理 | 5 |
| 上下文管理 | 6（与内部功能一致但对外的版本） |
| 搜索检索 | 2 |
| 实体管理 | 4 |
| 图谱查询 | 2 |
| 健康检查 | 2 |
| **合计** | **27** |

### 11.3 数据库表增加

在已有18张表基础上，新增以下表：

| 表名 | 用途 |
|------|------|
| `workspaces` | 工作区/租户管理 |
| `api_keys` | API Key 管理 |
| `jwt_configs` | JWT 委托认证配置 |
| `webhook_delivery_logs` | Webhook 发送日志（含重试记录） |
| `quota_usage_logs` | 配额用量日志 |

---

## 12. 安全性考量

### 12.1 API Key 安全

- API Key 使用 bcrypt 哈希存储（与密码同等级保护）
- 仅创建时返回完整 Key（之后不可查看）
- 支持设置过期时间
- 支持 IP 白名单
- 支持立即吊销

### 12.2 Webhook 安全

- 所有 Webhook 请求携带 HMAC-SHA256 签名
- 父产品验证签名确认来源
- Webhook URL 强制 HTTPS
- Webhook Secret 定期轮换支持

### 12.3 数据隔离安全

- 所有查询在 SQL 层强制附加 `workspace_id` 过滤
- 多租户模式下，API Key/JWT claim 中的 workspace_id 与请求中 X-CP-Workspace-Id header 交叉验证
- 审计日志记录所有跨 workspace 访问尝试

### 12.4 iframe 嵌入安全

- iframe 设置合理的 sandbox 属性
- 通过 `X-Frame-Options` 和 `Content-Security-Policy frame-ancestors` 限制嵌入来源
- postMessage 通信验证 origin

---

## 13. 实施路线图

### Phase 1：基础接口（Week 1-2）
- [ ] 运行模式（standalone/embedded、single/multi-tenant）
- [ ] Workspace 表 + CRUD
- [ ] API Key 认证
- [ ] workspace_id 列添加到核心表
- [ ] 外部 `/contexts` CRUD API
- [ ] 外部 `/search` API
- [ ] 健康检查端点

### Phase 2：事件与UI嵌入（Week 3-4）
- [ ] Webhook 事件系统（签名+重试）
- [ ] WebSocket 外部事件
- [ ] iframe 嵌入支持
- [ ] postMessage 通信协议
- [ ] Web Component（3个组件）
- [ ] React SDK（第一版）

### Phase 3：完善（Week 5-6）
- [ ] JWT 委托认证
- [ ] 自定义 Token 回调验证
- [ ] 配额管理
- [ ] Webhook 事件过滤
- [ ] Python SDK 发布
- [ ] TypeScript SDK 发布
- [ ] 完整集成文档和示例

---

## 14. 配置参数补充

在 `08_configuration_management.md` 的基础上，新增以下组件集成相关配置：

### 14.1 新增系统级配置（section: `integration`）

| 参数键 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `integration.runtime_mode` | str | standalone | standalone / embedded |
| `integration.tenant_mode` | str | single | single / multi |
| `integration.max_workspaces` | int | 50 | 多租户模式下最大工作区数 |
| `integration.default_workspace_quota.max_contexts` | int | 100000 | 新工作区默认上下文上限 |
| `integration.default_workspace_quota.max_api_calls_per_minute` | int | 500 | 新工作区默认API限流 |
| `integration.webhook.max_retries` | int | 5 | Webhook 最大重试次数 |
| `integration.webhook.timeout_seconds` | int | 10 | Webhook 请求超时 |
| `integration.webhook.retry_base_delay_seconds` | int | 60 | Webhook 重试基础延迟 |
| `integration.iframe.allowed_origins` | list[str] | [] | 允许嵌入iframe的父产品域名 |
| `integration.external_api.rate_limit_per_minute` | int | 300 | 外部API总限流 |

---

## 15. 运维与可观测性

### 15.1 外部调用指标

Prometheus 指标（`/api/v1/external/health/metrics`）：

```
# API 调用计数
cp_external_api_requests_total{workspace="ws_abc123", method="GET", path="/contexts", status="200"}
cp_external_api_requests_total{workspace="ws_abc123", method="POST", path="/search", status="200"}

# API 调用延迟
cp_external_api_request_duration_seconds{workspace="ws_abc123", method="GET", path="/contexts", quantile="0.5"}
cp_external_api_request_duration_seconds{workspace="ws_abc123", method="GET", path="/contexts", quantile="0.95"}

# Webhook 交付
cp_webhook_deliveries_total{workspace="ws_abc123", event_type="context.created", status="success"}
cp_webhook_deliveries_total{workspace="ws_abc123", event_type="context.created", status="failed"}
cp_webhook_delivery_duration_seconds{workspace="ws_abc123", event_type="context.created"}

# 配额使用
cp_workspace_quota_usage{workspace="ws_abc123", quota_type="contexts"}
cp_workspace_quota_usage{workspace="ws_abc123", quota_type="api_calls_per_minute"}

# 工作区状态
cp_workspace_status{workspace="ws_abc123", status="active"} 1
```

### 15.2 日志格式

外部API调用日志：

```json
{
  "timestamp": "2026-06-23T12:30:00.123Z",
  "level": "INFO",
  "component": "external_api",
  "workspace_id": "ws_abc123",
  "auth_method": "api_key",
  "user_id": "parent_user_123",
  "method": "POST",
  "path": "/api/v1/external/search",
  "status_code": 200,
  "duration_ms": 234,
  "request_id": "req_abc123",
  "user_agent": "ContextPlatformClient-Python/1.2.0"
}
```

---

## 16. 完整集成示例

### 16.1 父产品最小集成（API模式，10分钟完成）

```python
# 父产品后端代码（Python）

from context_platform_client import ContextPlatformClient

# Step 1: 初始化客户端（使用预先生成的 API Key）
cp = ContextPlatformClient(
    base_url=os.environ["CONTEXT_PLATFORM_URL"],
    api_key=os.environ["CONTEXT_PLATFORM_API_KEY"],
    workspace_id=os.environ["CONTEXT_PLATFORM_WORKSPACE_ID"]
)

# Step 2: 在业务逻辑中调用
async def get_customer_context(customer_name: str) -> list:
    """获取指定客户的最新上下文。"""
    result = cp.search(
        query=customer_name,
        mode="hybrid",
        filters=SearchFilters(
            confidence_min="L3",
            status=["active"]
        )
    )
    return result.items

async def record_decision(customer: str, project: str, decision: str):
    """将业务决策记录到上下文平台。"""
    cp.create_context(CreateContextRequest(
        title=f"{customer} - {project} 决策记录",
        content=decision,
        domain="project",
        entities=[
            EntityRef(name=customer, type="customer"),
            EntityRef(name=project, type="project"),
        ],
        confidence_source_type="manual_entry",
        source_system="parent_platform"
    ))

# Step 3: 注册 Webhook 接收事件（在应用启动时）
@cp.events.on("alert.triggered")
async def handle_alert(event):
    if event.data["severity"] == "critical":
        await send_slack_message(f"上下文告警: {event.data['message']}")

@cp.events.on("context.conflict_detected")
async def handle_conflict(event):
    await notify_reviewer(f"上下文矛盾: {event.data['context_id_a']} vs {event.data['context_id_b']}")

cp.events.start()
```

### 16.2 父产品 UI 嵌入（iframe模式）

```html
<!-- 父产品前端页面 -->
<div class="context-panel">
  <iframe
    id="cp-search"
    src="{{ cp_base_url }}/embed/search?workspace_id={{ workspace_id }}&token={{ cp_token }}&hide_header=true&theme=light"
    width="100%"
    height="600"
    sandbox="allow-scripts allow-same-origin allow-forms"
  ></iframe>
</div>

<script>
  const iframe = document.getElementById('cp-search');
  const CP_ORIGIN = '{{ cp_base_url }}';

  // 监听上下文选中事件
  window.addEventListener('message', (event) => {
    if (event.origin !== CP_ORIGIN) return;
    
    if (event.data.type === 'CP_CONTEXT_SELECTED') {
      // 在父产品中打开详情
      openContextDetail(event.data.payload.contextId);
    }
    if (event.data.type === 'CP_RESIZE') {
      // 自适应高度
      iframe.style.height = event.data.payload.height + 'px';
    }
  });
</script>
```

---

## 17. 兼容性与版本策略

### 17.1 API 版本策略

- URL 路径版本：`/api/v1/external/...`
- 大版本号变更（v1 → v2）：不兼容的 API 变更
- 小版本：向后兼容的新增字段和端点
- 每个 API 响应包含 `X-CP-API-Version` header
- 废弃 API 至少提前 6 个月通知（通过 `X-CP-Deprecation` header 和 Webhook 事件）

### 17.2 数据库迁移兼容性

- 所有数据库变更通过 Alembic 迁移向前兼容
- 新增列必须有默认值
- 不直接删除列（先标记废弃，3个版本后删除）
- workspace_id 迁移支持分步执行（先加列允许NULL，再填充，最后加NOT NULL约束）

---

