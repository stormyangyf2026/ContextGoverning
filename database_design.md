# 统一上下文管理中心 — 数据架构与数据库设计 v1.0

> 设计阶段: Phase 1 初始设计 
> 依赖文档: 《基础设施设计-v1.0 §15.2 存储模型》

---

## 1. 整体数据架构

```
┌────────────────────────────────────────────────────────┐
│                    应用服务层                            │
│   FastAPI REST API  │  MCP Server  │  WebSocket        │
└──────────┬──────────────────┬──────────────────────────┘
           │                  │
    ┌──────▼──────┐    ┌──────▼──────┐
    │  SQL查询     │    │  向量检索    │
    │  (SQLAlchemy)│    │  (pgvector) │
    └──────┬──────┘    └──────┬──────┘
           │                  │
    ┌──────▼──────────────────▼──────┐
    │        PostgreSQL 16+           │
    │  ┌───────────────────────────┐ │
    │  │  pgvector 扩展 (向量索引)  │ │
    │  │  pg_bestmatch (BM25)      │ │
    │  └───────────────────────────┘ │
    └────────────────────────────────┘
           │
    ┌──────▼──────┐    ┌─────────────┐
    │  LightRAG    │    │  Qdrant     │
    │  (知识图谱)  │    │  (Mem0向量) │
    └─────────────┘    └─────────────┘
```

**存储职责划分**：

| 存储组件 | 存储内容 | 用途 |
|---------|---------|------|
| PostgreSQL | 上下文条目、实体、关系、权限、用户、审计日志 | 结构化数据主存储 |
| pgvector | 上下文内容向量嵌入 | 语义相似度检索 |
| pg_bestmatch | BM25稀疏向量索引 | 关键词全文检索 |
| LightRAG图存储 | 知识图谱（实体节点+关系边） | 图谱遍历与图增强检索 |
| Qdrant（Mem0） | Agent记忆向量 | L2语义记忆检索 |
| 文件系统/iCloud | 原始文档附件、MEMORY.md | 原始文件存储与多机同步 |

---

## 2. 数据库表结构设计

### 2.1 ER图概览

```
┌─────────────────┐       ┌─────────────────┐
│   users         │       │   roles         │
│  id (PK)        │──┐    │  id (PK)        │
│  username       │  │    │  name           │
│  email          │  │    │  permissions    │
│  role_id (FK)   │──┘    └─────────────────┘
│  created_at     │
└────────┬────────┘
         │
         │ 1:N
         ▼
┌─────────────────┐       ┌─────────────────┐
│  user_entity_   │       │   entities      │
│  assignments    │──────►│  id (PK)        │
│  user_id (FK)   │       │  name           │
│  entity_type    │       │  type           │
│  entity_id (FK) │       │  domain         │
└─────────────────┘       │  metadata (JSON) │
                          └────────┬────────┘
                                   │
         ┌─────────────────────────┼────────────────────┐
         │                         │                    │
         ▼                         ▼                    ▼
┌─────────────────┐       ┌─────────────────┐    ┌─────────────────┐
│  context_items  │       │  relations      │    │  context_       │
│  id (PK)        │◄──────│  id (PK)        │    │  entities_map   │
│  title          │       │  source_id (FK) │    │  context_id (FK)│
│  content        │       │  target_id (FK) │    │  entity_id (FK) │
│  content_vector │       │  relation_type  │    └─────────────────┘
│  domain         │       │  metadata (JSON)│
│  status         │       └─────────────────┘
│  confidence (JSON)
│  lifecycle (JSON)
│  created_by (FK)
│  verified_by (FK)
│  ...            │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌──────────────┐
│context_│ │ permissions  │
│tags    │ │ id (PK)      │
│id (PK) │ │ context_id   │
│ctx_id  │ │ visibility   │
│tag     │ │ allowed_roles│
└────────┘ │ sensitivity  │
           └──────────────┘
```

### 2.2 上下文条目主表 `context_items`

```sql
CREATE TABLE context_items (
    -- 主键与标识
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id      VARCHAR(64) NOT NULL UNIQUE,  -- 可读ID，如 ctx_lioe_2026_q1_strategy
    
    -- 核心内容
    title           VARCHAR(512) NOT NULL,
    content         TEXT NOT NULL,
    content_vector  vector(1024),                 -- pgvector，BGE-M3 本地部署 1024维
    content_hash    VARCHAR(64) NOT NULL,          -- SHA256，用于去重检测
    
    -- 分类
    domain          VARCHAR(32) NOT NULL,          -- customer/project/operations/external
    sub_category    VARCHAR(64),                   -- 二级分类，如 financial/contract/policy
    tags            TEXT[],                        -- PostgreSQL数组，多标签
    
    -- 实体关联（通过 context_entities_map 关联）
    
    -- 可信度（JSON存储，灵活扩展）
    confidence_level VARCHAR(4) NOT NULL DEFAULT 'L2',  -- L0/L1/L2/L3/L4/L5
    confidence_score REAL NOT NULL DEFAULT 0.5,          -- 0.0-1.0
    confidence_source TEXT,                              -- 来源描述
    confidence_source_type VARCHAR(32),                  -- contract/official_doc/expert_verified/financial_report/meeting_minutes/email/project_kb/ai_extract_verified/manual_entry/memory_md/ai_extract/web_scrape/verbal/unknown/competitor_rumor/lesson_learned
    confidence_extracted_by VARCHAR(128),                -- 提取者（AI/人名）

    -- 上下文子类型（经验教训等特殊类型上下文）
    context_subtype VARCHAR(32),                         -- NULL=普通上下文 / lesson_learned=经验教训（含结构化解决方案）
    context_role VARCHAR(16),                            -- Memory.md模板角色：goal/finding/progress/lesson_learned（NULL=非模板导入）
    structured_fields JSONB,                             -- 结构化提取字段。lesson_learned类型时存储 {"error":"...","attempt":"...","resolution":"...","summary":"..."}

    -- 生命周期
    lifecycle_status VARCHAR(16) NOT NULL DEFAULT 'pending_review',
        -- pending_review/active/decaying/needs_update/superseded/contradicted/archived
    lifecycle_valid_from DATE,
    lifecycle_valid_until DATE,
    lifecycle_superseded_by UUID REFERENCES context_items(id),

    -- 不可变策略与版本管理（已确认上下文的"仅追加不修改"）
    is_immutable BOOLEAN NOT NULL DEFAULT FALSE,         -- TRUE=内容不可直接修改，只能创建新版本
    version INTEGER NOT NULL DEFAULT 1,                  -- 版本号，首次创建=1，每次创建新版本时递增
    superseded_by UUID REFERENCES context_items(id),     -- 当被新版本替代时，指向新版本的id

    -- 来源追踪
    source_url TEXT,
    source_document_title VARCHAR(512),
    source_system VARCHAR(32),                   -- project_kb/feishu/email/finance_api/memory_md/manual
    source_platform VARCHAR(32),                 -- 当source_system=project_kb时，记录具体平台：ima/feishu_drive/other_drive；当source_system=memory_md时，记录文件路径
    source_collected_at TIMESTAMPTZ,
    
    -- 人员
    created_by VARCHAR(128) NOT NULL,            -- 创建者标识（用户名或Agent名）
    verified_by VARCHAR(128),                     -- 验证者标识
    verified_at TIMESTAMPTZ,
    
    -- 审计
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    archived_at TIMESTAMPTZ,
    
    -- 权重
    relevance_score REAL DEFAULT 0.0,             -- 相关性评分（实体匹配度）
    
    -- 软删除
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at TIMESTAMPTZ,
    
    -- RLHF 反馈学习字段 (新增)
    classification_source VARCHAR(16) DEFAULT 'rule',         -- rule / learned / manual
    classification_rule_version VARCHAR(32),                  -- 分类时规则版本号
    last_classified_at TIMESTAMPTZ,                           -- 最近分类时间
    auto_classification_correct BOOLEAN                       -- 自动分类是否被审核确认正确
);

-- 索引
CREATE INDEX idx_context_items_domain ON context_items(domain);
CREATE INDEX idx_context_items_status ON context_items(lifecycle_status);
CREATE INDEX idx_context_items_confidence ON context_items(confidence_level);
CREATE INDEX idx_context_items_created ON context_items(created_at DESC);
CREATE INDEX idx_context_items_updated ON context_items(updated_at DESC);
CREATE INDEX idx_context_items_valid_until ON context_items(lifecycle_valid_until)
    WHERE lifecycle_status = 'active';
CREATE INDEX idx_context_items_content_hash ON context_items(content_hash);
CREATE INDEX idx_context_items_source_system ON context_items(source_system);
CREATE INDEX idx_context_items_context_subtype ON context_items(context_subtype);
CREATE INDEX idx_context_items_version ON context_items(version);
CREATE INDEX idx_context_items_is_immutable ON context_items(is_immutable) WHERE is_immutable = TRUE;
CREATE INDEX idx_context_items_class_source ON context_items(classification_source);
CREATE INDEX idx_context_items_class_version ON context_items(classification_rule_version);
CREATE INDEX idx_context_items_class_correct ON context_items(auto_classification_correct) WHERE auto_classification_correct IS NOT NULL;

-- pgvector 向量索引（IVFFlat，适用于10万+数据量时用HNSW替代）
CREATE INDEX idx_context_items_vector ON context_items
    USING ivfflat (content_vector vector_cosine_ops) WITH (lists = 100);

-- 全文搜索索引（用于BM25）
CREATE INDEX idx_context_items_fts ON context_items
    USING GIN (to_tsvector('simple', title || ' ' || content));
```

### 2.3 实体表 `entities`

```sql
CREATE TABLE entities (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(256) NOT NULL,
    type            VARCHAR(32) NOT NULL,         -- customer/project/offering/competitor/person/event
    domain          VARCHAR(32),                   -- customer/project/operations/external
    aliases         TEXT[],                        -- 别称/简称
    metadata        JSONB DEFAULT '{}',           -- 扩展属性（行业/规模/区域等）
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(name, type)
);

CREATE INDEX idx_entities_type ON entities(type);
CREATE INDEX idx_entities_domain ON entities(domain);
CREATE INDEX idx_entities_name_trgm ON entities USING GIN (name gin_trgm_ops);  -- 模糊匹配
```

### 2.4 上下文-实体关联表 `context_entities_map`

```sql
CREATE TABLE context_entities_map (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id      UUID NOT NULL REFERENCES context_items(id) ON DELETE CASCADE,
    entity_id       UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    role            VARCHAR(32),                  -- 实体在此上下文中的角色（subject/object/mention）
    UNIQUE(context_id, entity_id)
);

CREATE INDEX idx_cem_context ON context_entities_map(context_id);
CREATE INDEX idx_cem_entity ON context_entities_map(entity_id);
```

### 2.5 关系表 `relations`

```sql
CREATE TABLE relations (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id       UUID NOT NULL REFERENCES context_items(id) ON DELETE CASCADE,
    target_id       UUID NOT NULL REFERENCES context_items(id) ON DELETE CASCADE,
    relation_type   VARCHAR(32) NOT NULL,
        -- drives/threatens/depends_on/contradicts/supersedes/informs/part_of
    direction       VARCHAR(8) NOT NULL DEFAULT 'forward',  -- forward/bidirectional
    metadata        JSONB DEFAULT '{}',           -- 关系元数据
    created_by      VARCHAR(128) NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(source_id, target_id, relation_type),
    CHECK (source_id != target_id)
);

CREATE INDEX idx_relations_source ON relations(source_id);
CREATE INDEX idx_relations_target ON relations(target_id);
CREATE INDEX idx_relations_type ON relations(relation_type);
```

### 2.6 权限表 `permissions`

```sql
CREATE TABLE permissions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id      UUID NOT NULL REFERENCES context_items(id) ON DELETE CASCADE,
    
    -- 可见性
    visibility      VARCHAR(16) NOT NULL DEFAULT 'internal',
        -- public/internal/confidential/top_secret
    
    -- RBAC
    allowed_roles   TEXT[] NOT NULL DEFAULT '{}',  -- {admin, partner, senior_consultant, consultant}
    
    -- 实体边界（如果非空，仅分配到这些实体的用户可见）
    restricted_entity_type VARCHAR(32),            -- customer/project
    restricted_entity_id   UUID REFERENCES entities(id),
    
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_permissions_context ON permissions(context_id);
CREATE INDEX idx_permissions_visibility ON permissions(visibility);
```

### 2.7 用户表 `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(128) NOT NULL UNIQUE,
    email           VARCHAR(256) NOT NULL UNIQUE,
    display_name    VARCHAR(256),
    role            VARCHAR(32) NOT NULL DEFAULT 'consultant',
        -- admin/partner/senior_consultant/consultant
    avatar_url      TEXT,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_role ON users(role);
```

### 2.8 用户-实体分配表 `user_entity_assignments`

```sql
CREATE TABLE user_entity_assignments (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_type     VARCHAR(32) NOT NULL,          -- customer/project
    entity_id       UUID NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    access_level    VARCHAR(16) NOT NULL DEFAULT 'read',  -- read/write
    UNIQUE(user_id, entity_type, entity_id)
);

CREATE INDEX idx_uea_user ON user_entity_assignments(user_id);
CREATE INDEX idx_uea_entity ON user_entity_assignments(entity_id, entity_type);
```

### 2.9 审计日志表 `audit_logs`

```sql
CREATE TABLE audit_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id      UUID REFERENCES context_items(id) ON DELETE SET NULL,
    action          VARCHAR(32) NOT NULL,           -- create/update/delete/verify/reject/archive/resolve_conflict
    actor           VARCHAR(128) NOT NULL,           -- 操作者
    changes         JSONB DEFAULT '{}',              -- 变更内容快照
    ip_address      INET,
    user_agent      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_context ON audit_logs(context_id);
CREATE INDEX idx_audit_actor ON audit_logs(actor);
CREATE INDEX idx_audit_action ON audit_logs(action);
CREATE INDEX idx_audit_created ON audit_logs(created_at DESC);
```

### 2.10 上下文标签表 `context_tags`

```sql
CREATE TABLE context_tags (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id      UUID NOT NULL REFERENCES context_items(id) ON DELETE CASCADE,
    tag             VARCHAR(128) NOT NULL,
    tag_type        VARCHAR(32) DEFAULT 'manual',   -- auto/manual
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(context_id, tag)
);

CREATE INDEX idx_tags_context ON context_tags(context_id);
CREATE INDEX idx_tags_tag ON context_tags(tag);
```

### 2.11 推送规则表 `push_rules`

```sql
CREATE TABLE push_rules (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(256) NOT NULL,
    description     TEXT,
    trigger_type    VARCHAR(32) NOT NULL,      -- financial_change/milestone_delay/competitor_appear/context_conflict/context_expiring/high_value_intel
    trigger_config  JSONB NOT NULL DEFAULT '{}',  -- 触发条件配置
    target_roles    TEXT[] NOT NULL,              -- 推送目标角色
    target_users    UUID[] DEFAULT '{}',           -- 推送指定用户
    template_id     VARCHAR(64),                   -- 消息模板ID（关联飞书卡片模板）
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.12 通知表 `notifications`

```sql
CREATE TABLE notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type            VARCHAR(32) NOT NULL,          -- alert/review_task/context_update/system
    title           VARCHAR(256) NOT NULL,
    body            TEXT,
    context_id      UUID REFERENCES context_items(id) ON DELETE SET NULL,
    is_read         BOOLEAN NOT NULL DEFAULT FALSE,
    action_url      TEXT,                           -- 点击跳转链接
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_notifications_user ON notifications(user_id, is_read);
CREATE INDEX idx_notifications_created ON notifications(created_at DESC);
```

### 2.13 通知设置表 `notification_settings`

```sql
CREATE TABLE notification_settings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    channels        JSONB NOT NULL DEFAULT '{"feishu_bot": true, "in_app": true, "email": false}',
    quiet_hours_start TIME,                       -- 免打扰开始时间
    quiet_hours_end   TIME,                       -- 免打扰结束时间
    enabled_types   TEXT[] NOT NULL DEFAULT '{}',  -- 启用的通知类型
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.14 推送规则表 `push_rules`

（已在2.11定义，此处为引用）

### 2.15 推送日志表 `push_logs`

```sql
CREATE TABLE push_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_id         UUID REFERENCES push_rules(id),
    context_id      UUID REFERENCES context_items(id),
    triggered_by    TEXT NOT NULL,              -- 触发条件描述
    target_user     UUID REFERENCES users(id),
    target_channel  VARCHAR(32) NOT NULL,       -- feishu_bot/email/in_app
    status          VARCHAR(16) NOT NULL DEFAULT 'sent',  -- sent/delivered/read/failed
    message_content JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_push_logs_rule ON push_logs(rule_id);
CREATE INDEX idx_push_logs_user ON push_logs(target_user);
CREATE INDEX idx_push_logs_created ON push_logs(created_at DESC);
```

### 2.16 系统配置表 `system_configs`

存储系统级可配置参数，通过管理端 `/admin/config` 页面管理。所有配置项附带校验规则和填写说明，修改实时生效。

```sql
CREATE TABLE system_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    section         VARCHAR(64) NOT NULL,      -- 配置分组: confidence_engine/ingestion/search/llm/security/lifecycle/notification/export
    config_key      VARCHAR(128) NOT NULL,     -- 配置键名: 如 decay_start_months
    config_value    JSONB NOT NULL,            -- 配置值（支持 string/number/boolean/array/object）
    value_type      VARCHAR(16) NOT NULL,      -- 值类型: string/number/boolean/array/object
    description     TEXT,                      -- 参数说明（给管理员看）
    default_value   JSONB NOT NULL,            -- 默认值（用于恢复默认）
    validation      JSONB,                     -- 校验规则: {"min": 0, "max": 1.0} 或 {"enum": ["L0","L1","L2","L3","L4","L5"]}
    input_hint      TEXT,                      -- 输入提示和填写样例（给管理员看的指导文字）
    impact_note     TEXT,                      -- 修改影响说明
    is_visible      BOOLEAN NOT NULL DEFAULT TRUE,  -- 是否在管理界面显示
    sort_order      INT NOT NULL DEFAULT 0,    -- 在管理界面中的排序
    updated_by      VARCHAR(128),              -- 最后修改人
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(section, config_key)
);

CREATE INDEX idx_system_configs_section ON system_configs(section);
```

**字段说明**：
- `config_value` 和 `default_value` 使用 JSONB 类型，统一存储不同值类型的配置值（数字存为JSON数字、字符串存为JSON字符串等）
- `validation` 为 JSONB，存储前端输入控件的约束条件，如数值的 min/max/step、字符串的 enum 列表
- `input_hint` 和 `impact_note` 为 Markdown 格式，在管理界面渲染时解析为富文本提示
- 系统部署时通过种子脚本初始化所有默认配置项

### 2.17 用户设置表 `user_settings`

存储用户级配置，通过用户端设置弹窗和管理端用户编辑页管理。

```sql
CREATE TABLE user_settings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    section         VARCHAR(64) NOT NULL,      -- 设置分组: notification_preferences/search_preferences/ui_preferences
    setting_key     VARCHAR(128) NOT NULL,     -- 设置键名: 如 channels.in_app
    setting_value   JSONB NOT NULL,            -- 设置值
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, section, setting_key)
);

CREATE INDEX idx_user_settings_user ON user_settings(user_id);
CREATE INDEX idx_user_settings_section ON user_settings(section);
```

**字段说明**：
- 采用 EAV（实体-属性-值）模式，每条记录存储单个设置键值对
- 新用户注册时，通过默认值函数生成初始设置记录
- 前端读取时按 `section` 聚合为一个 JSON 对象返回

### 2.18 配置变更日志表 `config_change_logs`

记录所有系统配置变更，用于审计追溯。

```sql
CREATE TABLE config_change_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_type     VARCHAR(16) NOT NULL,      -- system/user
    section         VARCHAR(64) NOT NULL,
    config_key      VARCHAR(128) NOT NULL,
    old_value       JSONB,
    new_value       JSONB NOT NULL,
    changed_by      VARCHAR(128) NOT NULL,
    change_reason   TEXT,                      -- 变更原因（管理员填写）
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_config_logs_type ON config_change_logs(config_type);
CREATE INDEX idx_config_logs_section ON config_change_logs(section);
CREATE INDEX idx_config_logs_created ON config_change_logs(created_at DESC);
```

### 2.19 工作区表 `workspaces`（组件化多租户）

```sql
CREATE TABLE workspaces (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    VARCHAR(32) NOT NULL UNIQUE,   -- 可读ID: ws_abc123
    name            VARCHAR(256) NOT NULL,
    slug            VARCHAR(128) NOT NULL UNIQUE,
    description     TEXT,
    auth_config     JSONB NOT NULL DEFAULT '{}',  -- 认证配置: {mode, jwt_config, custom_config}
    features        JSONB NOT NULL DEFAULT '{}',  -- 功能开关: {ingestion_enabled, graph_enabled, ...}
    quotas          JSONB NOT NULL DEFAULT '{}',  -- 配额: {max_contexts, max_api_calls_per_minute, ...}
    webhook_config  JSONB,                        -- Webhook配置: {url, secret, event_types[], filter_rules}
    ui_config       JSONB,                        -- UI嵌入配置: {allowed_origins[], theme}
    status          VARCHAR(16) NOT NULL DEFAULT 'active',  -- active/suspended/deleted
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_workspaces_slug ON workspaces(slug);
CREATE INDEX idx_workspaces_status ON workspaces(status);
```

### 2.20 API Key 表 `api_keys`（组件化外部认证）

```sql
CREATE TABLE api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    name            VARCHAR(256) NOT NULL,
    key_hash        VARCHAR(128) NOT NULL,         -- bcrypt hash of the key
    key_prefix      VARCHAR(8) NOT NULL,           -- cpk_live (前8字符标识)
    role            VARCHAR(32) NOT NULL DEFAULT 'admin',  -- admin/partner/senior_consultant/consultant/agent
    entity_scope    TEXT[] DEFAULT '{}',           -- 实体范围限制
    allowed_ips     TEXT[],                        -- IP白名单
    last_used_at    TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    is_revoked      BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_api_keys_workspace ON api_keys(workspace_id);
CREATE INDEX idx_api_keys_key_hash ON api_keys(key_hash);
```

### 2.21 JWT 配置表 `jwt_configs`（组件化JWT委托认证）

```sql
CREATE TABLE jwt_configs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE UNIQUE,
    issuer          VARCHAR(512) NOT NULL,
    jwks_url        VARCHAR(1024),
    audience        VARCHAR(256),
    claim_mapping   JSONB NOT NULL DEFAULT '{}',  -- {sub: user_id, custom:tenant: workspace_id, ...}
    default_role    VARCHAR(32) NOT NULL DEFAULT 'consultant',
    token_refresh_url VARCHAR(1024),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    last_verified_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### 2.22 Webhook 发送日志表 `webhook_delivery_logs`（组件化事件推送）

```sql
CREATE TABLE webhook_delivery_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE,
    event_id        VARCHAR(64) NOT NULL,
    event_type      VARCHAR(64) NOT NULL,
    target_url      VARCHAR(1024) NOT NULL,
    request_body    JSONB,
    response_status INTEGER,
    response_body   TEXT,
    duration_ms     INTEGER,
    attempt_number  INTEGER NOT NULL DEFAULT 1,
    status          VARCHAR(16) NOT NULL,          -- success/failed/retrying
    error_message   TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_webhook_logs_workspace ON webhook_delivery_logs(workspace_id);
CREATE INDEX idx_webhook_logs_event ON webhook_delivery_logs(event_id);
CREATE INDEX idx_webhook_logs_created ON webhook_delivery_logs(created_at DESC);
```

### 2.23 RLHF 人类反馈强化学习表组（新增）

#### 2.23.1 审核记录表 `review_records`

```sql
CREATE TABLE review_records (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id      UUID NOT NULL REFERENCES context_items(id) ON DELETE CASCADE,
    reviewer_id     UUID NOT NULL REFERENCES users(id),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    decision        VARCHAR(16) NOT NULL,           -- approved / rejected / needs_revision
    reject_reason   VARCHAR(32),                    -- incorrect_classification / outdated / low_quality / duplicate / irrelevant / other
    corrected_domain         VARCHAR(32),
    corrected_sub_category   VARCHAR(64),
    original_domain          VARCHAR(32),
    original_sub_category    VARCHAR(64),
    classification_correct   BOOLEAN,
    confidence_rating        SMALLINT,              -- 1-5
    confidence_adjustment    VARCHAR(8),            -- upgrade / downgrade / confirm / none
    adjusted_confidence_level VARCHAR(4),
    adjusted_confidence_score FLOAT,
    quality_score            SMALLINT,              -- 1-5
    quality_dimensions       JSONB,                 -- {clarity, accuracy, completeness, relevance, timeliness}
    is_golden_sample         BOOLEAN DEFAULT FALSE,
    review_comment           TEXT,
    review_duration_seconds  INTEGER,
    review_source            VARCHAR(16) DEFAULT 'web',
    priority                 VARCHAR(8) DEFAULT 'normal',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rr_context ON review_records(context_id);
CREATE INDEX idx_rr_reviewer ON review_records(reviewer_id);
CREATE INDEX idx_rr_decision ON review_records(decision);
CREATE INDEX idx_rr_workspace ON review_records(workspace_id);
CREATE INDEX idx_rr_class_correct ON review_records(classification_correct);
CREATE INDEX idx_rr_golden ON review_records(is_golden_sample) WHERE is_golden_sample = TRUE;
```

#### 2.23.2 分类标注表 `classification_labels`

```sql
CREATE TABLE classification_labels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    context_id      UUID NOT NULL REFERENCES context_items(id) ON DELETE CASCADE,
    labeler_id      UUID NOT NULL REFERENCES users(id),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    label_type      VARCHAR(16) NOT NULL,           -- domain / sub_category / tag
    predicted_value VARCHAR(64),
    corrected_value VARCHAR(64) NOT NULL,
    confidence      FLOAT DEFAULT 1.0,
    label_source    VARCHAR(16) DEFAULT 'review',   -- review / user_feedback / admin_override / batch_import
    is_validated    BOOLEAN DEFAULT FALSE,
    validated_by    UUID REFERENCES users(id),
    validation_note TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_cl_context ON classification_labels(context_id);
CREATE INDEX idx_cl_labeler ON classification_labels(labeler_id);
CREATE INDEX idx_cl_type ON classification_labels(label_type);
CREATE INDEX idx_cl_source ON classification_labels(label_source);
```

#### 2.23.3 分类规则权重表 `classification_rule_weights`

```sql
CREATE TABLE classification_rule_weights (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    rule_keyword    VARCHAR(128) NOT NULL,
    target_domain   VARCHAR(32) NOT NULL,
    target_sub_category VARCHAR(64),
    weight          FLOAT DEFAULT 0.5,
    precision       FLOAT,
    recall_impact   FLOAT,
    total_matches   INTEGER DEFAULT 0,
    correct_matches INTEGER DEFAULT 0,
    last_corrected  TIMESTAMPTZ,
    status          VARCHAR(16) DEFAULT 'active',   -- active / deprecated / under_review
    source          VARCHAR(16) DEFAULT 'manual',   -- manual / learned / imported
    learned_from    INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE(workspace_id, rule_keyword, target_domain)
);

CREATE INDEX idx_crw_workspace ON classification_rule_weights(workspace_id);
CREATE INDEX idx_crw_domain ON classification_rule_weights(target_domain);
CREATE INDEX idx_crw_status ON classification_rule_weights(status);
CREATE INDEX idx_crw_weight ON classification_rule_weights(weight DESC);
```

#### 2.23.4 反馈数据集表 `feedback_datasets`

```sql
CREATE TABLE feedback_datasets (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    name            VARCHAR(256) NOT NULL,
    description     TEXT,
    dataset_type    VARCHAR(16) NOT NULL,           -- training / validation / test
    version         VARCHAR(32) NOT NULL,
    total_samples   INTEGER DEFAULT 0,
    domain_distribution JSONB,
    class_accuracy_before FLOAT,
    class_accuracy_after  FLOAT,
    status          VARCHAR(16) DEFAULT 'draft',    -- draft / ready / training / completed / archived
    used_in_learning BOOLEAN DEFAULT FALSE,
    snapshot_period_start TIMESTAMPTZ,
    snapshot_period_end   TIMESTAMPTZ,
    min_confidence_label  FLOAT DEFAULT 0.7,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  UUID REFERENCES users(id)
);

CREATE INDEX idx_fd_workspace ON feedback_datasets(workspace_id);
CREATE INDEX idx_fd_type ON feedback_datasets(dataset_type);
CREATE INDEX idx_fd_status ON feedback_datasets(status);
```

#### 2.23.5 审核员画像表 `reviewer_profiles`

```sql
CREATE TABLE reviewer_profiles (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) UNIQUE,
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    total_reviews           INTEGER DEFAULT 0,
    approved_count          INTEGER DEFAULT 0,
    rejected_count          INTEGER DEFAULT 0,
    needs_revision_count    INTEGER DEFAULT 0,
    classification_accuracy FLOAT,
    avg_confidence_variance FLOAT,
    avg_review_duration     FLOAT,
    agreement_rate          FLOAT,
    golden_sample_accuracy  FLOAT,
    domain_expertise        JSONB,                  -- {"customer": 0.9, "project": 0.7, ...}
    reviewer_level          VARCHAR(16) DEFAULT 'junior',  -- junior / senior / expert
    reviewer_weight         FLOAT DEFAULT 0.5,
    is_active               BOOLEAN DEFAULT TRUE,
    last_review_at  TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_rp_user ON reviewer_profiles(user_id);
CREATE INDEX idx_rp_workspace ON reviewer_profiles(workspace_id);
```

#### 2.23.6 规则学习日志表 `rule_learning_logs`

```sql
CREATE TABLE rule_learning_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    workspace_id    UUID NOT NULL REFERENCES workspaces(id),
    dataset_id      UUID REFERENCES feedback_datasets(id),
    trigger_source  VARCHAR(32) NOT NULL,           -- manual / scheduled / threshold
    total_rules_before  INTEGER,
    accuracy_before     FLOAT,
    rules_added         INTEGER DEFAULT 0,
    rules_updated       INTEGER DEFAULT 0,
    rules_deprecated    INTEGER DEFAULT 0,
    accuracy_after      FLOAT,
    accuracy_improvement FLOAT,
    learning_details    JSONB,
    top_new_keywords    JSONB,
    status          VARCHAR(16) DEFAULT 'running',
    error_message   TEXT,
    duration_seconds INTEGER,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by  UUID REFERENCES users(id)
);

CREATE INDEX idx_rll_workspace ON rule_learning_logs(workspace_id);
CREATE INDEX idx_rll_trigger ON rule_learning_logs(trigger_source);
CREATE INDEX idx_rll_created ON rule_learning_logs(created_at DESC);
```

### 2.24 核心表 workspace_id 扩展

为支持多租户隔离，以下核心表增加 `workspace_id` 外键列：

```sql
-- 在所有需要多租户隔离的核心表中增加 workspace_id 列
ALTER TABLE context_items ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE entities ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE relations ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE users ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE permissions ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE notifications ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE push_rules ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE push_logs ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE context_tags ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE user_entity_assignments ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE audit_logs ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE notification_settings ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE system_configs ADD COLUMN workspace_id UUID REFERENCES workspaces(id);  -- NULL=全局配置
ALTER TABLE user_settings ADD COLUMN workspace_id UUID REFERENCES workspaces(id);
ALTER TABLE config_change_logs ADD COLUMN workspace_id UUID REFERENCES workspaces(id);

-- workspace_id 索引
CREATE INDEX idx_context_items_workspace ON context_items(workspace_id);
CREATE INDEX idx_entities_workspace ON entities(workspace_id);
CREATE INDEX idx_users_workspace ON users(workspace_id);
-- ...（其他表同理）
```

**迁移策略**：首次部署时直接创建含 workspace_id 的表。已有系统的迁移分步执行：先加列允许 NULL → 填充 DEFAULT workspace → 加 NOT NULL 约束。

---

## 3. pgvector 向量存储方案

### 3.1 向量模型选择

采用 BGE-M3 本地部署（1024维）作为嵌入模型。

BGE-M3 本地部署优势：免费、隐私数据不出境、中文效果好；部署要求：首次加载约需 2-4GB 显存/内存。

### 3.2 向量索引策略

| 数据量级 | 索引类型 | 参数 | 说明 |
|---------|---------|------|------|
| <10万条 | IVFFlat | lists=100 | 当前推荐，构建快 |
| 10万-100万条 | HNSW | m=16, ef_construction=200 | 高召回率+高性能 |
| >100万条 | 分区分表 | 按domain分区 | 水平扩展 |

### 3.3 向量检索参数

```sql
-- 语义相似度检索示例
SELECT 
    id, title, 
    1 - (content_vector <=> query_embedding) AS similarity
FROM context_items
WHERE lifecycle_status = 'active'
    AND is_deleted = FALSE
ORDER BY content_vector <=> query_embedding
LIMIT 20;
```

**检索融合权重**（在应用层计算）：
```python
final_score = bm25_score * 0.3 + vector_similarity * 0.4 + graph_boost * 0.3
```

---

## 4. 数据库索引策略总览

| 表 | 索引 | 类型 | 用途 |
|----|------|------|------|
| context_items | domain | B-tree | 按域筛选 |
| context_items | lifecycle_status | B-tree | 按状态筛选 |
| context_items | confidence_level | B-tree | 可信度过滤 |
| context_items | created_at DESC | B-tree | 时间排序 |
| context_items | content_vector | IVFFlat | 向量相似度 |
| context_items | title+content | GIN (FTS) | 全文搜索BM25 |
| context_items | content_hash | B-tree | 去重检测 |
| entities | name+type | Unique | 实体唯一性 |
| entities | name gin_trgm | GIN trigram | 实体模糊搜索 |
| relations | source_id+target_id+relation_type | Unique | 关系去重 |
| relations | source_id/target_id | B-tree | 图谱遍历 |
| permissions | context_id | B-tree | 权限查询 |
| audit_logs | created_at DESC | B-tree | 审计时间线 |
| system_configs | section | B-tree | 按分组查询配置 |
| system_configs | section+config_key | Unique | 配置键唯一性 |
| user_settings | user_id | B-tree | 按用户查询设置 |
| user_settings | section | B-tree | 按分组查询设置 |
| config_change_logs | section | B-tree | 按分组查询变更日志 |
| config_change_logs | created_at DESC | B-tree | 变更时间线 |
| workspaces | slug | Unique | 工作区标识唯一性 |
| workspaces | status | B-tree | 按状态筛选 |
| api_keys | workspace_id | B-tree | 按工作区查询API Key |
| api_keys | key_hash | B-tree | API Key查找 |
| jwt_configs | workspace_id | Unique | 每个工作区一套JWT配置 |
| webhook_delivery_logs | workspace_id | B-tree | 按工作区查询 |
| webhook_delivery_logs | event_id | B-tree | 按事件ID查询 |
| webhook_delivery_logs | created_at DESC | B-tree | 发送时间线 |
| context_items | workspace_id | B-tree | 多租户数据隔离 |
| entities | workspace_id | B-tree | 多租户数据隔离 |
| users | workspace_id | B-tree | 多租户用户隔离 |

---

## 5. 生命周期状态映射

| 英文枚举值 | 中文名称 | 含义 | Agent可用 | 
|-----------|---------|------|----------|
| pending_review | 待验证 | 新创建，等待人工审核 | 否 |
| active | 活跃 | 已验证，可被Agent引用 | 是 |
| decaying | 衰减 | 超过6个月未更新，置信度降 | 是（带警告） |
| needs_update | 待更新 | 触发更新条件（如财报到期） | 是（带警告） |
| superseded | 被替代 | 被新版本取代，指向新版 | 否（自动跳转新版） |
| contradicted | 矛盾 | 与其他上下文冲突，暂停引用 | 否 |
| archived | 归档 | 项目结束+满2年，仅审计查询 | 否 |

---

## 6. 数据迁移与版本管理

### 5.1 迁移工具

使用 Alembic 进行数据库版本管理：

```
alembic/
├── versions/
│   ├── 001_initial_schema.py      # 初始建表
│   ├── 002_add_push_rules.py      # 推送规则表
│   └── ...
├── env.py
└── alembic.ini
```

### 5.2 数据迁移策略

- **开发阶段**：Alembic自动迁移，允许重建
- **生产阶段**：前向兼容迁移（add column优先于drop column），可回滚
- **大表变更**：使用 `CREATE INDEX CONCURRENTLY` 避免锁表

---

## 7. 备份与恢复策略

| 策略 | 频率 | 工具 | 保留期 |
|------|------|------|--------|
| 全量备份 | 每日凌晨2点 | pg_dump | 30天 |
| WAL归档 | 持续 | pg_receivewal | 7天 |
| 异地备份 | 每日 | iCloud同步dump文件 | 30天 |
| 向量索引重建 | 按需 | REINDEX CONCURRENTLY | - |

**恢复目标**：RPO < 1小时（WAL），RTO < 4小时（全量+WAL恢复）

---


4. **[已决策] 多租户隔离**：不需要，无外部用户访问。权限通过应用层 permissions 表 + user_entity_assignments 控制即可。
