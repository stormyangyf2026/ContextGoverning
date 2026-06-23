[08_configuration_management.md](https://github.com/user-attachments/files/29242071/08_configuration_management.md)
# 统一上下文管理中心 — 配置管理详细设计 v1.0

> 设计阶段：生产级详细设计 | 用途：开发人员可据此直接编写代码，无需额外设计决策


---

## 1. 配置管理架构概览

### 1.1 三层配置体系

```
┌─────────────────────────────────────────────────────────────────┐
│                    配置管理三层架构                                │
│                                                                 │
│  Layer 1: 系统级配置（管理员统一管理）                              │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 管理入口: /admin/config                                     │  │
│  │ 存储: system_config 表                                      │  │
│  │ 权限: admin 角色可读写，其他角色只读                          │  │
│  │ 生效: 实时生效（config_service 内存缓存 + Redis 广播失效）    │  │
│  │ 分类: 可信度引擎 / 采集管道 / 检索参数 / LLM / 通知 / 安全   │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Layer 2: 用户级配置（用户自行配置）                               │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 管理入口: 用户端 /notifications 设置弹窗 + /workspace 设置    │  │
│  │                  管理端 /admin/users 用户编辑弹窗            │  │
│  │ 存储: user_settings 表                                      │  │
│  │ 权限: 用户可配置自己的设置，admin 可配置他人                   │  │
│  │ 分类: 通知偏好 / 搜索偏好 / 界面偏好                          │  │
│  └───────────────────────────────────────────────────────────┘  │
│                                                                 │
│  Layer 3: 环境变量（部署时配置，运行时只读）                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │ 管理入口: .env 文件（不在Web UI中管理）                      │  │
│  │ 存储: .env + Docker环境变量                                  │  │
│  │ 权限: 仅部署运维人员可修改                                   │  │
│  │ 分类: 数据库连接 / API密钥 / 服务端口 / 部署模式              │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 1.2 ConfigService 架构

```python
# backend/app/services/config_service.py
# 配置服务：统一管理三层配置的读取、写入、缓存、变更通知

class ConfigService:
    """
    配置服务单例。通过 FastAPI 依赖注入使用。
    
    职责：
    - 系统级配置的 CRUD + 缓存管理
    - 用户级配置的 CRUD + 缓存管理
    - 环境变量读取（只读）
    - 配置变更时的 WebSocket 广播通知
    - 配置热重载（无需重启服务）
    """

    def __init__(self, redis_client=None, ws_manager=None):
        self._redis = redis_client
        self._ws_manager = ws_manager  # WebSocket 管理器，用于广播变更
        self._system_cache: dict[str, Any] = {}  # 系统配置内存缓存
        self._user_cache: dict[str, dict] = {}    # 用户配置内存缓存
        self._cache_ttl: int = 60  # 缓存TTL秒，到期从DB刷新

    # -------- 系统配置 --------
    async def get_system_config(self, section: str) -> dict:
        """获取指定分组的系统配置。先从缓存读，缓存未命中查DB。"""

    async def get_all_system_configs(self) -> dict[str, dict]:
        """获取全部系统配置（管理端配置页面用）。"""

    async def update_system_config(self, section: str, key: str, value: Any) -> None:
        """更新单个系统配置项。写DB → 清缓存 → WebSocket广播变更。"""

    async def batch_update_system_config(self, section: str, updates: dict) -> None:
        """批量更新某分组下的多个配置项。"""

    async def reset_system_config_to_default(self, section: str = None) -> None:
        """重置为默认值。section=None 时重置全部。"""

    # -------- 用户配置 --------
    async def get_user_settings(self, user_id: UUID) -> dict:
        """获取指定用户的全部设置。"""

    async def update_user_setting(self, user_id: UUID, key: str, value: Any) -> None:
        """更新用户单个设置项。"""

    async def batch_update_user_settings(self, user_id: UUID, settings: dict) -> None:
        """批量更新用户设置。"""

    # -------- 环境变量 --------
    @staticmethod
    def get_env(key: str, default: Any = None) -> str:
        """读取环境变量（只读）。"""

    @staticmethod
    def get_all_env_descriptions() -> dict:
        """返回所有环境变量的说明文档（供管理端展示参考）。"""

    # -------- 缓存管理 --------
    async def invalidate_system_cache(self, section: str = None):
        """使系统配置缓存失效。section=None 时清空全部。"""

    async def invalidate_user_cache(self, user_id: UUID):
        """使用户配置缓存失效。"""

    # -------- 变更广播 --------
    async def broadcast_config_change(self, section: str, changes: dict):
        """通过WebSocket向管理端广播配置变更事件。"""
```

---

## 2. 系统级配置参数完整清单

### 2.1 可信度引擎参数 (section: `confidence_engine`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `decay_start_months` | int | 6 | 时效衰减起始月数。上下文最后更新后超过此月数，开始应用衰减。 | 整数，1-60 | `6`（即6个月后开始衰减） |
| `decay_rate_per_month` | float | 0.03 | 时效衰减率。超过衰减起始月数后，每过一个月 confidence_score 降低的量。 | 浮点数，0.0-1.0，建议0.01-0.10 | `0.03`（每月降0.03分） |
| `min_score_after_decay` | float | 0.20 | 衰减后最低分数。即使无限时间衰减，分数也不会低于此值。 | 浮点数，0.0-1.0，必须 < 最低初始分数 | `0.20`（最低不会因衰减降到0.20以下） |
| `corroboration_weight_cap` | float | 0.15 | 单次多源印证的提权上限。新来源对已有条目提权的权重最大值。 | 浮点数，0.0-1.0，建议0.05-0.30 | `0.15`（单次最多提权15%） |
| `max_corroboration_boost` | float | 0.45 | 多源印证总提权上限。无论多少源印证，总提权不超过此值。 | 浮点数，0.0-1.0，必须 > corroboration_weight_cap | `0.45`（最多提权45%，L2最多到L5） |
| `conflict_penalty` | float | 0.10 | 矛盾惩罚值。标记矛盾时双方分数各减此值。 | 浮点数，0.0-1.0，建议0.05-0.20 | `0.10`（矛盾双方各扣0.10分） |
| `semantic_similarity_threshold` | float | 0.85 | 语义去重相似度阈值。Memory.md导入或采集管道中，新内容与已有内容向量相似度超过此值视为重复。 | 浮点数，0.0-1.0，建议0.75-0.95 | `0.85`（相似度>85%视为重复） |
| `corroboration_similarity_threshold` | float | 0.70 | 多源印证判定阈值。两个来源的内容向量相似度超过此值，视为同一主题/属性，可触发多源印证。 | 浮点数，0.0-1.0，必须 < semantic_similarity_threshold | `0.70`（相似度>70%可触发印证） |
| `manual_override_immunity_days` | int | 30 | 手动调级免疫天数。管理员手动调整可信度后，此天数内不触发自动衰减。 | 整数，0-365 | `30`（手动调级后30天内免疫自动衰减） |
| `confidence_corroboration_decay_type_count` | int | 2 | 同类型来源重复印证递减阈值。同一来源类型印证超过此次数后，权重减半。 | 整数，1-10 | `2`（第3次同类型印证开始权重减半） |

**使用说明**：
- 衰减起始月数设置得越小，上下文越容易降级，系统对新鲜度越敏感。建议结合团队更新频率调整。
- 衰减率设置为0.03时，每年衰减约0.36分，足以让L4(0.90)在2年未更新后降至L0。
- 印证总提权上限0.45是让最低的L2(0.60)能在大量印证后达到L5的保证。

**修改影响**：修改后立即生效，新入库上下文使用新参数；已有上下文的衰减计算在下次定时任务中按新参数重新计算。

---

### 2.2 初始可信度映射 (section: `confidence_mapping`)

此分组包含16条来源类型到初始可信度的映射规则，每条规则为一个配置项。

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `map.contract.level` | str | L5 | 合同/协议的初始可信度等级 | L0/L1/L2/L3/L4/L5 | `L5` |
| `map.contract.score` | float | 0.98 | 合同/协议的初始可信度分数 | 浮点数，0.0-1.0 | `0.98` |
| `map.official_doc.level` | str | L5 | 官方发布文档（年报/公告/政府文件）的初始可信度等级 | L0-L5 | `L5` |
| `map.official_doc.score` | float | 0.97 | 官方发布文档的初始可信度分数 | 0.0-1.0 | `0.97` |
| `map.expert_verified.level` | str | L4 | 专家人工验证后确认的初始可信度等级 | L0-L5 | `L4` |
| `map.expert_verified.score` | float | 0.93 | 专家人工验证后确认的初始可信度分数 | 0.0-1.0 | `0.93` |
| `map.financial_report.level` | str | L4 | 正式财报/审计报告的初始可信度等级 | L0-L5 | `L4` |
| `map.financial_report.score` | float | 0.92 | 正式财报/审计报告的初始可信度分数 | 0.0-1.0 | `0.92` |
| `map.meeting_minutes.level` | str | L4 | 正式会议纪要的初始可信度等级 | L0-L5 | `L4` |
| `map.meeting_minutes.score` | float | 0.90 | 正式会议纪要的初始可信度分数 | 0.0-1.0 | `0.90` |
| `map.email.level` | str | L4 | 正式邮件往来的初始可信度等级 | L0-L5 | `L4` |
| `map.email.score` | float | 0.88 | 正式邮件往来的初始可信度分数 | 0.0-1.0 | `0.88` |
| `map.project_kb.level` | str | L3 | 项目知识库导入的初始可信度等级 | L0-L5 | `L3` |
| `map.project_kb.score` | float | 0.78 | 项目知识库导入的初始可信度分数 | 0.0-1.0 | `0.78` |
| `map.ai_extract_verified.level` | str | L3 | AI提取经人工审核通过的初始可信度等级 | L0-L5 | `L3` |
| `map.ai_extract_verified.score` | float | 0.78 | AI提取经人工审核通过的初始可信度分数 | 0.0-1.0 | `0.78` |
| `map.manual_entry.level` | str | L3 | 人工手动录入的初始可信度等级 | L0-L5 | `L3` |
| `map.manual_entry.score` | float | 0.75 | 人工手动录入的初始可信度分数 | 0.0-1.0 | `0.75` |
| `map.memory_md.level` | str | L2 | Memory.md导入的初始可信度等级 | L0-L5 | `L2` |
| `map.memory_md.score` | float | 0.65 | Memory.md导入的初始可信度分数 | 0.0-1.0 | `0.65` |
| `map.ai_extract.level` | str | L2 | AI自动提取未审核的初始可信度等级 | L0-L5 | `L2` |
| `map.ai_extract.score` | float | 0.60 | AI自动提取未审核的初始可信度分数 | 0.0-1.0 | `0.60` |
| `map.web_scrape.level` | str | L2 | 网页抓取的初始可信度等级 | L0-L5 | `L2` |
| `map.web_scrape.score` | float | 0.55 | 网页抓取的初始可信度分数 | 0.0-1.0 | `0.55` |
| `map.verbal.level` | str | L1 | 口述/非正式沟通的初始可信度等级 | L0-L5 | `L1` |
| `map.verbal.score` | float | 0.40 | 口述/非正式沟通的初始可信度分数 | 0.0-1.0 | `0.40` |
| `map.unknown.level` | str | L1 | 未知来源的初始可信度等级 | L0-L5 | `L1` |
| `map.unknown.score` | float | 0.40 | 未知来源的初始可信度分数 | 0.0-1.0 | `0.40` |
| `map.competitor_rumor.level` | str | L1 | 竞品传闻的初始可信度等级 | L0-L5 | `L1` |
| `map.competitor_rumor.score` | float | 0.35 | 竞品传闻的初始可信度分数 | 0.0-1.0 | `0.35` |
| `map.lesson_learned.level` | str | L3 | 经验教训（来自Memory.md Lessons Learned模板或Agent反思回写）的初始可信度等级 | L0-L5 | `L3` |
| `map.lesson_learned.score` | float | 0.78 | 经验教训的初始可信度分数（含结构化解决方案，Agent检索时优先展示） | 0.0-1.0 | `0.78` |

**使用说明**：
- 每组(level, score)必须满足一致性：score 必须在 level 对应的区间内（L5:[0.95,1.0], L4:[0.85,0.95), L3:[0.70,0.85), L2:[0.50,0.70), L1:[0.30,0.50), L0:[0.00,0.30)）
- 修改后新采集的上下文使用新映射，已有上下文的初始可信度不变
- **不允许删除**已有的来源类型映射（只能修改 level 和 score）

---

### 2.3 采集管道参数 (section: `ingestion`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `source.project_kb.enabled` | bool | true | 是否启用项目知识库采集 | true/false | `true` |
| `source.project_kb.interval_hours` | int | 24 | 项目知识库采集间隔（小时）。全量同步间隔。 | 整数，1-168（1小时-1周） | `24`（每24小时同步一次） |
| `source.project_kb.priority` | str | P0 | 项目知识库采集优先级 | P0/P1/P2 | `P0` |
| `source.project_kb.platforms` | list[str] | ["ima","feishu_drive"] | 支持的项目知识库平台列表 | ima/feishu_drive/other_drive 的任意组合 | `["ima", "feishu_drive"]` |
| `source.memory_md.enabled` | bool | true | 是否启用 Memory.md 文件监听导入 | true/false | `true` |
| `source.memory_md.scan_interval_hours` | int | 1 | Memory.md 定时扫描间隔（小时）。watchdog实时监听不受此影响。 | 整数，1-24 | `1`（每小时定时扫描一次） |
| `source.memory_md.watch_paths` | list[str] | [".codebuddy/memory/"] | Memory.md 监听目录路径列表 | 有效的目录路径 | `[".codebuddy/memory/", "docs/memory/"]` |
| `source.memory_md.priority` | str | P1 | Memory.md 导入优先级 | P0/P1/P2 | `P1` |
| `source.feishu_doc.enabled` | bool | false | 是否启用飞书文档采集 | true/false | `false`（默认关闭，需手动开启） |
| `source.feishu_doc.interval_hours` | int | 1 | 飞书文档采集间隔（小时） | 整数，1-24 | `1`（每小时增量拉取） |
| `source.feishu_doc.priority` | str | P1 | 飞书文档采集优先级 | P0/P1/P2 | `P1` |
| `source.feishu_group.enabled` | bool | false | 是否启用飞书群消息采集 | true/false | `false` |
| `source.feishu_group.keywords` | list[str] | [] | 飞书群消息采集关键词。命中关键词的消息才被采集。 | 每项为非空字符串 | `["风险", "里程碑", "变更", "决策"]` |
| `source.email.enabled` | bool | false | 是否启用邮件采集 | true/false | `false` |
| `source.email.interval_minutes` | int | 15 | 邮件采集间隔（分钟） | 整数，5-1440 | `15`（每15分钟检查新邮件） |
| `source.finance_api.enabled` | bool | true | 是否启用财报自动抓取 | true/false | `true` |
| `source.finance_api.schedule` | str | market_day_20:00 | 财报抓取时间表。cron表达式或预设名。 | 有效的cron表达式或预设名 | `market_day_20:00`（每个交易日20:00执行） |
| `ingestion.dedup.similarity_threshold` | float | 0.85 | 采集管道去重相似度阈值 | 0.0-1.0 | `0.85` |
| `ingestion.max_chunk_size` | int | 8000 | 大文本分块最大字符数 | 整数，1000-50000 | `8000` |
| `ingestion.max_items_per_batch` | int | 500 | 单次批量入库最大条数 | 整数，10-5000 | `500` |
| `ingestion.entity_match_threshold` | float | 0.75 | 实体模糊匹配阈值。Levenshtein距离+语义相似度的综合阈值。 | 0.0-1.0 | `0.75` |

**使用说明**：
- 启用/禁用采集源时，已有采集队列中的任务会完成当前批次后停止
- 采集间隔修改后，下一次采集按新间隔调度
- 飞书采集需要先配置飞书 API 凭证（在环境变量中）

---

### 2.4 搜索与检索参数 (section: `search`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `hybrid.bm25_weight` | float | 0.3 | BM25关键词检索在融合排序中的权重 | 0.0-1.0，三个权重之和必须=1.0 | `0.3` |
| `hybrid.vector_weight` | float | 0.4 | 向量语义检索在融合排序中的权重 | 0.0-1.0 | `0.4` |
| `hybrid.graph_weight` | float | 0.3 | 图谱关系检索在融合排序中的权重 | 0.0-1.0 | `0.3` |
| `graph.max_depth` | int | 2 | 图谱遍历最大跳数。查询实体关联时最多展开几层关系。 | 整数，1-5 | `2`（最多2跳） |
| `search.default_page_size` | int | 20 | 搜索结果默认每页条数 | 整数，5-100 | `20` |
| `search.max_page_size` | int | 100 | 搜索结果最大每页条数。防止恶意大页请求。 | 整数，50-500 | `100` |
| `search.suggestion_max_count` | int | 5 | 搜索建议最多返回条数 | 整数，1-20 | `5` |
| `search.min_query_length` | int | 1 | 最短搜索词长度（字符数） | 整数，1-5 | `1` |
| `search.semantic_min_similarity` | float | 0.5 | 语义搜索最低相似度阈值。低于此分数的结果不返回。 | 0.0-1.0 | `0.5` |
| `search.timeout_seconds` | int | 10 | 搜索超时时间（秒）。超时后返回已有结果。 | 整数，1-60 | `10` |

**使用说明**：
- 三个融合权重之和必须等于 1.0，系统保存时自动校验。若需要强调语义搜索可调高 vector_weight。
- 图谱最大跳数越大，查询越慢但结果越丰富。建议保持2跳。
- 语义最低相似度设得越低，召回率越高但精确度越低。

---

### 2.5 LLM 调用参数 (section: `llm`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `llm.model` | str | deepseek-chat | LLM 模型名称 | 有效的模型名 | `deepseek-chat` |
| `llm.temperature` | float | 0.3 | LLM 温度参数。控制输出随机性。分类/抽取场景用低值(0.0-0.3)，生成场景用中值(0.5-0.7)。 | 0.0-2.0 | `0.3` |
| `llm.max_tokens` | int | 4096 | LLM 单次调用最大输出 Token 数 | 整数，256-32768 | `4096` |
| `llm.request_timeout_seconds` | int | 60 | LLM API 请求超时时间（秒） | 整数，10-300 | `60` |
| `llm.max_retries` | int | 3 | LLM 调用失败最大重试次数 | 整数，0-10 | `3` |
| `llm.retry_backoff_seconds` | int | 2 | LLM 重试退避基础间隔（秒）。每次重试间隔 = backoff * 2^retry_count | 整数，1-30 | `2`（第1次重试等2秒，第2次4秒，第3次8秒） |
| `llm.daily_token_budget` | int | 1000000 | LLM 每日 Token 预算上限。超过后暂停自动调用（人工审核除外）。 | 整数，10000-10000000 | `1000000`（100万Token/天） |
| `llm.token_budget_warning_pct` | int | 80 | Token 预算告警百分比。当日消耗达到预算的此百分比时发送告警通知。 | 整数，50-100 | `80`（消耗80%时告警） |
| `embedding.model` | str | BGE-M3 | 本地嵌入模型名称。用于向量化上下文的模型。 | 有效的模型名 | `BGE-M3` |
| `embedding.dimension` | int | 1024 | 嵌入向量维度。必须与模型输出维度一致。 | 整数，128-4096 | `1024` |
| `embedding.batch_size` | int | 32 | 嵌入批处理大小。一次批处理多少条文本。 | 整数，1-256 | `32` |

**使用说明**：
- temperature 对于分类和实体抽取场景应设为 0.0-0.3（低随机性），对于摘要生成场景可设为 0.5-0.7
- daily_token_budget 用于成本控制，达到上限后系统仍可人工审核和手动录入
- 嵌入模型切换需要重建向量索引（全量重新嵌入），操作窗口建议在低峰期

---

### 2.6 权限与安全参数 (section: `security`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `auth.access_token_ttl_minutes` | int | 30 | JWT Access Token 有效期（分钟） | 整数，5-1440 | `30`（30分钟后过期） |
| `auth.refresh_token_ttl_days` | int | 7 | JWT Refresh Token 有效期（天） | 整数，1-90 | `7`（7天后过期） |
| `auth.password_min_length` | int | 8 | 用户密码最小长度 | 整数，6-32 | `8` |
| `auth.max_login_attempts` | int | 5 | 最大登录失败次数。超过后锁定账号。 | 整数，3-20 | `5`（5次失败后锁定） |
| `auth.lockout_duration_minutes` | int | 30 | 账号锁定时长（分钟） | 整数，5-1440 | `30`（锁定30分钟） |
| `rate_limit.user_per_minute` | int | 100 | 普通用户API请求限流（次/分钟） | 整数，10-1000 | `100` |
| `rate_limit.agent_per_minute` | int | 300 | Agent API请求限流（次/分钟） | 整数，10-1000 | `300` |
| `rate_limit.admin_per_minute` | int | 50 | 管理端API请求限流（次/分钟） | 整数，10-500 | `50` |
| `permission.cache_ttl_seconds` | int | 300 | 权限检查结果缓存TTL（秒） | 整数，60-3600 | `300`（5分钟） |
| `permission.cache_max_entries` | int | 10000 | 权限缓存最大条目数 | 整数，1000-100000 | `10000` |
| `audit.retention_days` | int | 365 | 审计日志保留天数 | 整数，30-3650 | `365`（保留1年） |
| `audit.archive_retention_days` | int | 1825 | 归档上下文保留天数 | 整数，365-7300 | `1825`（保留5年） |

**使用说明**：
- Access Token TTL 设得越短越安全，但会增加刷新频率。建议30分钟。
- 限流参数按角色区分，Agent 需要更高的限流以支撑高频检索。
- 审计日志保留天数到期后自动清理，清理任务在每日凌晨执行。

---

### 2.7 生命周期参数 (section: `lifecycle`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `lifecycle.archive_after_project_end_days` | int | 730 | 项目结束后多少天归档上下文 | 整数，90-3650 | `730`（2年） |
| `lifecycle.decay_warning_days` | int | 30 | 衰减前多少天发送预警通知 | 整数，7-180 | `30`（衰减前30天提醒） |
| `lifecycle.auto_archive_enabled` | bool | true | 是否启用自动归档 | true/false | `true` |
| `lifecycle.auto_supersede_enabled` | bool | true | 是否启用自动替代检测（新版本替代旧版本） | true/false | `true` |
| `lifecycle.conflict_check_interval_hours` | int | 6 | 冲突检测定时任务间隔（小时） | 整数，1-24 | `6`（每6小时检测一次） |

**使用说明**：
- 项目结束判定依赖 `entities` 表中项目的 `metadata.end_date` 字段。
- 衰减预警通知在上下文即将衰减前发送给创建者和相关审核人。
- 自动归档将上下文从活跃索引中移除，可在审计日志中查询。

---

### 2.8 通知与推送参数 (section: `notification`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `notification.default_channels` | list[str] | ["in_app"] | 新用户默认通知渠道 | in_app/feishu_bot/email 的任意组合 | `["in_app"]` |
| `notification.max_retention_days` | int | 90 | 通知消息保留天数。超过后自动清理。 | 整数，7-365 | `90` |
| `notification.batch_send_interval_seconds` | int | 30 | 批量推送间隔（秒）。相同用户的多个通知在此间隔内合并为一条。 | 整数，10-300 | `30`（30秒内合并） |
| `notification.max_batch_size` | int | 10 | 单次合并通知最多包含条数 | 整数，1-50 | `10` |

---

### 2.9 报告与导出参数 (section: `export`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `export.max_rows_csv` | int | 10000 | CSV 导出最大行数 | 整数，100-100000 | `10000` |
| `export.max_contexts_pdf` | int | 50 | PDF 报告最多包含上下文条数 | 整数，10-500 | `50` |
| `export.graph_image_max_nodes` | int | 200 | 图谱导出图片最大节点数。超过此数降级为简化视图。 | 整数，50-1000 | `200` |
| `export.temp_file_retention_hours` | int | 24 | 导出临时文件保留时间（小时） | 整数，1-168 | `24` |

### 2.10 RLHF 反馈学习参数 (section: `rlhf`) [新增]

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `rlhf.auto_learn_enabled` | bool | true | 是否启用每周自动规则学习 | true/false | `true` |
| `rlhf.auto_learn_schedule` | string | "0 2 * * 1" | 自动学习 cron 表达式（默认周一凌晨2点） | 合法 cron 表达式 | `"0 2 * * 1"` |
| `rlhf.min_feedback_for_learning` | int | 100 | 触发学习的最小反馈数据量 | 整数，50-1000 | `100` |
| `rlhf.min_accuracy_improvement` | float | 0.02 | 自动应用学习结果的最小准确率提升（2%） | 浮点数，0.01-0.10 | `0.02` |
| `rlhf.new_keyword_min_frequency` | int | 3 | 新关键词发现的最小出现次数 | 整数，2-20 | `3` |
| `rlhf.new_keyword_tfidf_threshold` | float | 0.15 | 新关键词 TF-IDF 阈值（低于此值过滤） | 浮点数，0.05-0.50 | `0.15` |
| `rlhf.rule_weight_smooth_factor` | float | 0.3 | 规则权重更新的平滑因子（α） | 浮点数，0.1-0.5 | `0.3` |
| `rlhf.min_precision_to_keep` | float | 0.3 | 规则保留的最低精确率（低于此值废弃） | 浮点数，0.1-0.5 | `0.3` |
| `rlhf.reviewer_weight_agreement_factor` | float | 0.3 | 审核员权重中一致性因子的比重 | 浮点数，0.1-0.5 | `0.3` |
| `rlhf.reviewer_weight_golden_factor` | float | 0.3 | 审核员权重中金标准因子的比重 | 浮点数，0.1-0.5 | `0.3` |
| `rlhf.reviewer_weight_experience_factor` | float | 0.2 | 审核员权重中经验因子的比重 | 浮点数，0.1-0.3 | `0.2` |
| `rlhf.confidence_calibration_rate` | float | 0.2 | 可信度映射校准的学习率（λ） | 浮点数，0.05-0.50 | `0.2` |
| `rlhf.max_learning_runtime_seconds` | int | 300 | 单次学习的最大运行时间（秒） | 整数，60-1800 | `300` |
| `rlhf.dataset_train_test_split` | float | 0.8 | 数据集训练/测试拆分比例 | 浮点数，0.6-0.9 | `0.8` |

修改影响说明：调整 `min_accuracy_improvement` 将影响学习结果是否自动应用；降低 `new_keyword_tfidf_threshold` 会引入更多候选关键词但可能增加噪声；`confidence_calibration_rate` 过大可能导致可信度参数剧烈波动。

---

## 3. 用户级配置参数完整清单

### 3.1 通知偏好 (section: `notification_preferences`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `channels.in_app` | bool | true | 是否接收站内通知 | true/false | `true` |
| `channels.feishu_bot` | bool | false | 是否接收飞书Bot推送 | true/false | `false` |
| `channels.email` | bool | false | 是否接收邮件通知 | true/false | `false` |
| `quiet_hours.enabled` | bool | false | 是否启用免打扰时段 | true/false | `false` |
| `quiet_hours.start` | str | 22:00 | 免打扰开始时间（HH:MM格式） | 有效时间格式 HH:MM（00:00-23:59） | `22:00` |
| `quiet_hours.end` | str | 08:00 | 免打扰结束时间（HH:MM格式） | 有效时间格式 HH:MM（00:00-23:59） | `08:00` |
| `enabled_types` | list[str] | ["alert","review","update"] | 接收的通知类型。可选: alert/review/update/system | alert/review/update/system 的任意组合 | `["alert", "review"]` |

**使用说明**：
- 免打扰时段内，通知仍会创建但不会实时推送，等时段结束后批量推送
- 紧急告警（如系统故障）不受免打扰限制
- 通知类型说明：alert=重要告警（如上下文矛盾/财务变化），review=审核任务，update=上下文更新，system=系统公告

---

### 3.2 搜索偏好 (section: `search_preferences`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `search.default_view_mode` | str | card | 搜索结果默认视图模式 | card/list/timeline | `card` |
| `search.default_query_mode` | str | exact | 搜索默认查询模式 | exact/semantic/relation/timeline/contradiction | `exact` |
| `search.default_page_size` | int | 20 | 搜索结果默认每页条数 | 整数，5-100（不超过系统 max_page_size） | `20` |
| `search.default_confidence_min` | str | L0 | 搜索默认最低可信度等级 | L0/L1/L2/L3/L4/L5 | `L0`（不限） |

**使用说明**：
- 用户设置的 page_size 不能超过系统级 `search.max_page_size`
- 视图模式影响用户端搜索页的默认展示方式

---

### 3.3 界面偏好 (section: `ui_preferences`)

| 参数键 | 类型 | 默认值 | 说明 | 输入约束 | 填写样例 |
|--------|------|--------|------|---------|---------|
| `ui.language` | str | zh-CN | 界面语言 | zh-CN/en | `zh-CN` |
| `ui.timezone` | str | Asia/Shanghai | 用户时区 | 有效 IANA 时区名 | `Asia/Shanghai` |
| `ui.date_format` | str | YYYY-MM-DD | 日期显示格式 | YYYY-MM-DD/MM/DD/YYYY/DD/MM/YYYY | `YYYY-MM-DD` |
| `ui.graph_auto_expand` | bool | true | 图谱页面是否自动展开首层关联 | true/false | `true` |
| `ui.graph_animation_enabled` | bool | true | 图谱页面是否启用动画 | true/false | `true` |

**使用说明**：
- 时区影响所有时间显示（创建时间、更新时间、衰减预警等）
- 日期格式影响前端所有日期渲染

---

## 4. 环境变量完整清单（Layer 3，只读）

以下环境变量在 `.env` 文件中配置，不在 Web UI 中管理。管理端配置页面以只读方式展示这些参数供参考。

| 变量名 | 类型 | 必填 | 说明 | 样例值 |
|--------|------|------|------|--------|
| `DATABASE_URL` | str | 是 | PostgreSQL 连接字符串 | `postgresql://admin:password@localhost:5432/context_platform` |
| `DEEPSEEK_API_KEY` | str | 是 | DeepSeek API 密钥 | `sk-xxxxxxxxxxxxxxxx` |
| `DEEPSEEK_BASE_URL` | str | 否 | DeepSeek API 基础URL（默认 https://api.deepseek.com） | `https://api.deepseek.com` |
| `REDIS_URL` | str | 否 | Redis 连接字符串（不设置则使用内存LRU降级） | `redis://localhost:6379/0` |
| `QDRANT_URL` | str | 否 | Qdrant 连接字符串（Mem0 使用） | `http://localhost:6333` |
| `SECRET_KEY` | str | 是 | JWT 签名密钥（至少32字符随机字符串） | `openssl rand -hex 32 生成的值` |
| `ENVIRONMENT` | str | 是 | 运行环境 | `development` / `staging` / `production` |
| `LOG_LEVEL` | str | 否 | 日志级别（默认 INFO） | `DEBUG` / `INFO` / `WARNING` / `ERROR` |
| `CORS_ORIGINS` | str | 否 | 允许跨域的前端域名（逗号分隔） | `http://localhost:3001,http://localhost:3002` |
| `BACKEND_PORT` | int | 否 | 后端服务端口（默认 8000） | `8000` |
| `FEISHU_APP_ID` | str | 否 | 飞书应用 ID（启用飞书采集时必填） | `cli_xxxxxxxxxxxx` |
| `FEISHU_APP_SECRET` | str | 否 | 飞书应用密钥 | `xxxxxxxxxxxxxxxx` |
| `DOMAIN_NAME` | str | 否 | 域名（Phase 3 配置域名后填写，配置后自动启动HTTPS） | `context-platform.example.com` |
| `SSL_ENABLED` | bool | 否 | 是否启用 SSL（域名配置后自动设为 true） | `true` |
| `SSL_CERT_PATH` | str | 否 | SSL 证书路径（自动生成时可为空） | `/etc/letsencrypt/live/.../fullchain.pem` |
| `SSL_KEY_PATH` | str | 否 | SSL 私钥路径 | `/etc/letsencrypt/live/.../privkey.pem` |

**使用说明**：
- `.env.example` 文件包含所有变量的模板和注释，复制为 `.env` 后填写实际值
- `SECRET_KEY` 生产环境必须更换为随机字符串
- 飞书相关变量仅在启用飞书采集时需要

---

## 5. 数据库设计（配置存储）

### 5.1 系统配置表 `system_configs`

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
    is_visible      BOOLEAN NOT NULL DEFAULT TRUE,  -- 是否在管理界面显示
    sort_order      INT NOT NULL DEFAULT 0,    -- 在管理界面中的排序
    updated_by      VARCHAR(128),              -- 最后修改人
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(section, config_key)
);

CREATE INDEX idx_system_configs_section ON system_configs(section);
```

### 5.2 用户设置表 `user_settings`

```sql
CREATE TABLE user_settings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    section         VARCHAR(64) NOT NULL,      -- 设置分组: notification_preferences/search_preferences/ui_preferences
    setting_key     VARCHAR(128) NOT NULL,     -- 设置键名
    setting_value   JSONB NOT NULL,            -- 设置值
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    
    UNIQUE(user_id, section, setting_key)
);

CREATE INDEX idx_user_settings_user ON user_settings(user_id);
CREATE INDEX idx_user_settings_section ON user_settings(section);
```

### 5.3 配置变更日志表 `config_change_logs`

```sql
CREATE TABLE config_change_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_type     VARCHAR(16) NOT NULL,      -- system/user
    section         VARCHAR(64) NOT NULL,
    config_key      VARCHAR(128) NOT NULL,
    old_value       JSONB,
    new_value       JSONB NOT NULL,
    changed_by      VARCHAR(128) NOT NULL,
    change_reason   TEXT,                      -- 变更原因（可选）
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_config_logs_type ON config_change_logs(config_type);
CREATE INDEX idx_config_logs_created ON config_change_logs(created_at DESC);
```

---

## 6. API 设计

### 6.1 系统配置 API

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

**请求/响应格式**：

```json
// GET /api/v1/admin/config/confidence_engine 响应
{
    "data": {
        "section": "confidence_engine",
        "label": "可信度引擎参数",
        "description": "控制可信度引擎的算法行为，包括衰减、印证、惩罚等参数",
        "items": [
            {
                "key": "decay_start_months",
                "value": 6,
                "value_type": "number",
                "default_value": 6,
                "description": "时效衰减起始月数。上下文最后更新后超过此月数，开始应用衰减。",
                "validation": {"min": 1, "max": 60, "step": 1},
                "input_hint": "请输入1-60之间的整数，例如 6（表示6个月后开始衰减）。设置越小，系统对新鲜度越敏感。",
                "example": "6"
            }
        ]
    }
}

// PUT /api/v1/admin/config/confidence_engine 请求
{
    "items": [
        {"key": "decay_start_months", "value": 12},
        {"key": "decay_rate_per_month", "value": 0.02}
    ],
    "change_reason": "根据季度评审，将衰减起始时间延长至12个月以适应团队更新频率"
}
```

### 6.2 用户设置 API

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/v1/settings` | 获取当前用户全部设置 | 登录用户 |
| GET | `/api/v1/settings/{section}` | 获取当前用户指定分组设置 | 登录用户 |
| PUT | `/api/v1/settings/{section}` | 批量更新当前用户指定分组设置 | 登录用户 |
| PUT | `/api/v1/settings/{section}/{key}` | 更新当前用户单个设置项 | 登录用户 |
| PUT | `/api/v1/admin/users/{id}/settings/{section}` | 管理员更新指定用户设置 | admin |

---

## 7. 前端管理界面设计（配置管理页 `/admin/config`）

### 7.1 页面布局

```
┌──────────────────────────────────────────────────────────────────────┐
│ 系统配置管理                                          变更日志 [查看] │
├──────────────────────────────────────────────────────────────────────┤
│ 配置分组Tab:                                                         │
│ [可信度引擎] [初始可信度映射] [采集管道] [搜索检索] [LLM调用]       │
│ [权限安全] [生命周期] [通知推送] [导出] [环境变量(只读)]              │
├──────────────────────────────────────────────────────────────────────┤
│                                                                      │
│ ┌─ 可信度引擎参数 ────────────────────────────────────────────────┐ │
│ │                                                                    │ │
│ │ 衰减参数                                                           │ │
│ │ ┌─────────────────────────────────────────────────────────────┐  │ │
│ │ │ decay_start_months            [  6  ] ←→ 1-60               │  │ │
│ │ │ → 时效衰减起始月数。超过此月数后上下文分数开始衰减。          │  │ │
│ │ │ → 默认值: 6 | 示例: 6（表示6个月后开始衰减）                 │  │ │
│ │ │                                                               │  │ │
│ │ │ decay_rate_per_month          [ 0.03 ] ←→ 0.00-1.00          │  │ │
│ │ │ → 每月衰减量。每过一个月从 confidence_score 中扣除此值。      │  │ │
│ │ │ → 默认值: 0.03 | 示例: 0.03（每月降0.03分）                  │  │ │
│ │ │                                                               │  │ │
│ │ │ min_score_after_decay         [ 0.20 ] ←→ 0.00-1.00          │  │ │
│ │ │ → 衰减后最低分数。分数不会因衰减降到低于此值。                │  │ │
│ │ │ → 默认值: 0.20 | 示例: 0.20（最低降到0.20）                  │  │ │
│ │ └─────────────────────────────────────────────────────────────┘  │ │
│ │                                                                    │ │
│ │ 印证参数                                                           │ │
│ │ ┌─────────────────────────────────────────────────────────────┐  │ │
│ │ │ corroboration_weight_cap       [ 0.15 ]                      │  │ │
│ │ │ → 单次多源印证的最大提权权重。                               │  │ │
│ │ │ → 默认值: 0.15 | 示例: 0.15（单次最多提权15%）              │  │ │
│ │ │                                                               │  │ │
│ │ │ max_corroboration_boost        [ 0.45 ]                      │  │ │
│ │ │ → 多源印证总提权上限。无论多少源印证，总提权不超过此值。      │  │ │
│ │ │ → 默认值: 0.45 | 示例: 0.45（最多提权45%，即0.60→1.05→1.0）│  │ │
│ │ │                                                               │  │ │
│ │ │ corroboration_similarity_threshold [ 0.70 ]                  │  │ │
│ │ │ → 两个来源的向量相似度超过此值才可触发多源印证。              │  │ │
│ │ │ → 默认值: 0.70 | 示例: 0.70（相似度>70%即视为同主题）       │  │ │
│ │ └─────────────────────────────────────────────────────────────┘  │ │
│ │                                                                    │ │
│ │ 冲突参数                                                           │ │
│ │ ┌─────────────────────────────────────────────────────────────┐  │ │
│ │ │ conflict_penalty               [ 0.10 ]                      │  │ │
│ │ │ → 矛盾标记时双方分数各扣除此值。                             │  │ │
│ │ │ → 默认值: 0.10 | 示例: 0.10（矛盾双方各扣0.10分）           │  │ │
│ │ └─────────────────────────────────────────────────────────────┘  │ │
│ │                                                                    │ │
│ │ 其他参数                                                           │ │
│ │ ┌─────────────────────────────────────────────────────────────┐  │ │
│ │ │ semantic_similarity_threshold   [ 0.85 ]                     │  │ │
│ │ │ → 语义去重阈值。新内容与已有内容相似度超过此值视为重复。      │  │ │
│ │ │ → 默认值: 0.85 | 示例: 0.85（相似度>85%视为重复）           │  │ │
│ │ │                                                               │  │ │
│ │ │ manual_override_immunity_days   [ 30   ]                     │  │ │
│ │ │ → 手动调级后免疫自动衰减的天数。                             │  │ │
│ │ │ → 默认值: 30 | 示例: 30（手动调级后30天内不自动衰减）       │  │ │
│ │ │                                                               │  │ │
│ │ │ confidence_corroboration_decay_type_count [ 2 ]              │  │ │
│ │ │ → 同类型来源重复印证超过此次数后权重减半。                    │  │ │
│ │ │ → 默认值: 2 | 示例: 2（第3次同类型印证权重减半）             │  │ │
│ │ └─────────────────────────────────────────────────────────────┘  │ │
│ │                                                                    │ │
│ │                                        [保存全部] [恢复默认值]    │ │
│ └────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────┘
```

### 7.2 每个配置项的统一模板

每个配置项在管理界面中按以下结构渲染（以 `decay_start_months` 为例）：

```
┌─────────────────────────────────────────────────────────────┐
│ 配置键: decay_start_months                                   │
│ ┌───────────────────────────────────────────────────────┐   │
│ │ 参数说明: 时效衰减起始月数。上下文最后更新后超过此     │   │
│ │ 月数，开始应用衰减。设置得越小，系统对新鲜度越敏感。   │   │
│ │                                                       │   │
│ │ 输入说明: 请输入1-60之间的整数。建议值: 3-12。        │   │
│ │ 填写样例: 6（表示6个月后开始衰减）                    │   │
│ │ 默认值: 6                                            │   │
│ │ 当前值: [  12   ] (修改中)                            │   │
│ │ 修改影响: 修改后立即生效，已有上下文的衰减计算在下次    │   │
│ │          定时任务中按新参数重新计算。                   │   │
│ │                                                       │   │
│ │ 校验规则: 最小值: 1, 最大值: 60, 步长: 1, 必须为整数  │   │
│ └───────────────────────────────────────────────────────┘   │
│                                     [恢复此项默认] [×清除]  │
└─────────────────────────────────────────────────────────────┘
```

### 7.3 初始可信度映射 Tab 特殊设计

这是一个表格形式的配置，每行一条映射规则：

```
┌─ 来源类型 → 初始可信度映射 ──────────────────────────────────────────┐
│                                                                        │
│ 说明：每种来源类型的上下文在首次入库时使用此映射确定初始可信度。        │
│ 修改后仅影响新入库的上下文，已有上下文不变。                            │
│                                                                        │
│ ┌────┬──────────────────────┬──────────┬──────────┬────────┐          │
│ │ #  │ 来源类型             │ 等级     │ 分数     │ 操作    │          │
│ ├────┼──────────────────────┼──────────┼──────────┼────────┤          │
│ │ 1  │ contract             │ [ L5 ▾ ] │ [ 0.98 ] │ [重置]  │ 合同/协议 │
│ │ 2  │ official_doc         │ [ L5 ▾ ] │ [ 0.97 ] │ [重置]  │ 官方文档 │
│ │ 3  │ expert_verified      │ [ L4 ▾ ] │ [ 0.93 ] │ [重置]  │ 专家确认 │
│ │ 4  │ financial_report     │ [ L4 ▾ ] │ [ 0.92 ] │ [重置]  │ 财报     │
│ │ 5  │ meeting_minutes      │ [ L4 ▾ ] │ [ 0.90 ] │ [重置]  │ 会议纪要 │
│ │ 6  │ email                │ [ L4 ▾ ] │ [ 0.88 ] │ [重置]  │ 邮件     │
│ │ 7  │ project_kb           │ [ L3 ▾ ] │ [ 0.78 ] │ [重置]  │ 项目知识库│
│ │ 8  │ ai_extract_verified  │ [ L3 ▾ ] │ [ 0.78 ] │ [重置]  │ AI提取验证│
│ │ 9  │ manual_entry         │ [ L3 ▾ ] │ [ 0.75 ] │ [重置]  │ 人工录入 │
│ │ 10 │ memory_md            │ [ L2 ▾ ] │ [ 0.65 ] │ [重置]  │ Memory.md│
│ │ 11 │ ai_extract           │ [ L2 ▾ ] │ [ 0.60 ] │ [重置]  │ AI提取   │
│ │ 12 │ web_scrape           │ [ L2 ▾ ] │ [ 0.55 ] │ [重置]  │ 网页抓取 │
│ │ 13 │ verbal               │ [ L1 ▾ ] │ [ 0.40 ] │ [重置]  │ 口述     │
│ │ 14 │ unknown              │ [ L1 ▾ ] │ [ 0.40 ] │ [重置]  │ 未知来源 │
│ │ 15 │ competitor_rumor     │ [ L1 ▾ ] │ [ 0.35 ] │ [重置]  │ 竞品传闻 │
│ └────┴──────────────────────┴──────────┴──────────┴────────┘          │
│                                                                        │
│ 校验提示：若等级与分数不一致（如 L5 等级但分数<0.95），保存时提示错误。│
│                                                                        │
│                                                [保存全部] [恢复默认值] │
└────────────────────────────────────────────────────────────────────────┘
```

### 7.4 采集管道 Tab

```
┌─ 采集源配置 ──────────────────────────────────────────────────────────┐
│                                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ 项目知识库 (project_kb)                          [✓ 启用] [配置] │   │
│ │ → 采集间隔: [ 24 ▾ ] 小时                                        │   │
│ │ → 优先级: [ P0 ▾ ]                                               │   │
│ │ → 支持平台: [☑ ima] [☑ feishu_drive] [☐ other_drive]            │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ Memory.md 导入 (memory_md)                       [✓ 启用] [配置] │   │
│ │ → 定时扫描间隔: [ 1 ▾ ] 小时                                     │   │
│ │ → 监听目录: [ .codebuddy/memory/        ] [+添加路径]            │   │
│ │ → 优先级: [ P1 ▾ ]                                               │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ 飞书文档 (feishu_doc)                           [☐ 启用] [配置]  │   │
│ │ → 采集间隔: [ 1 ▾ ] 小时                                         │   │
│ │ → 优先级: [ P1 ▾ ]                                               │   │
│ │ → 需要飞书 API 凭证（见环境变量）                                  │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ 飞书群消息 (feishu_group)                       [☐ 启用] [配置]  │   │
│ │ → 关键词过滤: [风险] [里程碑] [变更] [决策] [+添加]              │   │
│ │ → 仅采集命中关键词的消息                                          │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ 邮件采集 (email)                                [☐ 启用] [配置]  │   │
│ │ → 检查间隔: [ 15 ▾ ] 分钟                                        │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ 财报抓取 (finance_api)                          [✓ 启用] [配置]  │   │
│ │ → 执行时间: [ market_day_20:00 ▾ ]                                │   │
│ │ → 每个交易日20:00自动抓取上市客户财务数据                          │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│ 管道通用参数:                                                          │
│ ┌─────────────────────────────────────────────────────────────────┐   │
│ │ 去重相似度阈值: [ 0.85 ]  (0.0-1.0)                               │   │
│ │ → 新内容与已有内容向量相似度超过此值视为重复，跳过入库              │   │
│ │ → 默认值: 0.85 | 示例: 0.85                                      │   │
│ │                                                                   │   │
│ │ 大文本分块大小: [ 8000 ] 字符 (1000-50000)                         │   │
│ │ → 超过此长度的上下文自动分块，每块独立向量化但共享同一 context_id   │   │
│ │ → 默认值: 8000 | 示例: 8000                                      │   │
│ │                                                                   │   │
│ │ 单次批量入库上限: [ 500 ] 条 (10-5000)                             │   │
│ │ → 单次采集管道处理的最大条数，超过的分批处理                        │   │
│ │ → 默认值: 500 | 示例: 500                                        │   │
│ │                                                                   │   │
│ │ 实体匹配阈值: [ 0.75 ]  (0.0-1.0)                                  │   │
│ │ → Memory.md导入时与现有实体匹配的相似度阈值                         │   │
│ │ → 默认值: 0.75 | 示例: 0.75（相似度>75%视为同一实体）             │   │
│ └─────────────────────────────────────────────────────────────────┘   │
│                                                                        │
│                                                [保存全部] [恢复默认值] │
└────────────────────────────────────────────────────────────────────────┘
```

### 7.5 管理端配置页面交互规范

```typescript
// 配置页面状态管理
interface ConfigPageState {
  activeTab: ConfigSection;  // 当前激活的配置分组Tab
  configs: Record<ConfigSection, ConfigItem[]>;  // 所有配置项
  originalConfigs: Record<ConfigSection, ConfigItem[]>;  // 原始值（用于检测修改）
  isDirty: Record<ConfigSection, boolean>;  // 每个Tab是否有未保存修改
  isSaving: boolean;
  validationErrors: Record<string, string>;  // key → 校验错误信息
  changeReason: string;  // 变更原因（批量保存时必填）
  showChangeReasonDialog: boolean;  // 是否显示变更原因弹窗
}

// 保存操作
const handleSave = async (section: ConfigSection) => {
  // 1. 前端校验
  const errors = validateConfigItems(configs[section]);
  if (Object.keys(errors).length > 0) {
    setValidationErrors(errors);
    toast.error('存在校验错误，请修正后保存');
    return;
  }

  // 2. 显示变更原因弹窗
  setShowChangeReasonDialog(true);
};

const confirmSave = async () => {
  setIsSaving(true);
  try {
    // 计算变更项
    const changes = getChanges(originalConfigs[activeTab], configs[activeTab]);
    
    await api.put(`/api/v1/admin/config/${activeTab}`, {
      items: changes,
      change_reason: changeReason,
    });
    
    toast.success(`配置已保存（${changes.length} 项变更）`);
    setOriginalConfigs(activeTab, cloneDeep(configs[activeTab]));
    setIsDirty(activeTab, false);
  } catch (err) {
    toast.error(`保存失败: ${err.message}`);
  } finally {
    setIsSaving(false);
    setShowChangeReasonDialog(false);
  }
};

// 重置默认值（二次确认）
const handleReset = async (section: ConfigSection) => {
  // 弹出 AlertDialog 二次确认
  // 确认后调用 POST /api/v1/admin/config/{section}/reset
  // 重置成功后刷新当前Tab配置
};

// 单个配置项恢复默认
const handleResetItem = (section: ConfigSection, key: string) => {
  const item = configs[section].find(c => c.key === key);
  if (item) {
    updateConfigValue(section, key, item.default_value);
    toast.success(`${key} 已恢复默认值`);
  }
};

// 离开页面未保存提示
// 使用 useEffect + beforeunload 事件
```

---

## 8. 用户端配置入口设计

### 8.1 通知设置弹窗（已存在于 §2.5.3，此处扩展）

在用户端 `/notifications` 页面右上角「设置⚙」按钮，点击打开配置弹窗：

```
┌──────────────────────────────────────────────────┐
│ 通知设置                                    [×关闭]│
├──────────────────────────────────────────────────┤
│                                                   │
│ 推送渠道                                           │
│ ┌───────────────────────────────────────────────┐ │
│ │ [✓] 站内通知 — 在通知中心接收通知               │ │
│ │ [☐] 飞书消息 — 通过飞书Bot推送（需已绑定飞书）  │ │
│ │ [☐] 邮件通知 — 发送到注册邮箱                   │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ 接收的通知类型                                      │
│ ┌───────────────────────────────────────────────┐ │
│ │ [✓] 重要告警 — 上下文矛盾、财务指标变化等       │ │
│ │ [✓] 审核任务 — 待验证、待裁决等                │ │
│ │ [✓] 上下文更新 — 关注实体的新上下文入库         │ │
│ │ [☐] 系统公告 — 系统维护、版本更新等            │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ 免打扰时段                                          │
│ ┌───────────────────────────────────────────────┐ │
│ │ [✓] 启用免打扰                                 │ │
│ │ 从 [ 22:00 ] 至 [ 08:00 ]                     │ │
│ │ → 此时段内通知仍会创建，但不会实时推送          │ │
│ │ → 紧急告警（系统故障等）不受此限                │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│                              [取消]  [保存设置]    │
└──────────────────────────────────────────────────┘
```

### 8.2 搜索偏好设置（新增入口）

在用户端 `/search` 页面，搜索栏右侧增加一个偏好设置图标按钮：

```
搜索偏好弹窗：
┌──────────────────────────────────────────────────┐
│ 搜索偏好                                     [×关闭]│
├──────────────────────────────────────────────────┤
│                                                   │
│ 默认视图模式                                        │
│ ┌───────────────────────────────────────────────┐ │
│ │ (●) 卡片视图  ( ) 列表视图  ( ) 时间线视图     │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ 默认查询模式                                        │
│ ┌───────────────────────────────────────────────┐ │
│ │ (●) 精确查询 — 按关键词精确匹配                 │ │
│ │ ( ) 语义查询 — 按语义相似度匹配                 │ │
│ │ ( ) 关联查询 — 按知识图谱关系检索               │ │
│ │ ( ) 时间线查询 — 按时间序列检索                 │ │
│ │ ( ) 矛盾查询 — 检索存在矛盾的上下文             │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ 默认每页条数                                        │
│ ┌───────────────────────────────────────────────┐ │
│ │ [ 20 ▾ ] 条/页  (5-100)                        │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ 默认最低可信度                                      │
│ ┌───────────────────────────────────────────────┐ │
│ │ [ 不限(L0) ▾ ]                                 │ │
│ │ → 搜索结果仅显示不低于此等级的上下文             │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│                              [取消]  [保存设置]    │
└──────────────────────────────────────────────────┘
```

### 8.3 界面偏好设置（新增入口）

在用户端右上角用户头像下拉菜单中增加「偏好设置」入口：

```
界面偏好弹窗：
┌──────────────────────────────────────────────────┐
│ 界面偏好                                     [×关闭]│
├──────────────────────────────────────────────────┤
│                                                   │
│ 语言                                               │
│ ┌───────────────────────────────────────────────┐ │
│ │ [ 中文(简体) ▾ ]                               │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ 时区                                               │
│ ┌───────────────────────────────────────────────┐ │
│ │ [ Asia/Shanghai (UTC+8) ▾ ]                   │ │
│ │ → 影响所有时间显示（创建时间、更新时间、衰减预警等）│
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ 日期格式                                            │
│ ┌───────────────────────────────────────────────┐ │
│ │ (●) YYYY-MM-DD  (2026-06-23)                  │ │
│ │ ( ) MM/DD/YYYY  (06/23/2026)                  │ │
│ │ ( ) DD/MM/YYYY  (23/06/2026)                  │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│ 图谱偏好                                            │
│ ┌───────────────────────────────────────────────┐ │
│ │ [✓] 自动展开首层关联（打开图谱时自动展开节点）   │ │
│ │ [✓] 启用动画效果                                │ │
│ └───────────────────────────────────────────────┘ │
│                                                   │
│                              [取消]  [保存设置]    │
└──────────────────────────────────────────────────┘
```

---

## 9. 配置热生效机制

### 9.1 生效策略

| 配置类型 | 生效方式 | 生效延迟 |
|---------|---------|---------|
| 可信度引擎参数 | ConfigService 内存缓存 → 下次调用时使用新值 | < 1秒 |
| 初始可信度映射 | 同上 | < 1秒 |
| 采集管道参数 | Prefect 定时任务读取时获取最新 | 下一个采集周期 |
| 搜索参数 | SearchService 每次查询时读取 | < 1秒 |
| LLM 参数 | LLM Client 下次调用时读取 | < 1秒 |
| 权限安全参数 | 新 Token 签发时使用新TTL；已有Token不受影响 | 新Token < 0秒；旧Token最迟30分钟 |
| 生命周期参数 | 定时任务读取时获取最新 | 下一个任务周期 |
| 通知参数 | 每次推送时读取 | < 1秒 |
| 用户设置 | 用户下次请求时读取 | < 1秒 |

### 9.2 WebSocket 广播协议

管理端保存配置后，ConfigService 通过 WebSocket 广播变更：

```typescript
// 服务端广播
ws_manager.broadcast("admin", {
  event: "config.changed",
  data: {
    section: "confidence_engine",
    changed_by: "admin_user",
    changed_at: "2026-06-23T14:30:00Z",
    changes: [
      { key: "decay_start_months", old_value: 6, new_value: 12 }
    ],
  },
});

// 管理端接收（多管理员同时在线时更新其他管理员页面）
wsClient.on("config.changed", (data) => {
  if (data.changed_by !== currentUser.username) {
    toast.info(`配置 "${data.section}" 已被 ${data.changed_by} 更新`, {
      action: { label: "刷新", onClick: () => refetchConfig(data.section) },
    });
  }
});
```

---

## 10. 配置校验规则汇总

### 10.1 通用校验

| 校验类型 | 规则 | 错误提示 |
|---------|------|---------|
| 类型校验 | 输入值类型必须与 value_type 一致 | "{key} 必须是 {type} 类型" |
| 范围校验 | 数值必须在 validation.min 和 validation.max 之间 | "{key} 必须在 {min}-{max} 之间" |
| 枚举校验 | 字符串值必须在 validation.enum 列表中 | "{key} 可选值: {enum列表}" |
| 列表校验 | 列表项必须在 validation.item_enum 列表中 | "{key} 每项可选值: {item_enum列表}" |

### 10.2 交叉校验

| 校验条件 | 错误提示 |
|---------|---------|
| `decay_rate_per_month * 36 > 0.95` | "衰减率过高：3年衰减量将超过0.95，可能导致大量上下文过快地降级到L0" |
| `corroboration_weight_cap > max_corroboration_boost` | "单次印证权重上限不能大于总印证上限" |
| `hybrid.bm25_weight + hybrid.vector_weight + hybrid.graph_weight != 1.0` | "三个检索权重之和必须等于1.0，当前和为 {sum}" |
| `map.{type}.score 不在 map.{type}.level 对应区间内` | "分数 {score} 不在等级 {level} 对应的区间内。{level} 区间: [{min}, {max}]" |
| `auth.access_token_ttl_minutes > auth.refresh_token_ttl_days * 1440` | "Access Token TTL 不能大于 Refresh Token TTL" |
| `lifecycle.decay_warning_days > confidence_engine.decay_start_months * 30` | "衰减预警天数不能大于衰减起始月数的天数" |

---

## 11. 配置默认值种子数据

```sql
-- 初始部署时自动执行的种子数据（仅当 system_configs 表为空时）
-- 此脚本位于 backend/alembic/seeds/seed_system_configs.py

-- 可信度引擎
INSERT INTO system_configs (section, config_key, config_value, value_type, default_value, validation, input_hint, sort_order) VALUES
('confidence_engine', 'decay_start_months', '6', 'number', '6', '{"min":1,"max":60,"step":1}', '请输入1-60之间的整数，例如 6（表示6个月后开始衰减）。设置越小，系统对新鲜度越敏感。建议值: 3-12。', 1),
('confidence_engine', 'decay_rate_per_month', '0.03', 'number', '0.03', '{"min":0.0,"max":1.0,"step":0.01}', '请输入0.0-1.0之间的数，例如 0.03（每月降0.03分）。建议值: 0.01-0.10。', 2),
('confidence_engine', 'min_score_after_decay', '0.20', 'number', '0.20', '{"min":0.0,"max":1.0,"step":0.01}', '请输入0.0-1.0之间的数，例如 0.20（分数不会因衰减降到低于此值）。必须小于最低初始分数(0.35)。', 3),
('confidence_engine', 'corroboration_weight_cap', '0.15', 'number', '0.15', '{"min":0.0,"max":1.0,"step":0.01}', '请输入0.0-1.0之间的数，例如 0.15（单次最多提权15%）。建议值: 0.05-0.30。', 4),
('confidence_engine', 'max_corroboration_boost', '0.45', 'number', '0.45', '{"min":0.0,"max":1.0,"step":0.01}', '请输入0.0-1.0之间的数，例如 0.45（最多提权45%）。必须大于 corroboration_weight_cap。', 5),
('confidence_engine', 'conflict_penalty', '0.10', 'number', '0.10', '{"min":0.0,"max":1.0,"step":0.01}', '请输入0.0-1.0之间的数，例如 0.10（矛盾双方各扣0.10分）。建议值: 0.05-0.20。', 6),
('confidence_engine', 'semantic_similarity_threshold', '0.85', 'number', '0.85', '{"min":0.0,"max":1.0,"step":0.01}', '请输入0.0-1.0之间的数，例如 0.85（相似度>85%视为重复跳过入库）。建议值: 0.75-0.95。', 7),
('confidence_engine', 'corroboration_similarity_threshold', '0.70', 'number', '0.70', '{"min":0.0,"max":1.0,"step":0.01}', '请输入0.0-1.0之间的数，例如 0.70（相似度>70%即可触发多源印证）。必须小于 semantic_similarity_threshold。', 8),
('confidence_engine', 'manual_override_immunity_days', '30', 'number', '30', '{"min":0,"max":365,"step":1}', '请输入0-365之间的整数，例如 30（手动调级后30天内不自动衰减）。', 9),
('confidence_engine', 'confidence_corroboration_decay_type_count', '2', 'number', '2', '{"min":1,"max":10,"step":1}', '请输入1-10之间的整数，例如 2（第3次同类型印证权重减半）。', 10);

-- ...（其余分组的种子数据同理，此处省略重复模式）
```

---

## 12. 与传统配置文件的关系

项目同时支持通过 YAML/JSON 配置文件加载配置作为后备方案（开发和离线环境）：

```yaml
# backend/config/defaults.yaml
# 此文件定义系统默认值，与数据库种子数据保持一致
# 当数据库不可用时（如首次启动），ConfigService 从此文件加载

confidence_engine:
  decay_start_months: 6
  decay_rate_per_month: 0.03
  min_score_after_decay: 0.20
  # ...

# 环境变量覆盖
# 优先级: 数据库 > 环境变量 > config/defaults.yaml
# 可通过环境变量 CONFIG_OVERRIDE_PATH 指定自定义配置文件路径
```

**加载优先级**：
1. 数据库中 `system_configs` 表的值（最高优先级，管理员在Web UI修改的值）
2. 环境变量（`.env` 文件）
3. `config/defaults.yaml` 文件中的默认值（最低优先级，兜底）

---

## 13. 作为父产品子组件时的配置

当本产品（统一上下文管理中心）作为更大父产品的一个子组件部署时，父产品的运维人员需要创建一个集成配置文件来描述本产品如何接入父产品体系。本章定义该配置文件的结构、命名规范、各配置节点的含义和填写说明，并提供完整的填写样例。

### 13.1 配置文件概述

配置文件名为 `context-platform.yaml`，放置于父产品部署目录的 `config/integrations/` 子目录下。本产品在启动时会读取此文件完成与父产品的对接。

配置文件的作用是将本产品注册到父产品的生态中，包括：本产品的网络地址和端口、对父产品的认证方式（本产品验证来自父产品的请求）、父产品对本产品的认证方式（父产品调用本产品 API 时使用的凭证）、UI 嵌入外观偏好、功能开关、资源配额等。

配置文件使用 YAML 格式，结构分为 6 个顶层节点：`platform`（本产品基本信息）、`network`（网络与地址）、`auth`（双向认证）、`ui`（UI 嵌入外观）、`features`（功能开关）、`quotas`（资源配额）。

### 13.2 配置节点完整清单

#### 13.2.1 platform — 本产品基本信息

| 节点路径 | 类型 | 必填 | 说明 | 填写样例 |
|---------|------|------|------|---------|
| `platform.name` | string | 是 | 本产品在父产品体系中的显示名称，会出现在父产品的子组件管理列表和菜单中。建议使用简洁的中文名称。长度不超过 32 字符。 | `上下文管理中心` |
| `platform.slug` | string | 是 | 唯一标识符，用于父产品内部路由和 API 路径命名空间。仅允许小写字母、数字和连字符，长度不超过 64 字符。一旦设置不建议修改，因为会影响已有的 API 路由和数据库记录。 | `context-platform` |
| `platform.version` | string | 是 | 本产品当前部署的版本号，用于父产品检查兼容性和版本升级提醒。遵循语义化版本号格式。 | `1.0.0` |
| `platform.description` | string | 否 | 简要描述本产品用途，会在父产品子组件管理页面展示给管理员。建议 50-200 字。 | `统一管理项目上下文信息，支持多源采集、可信度评估、知识图谱检索和上下文分析` |
| `platform.contact_email` | string | 否 | 本产品运维负责人的联系邮箱，用于父产品侧出现问题或升级通知时联系。 | `ops@example.com` |

#### 13.2.2 network — 网络与地址

| 节点路径 | 类型 | 必填 | 说明 | 填写样例 |
|---------|------|------|------|---------|
| `network.host` | string | 是 | 本产品监听的主机地址。如果与父产品部署在同一台机器，通常为 `127.0.0.1`；如果独立部署，填写内网 IP。 | `127.0.0.1` |
| `network.port` | integer | 是 | 本产品后端服务的监听端口。父产品前台会通过此端口代理请求。范围：1024-65535。 | `8000` |
| `network.public_url` | string | 否 | 本产品从外部可访问的完整 URL。当父产品前台需要直接跳转到本产品独立页面时使用（而非通过 iframe 嵌入）。如果填写，应以 `https://` 开头且不以 `/` 结尾。 | `https://context-platform.example.com` |
| `network.health_check_path` | string | 否 | 健康检查端点路径，父产品将定期访问此路径以确认本产品正常运行。默认为 `/api/v1/health`。 | `/api/v1/health` |
| `network.health_check_interval_seconds` | integer | 否 | 父产品健康检查的间隔秒数。默认 30 秒。范围：10-300。 | `30` |

#### 13.2.3 auth — 双向认证

认证分为两个方向：`inbound` 控制父产品如何认证来自本产品的请求，`outbound` 控制本产品如何认证来自父产品的请求。

**auth.inbound — 父产品验证本产品请求**

| 节点路径 | 类型 | 必填 | 说明 | 填写样例 |
|---------|------|------|------|---------|
| `auth.inbound.type` | string | 是 | 本产品向父产品发请求时使用的认证方式。可选值：`api_key`（在请求头中携带 API Key）、`jwt`（使用 JWT Token）、`none`（不认证，仅限开发环境）。 | `api_key` |
| `auth.inbound.api_key_header_name` | string | 否 | 当 type=api_key 时，携带 API Key 的请求头名称。本产品会在调用父产品 API 时在此请求头中附带 API Key。 | `X-Context-Platform-Key` |
| `auth.inbound.api_key_value` | string | 否 | 当 type=api_key 时，实际的 API Key 值。本产品在首次启动时自动生成并写入此字段，父产品管理员将此 Key 配置到父产品侧的白名单中。自动生成值为 32 字符的 hex 字符串。 | `a1b2c3d4e5f6...`（自动生成后填入） |
| `auth.inbound.jwt.secret` | string | 否 | 当 type=jwt 时，JWT 签名密钥。至少 32 字符。 | `openssl rand -hex 32` 生成的值 |
| `auth.inbound.jwt.issuer` | string | 否 | 当 type=jwt 时，JWT 签发者标识。父产品验证 Token 时会检查此值。 | `context-platform` |
| `auth.inbound.jwt.ttl_seconds` | integer | 否 | 当 type=jwt 时，Token 有效期秒数。默认 3600（1小时）。 | `3600` |

**auth.outbound — 本产品验证父产品请求**

| 节点路径 | 类型 | 必填 | 说明 | 填写样例 |
|---------|------|------|------|---------|
| `auth.outbound.type` | string | 是 | 本产品验证来自父产品请求时使用的认证方式。可选值：`api_key`（验证 API Key，进入单租户模式）、`jwt`（验证 JWT Token 的签名和声明）、`custom`（回调父产品验证端点）。对应接口设计 §3.2.2 的三种模式。 | `jwt` |
| `auth.outbound.api_key.value` | string | 否 | 当 type=api_key 时，父产品调用本产品使用的 API Key。本产品在首次启动时自动生成，父产品管理员将此 Key 配置到父产品侧的调用代码中。生成后仅启动时显示一次，后续不可查看。 | `kp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `auth.outbound.jwt.issuer` | string | 否 | 当 type=jwt 时，本产品信任的 JWT 签发者。通常为父产品的域名或服务标识。 | `https://parent-product.example.com` |
| `auth.outbound.jwt.jwks_url` | string | 否 | 当 type=jwt 时，父产品的 JWKS 端点完整 URL，用于获取公钥验证 JWT 签名。 | `https://parent-product.example.com/.well-known/jwks.json` |
| `auth.outbound.jwt.audience` | string | 否 | 当 type=jwt 时，JWT 中 aud（受众）字段的期望值。用于验证 Token 确实是签发给本产品的。 | `context-platform` |
| `auth.outbound.jwt.claim_mapping.sub` | string | 否 | JWT 中映射为用户标识的标准声明，默认值为 `sub`。父产品在 JWT 的 sub 字段中传递用户唯一标识。 | `sub` |
| `auth.outbound.jwt.claim_mapping.email` | string | 否 | JWT 中映射为用户邮箱的标准声明，默认值为 `email`。 | `email` |
| `auth.outbound.jwt.claim_mapping.username` | string | 否 | JWT 中映射为用户名的标准声明，默认值为 `preferred_username`。 | `preferred_username` |
| `auth.outbound.jwt.claim_mapping.role` | string | 否 | JWT 中映射为用户角色的自定义声明。格式为 `custom:字段名`，如父产品在 JWT 的 `custom:role` 声明中传递角色。留空则所有用户使用 default_role。 | `custom:role` |
| `auth.outbound.jwt.default_role` | string | 否 | 当 JWT 中没有角色声明时，分配给用户的默认角色。可选：admin/partner/senior_consultant/consultant/viewer。默认 `consultant`。 | `consultant` |
| `auth.outbound.custom.verification_url` | string | 否 | 当 type=custom 时，父产品提供的 Token 验证端点完整 URL。本产品将收到的 Token 发到此端点验证。 | `https://parent-product.example.com/api/verify-token` |
| `auth.outbound.custom.verification_method` | string | 否 | 当 type=custom 时，HTTP 请求方法。默认 `POST`。可选：GET/POST。 | `POST` |
| `auth.outbound.custom.header_name` | string | 否 | 当 type=custom 时，父产品调用本产品时携带 Token 的请求头名称。本产品从此请求头中提取 Token 值。 | `X-Parent-Token` |
| `auth.outbound.custom.cache_ttl_seconds` | integer | 否 | 当 type=custom 时，Token 验证结果的缓存时间（秒）。在此时间内同一 Token 不再重复验证。默认 300。 | `300` |

#### 13.2.4 ui — UI 嵌入外观

当父产品通过 iframe 嵌入本产品的界面时，通过以下配置统一视觉风格。

| 节点路径 | 类型 | 必填 | 说明 | 填写样例 |
|---------|------|------|------|---------|
| `ui.embed_enabled` | boolean | 否 | 是否允许父产品通过 iframe 嵌入本产品页面。开启后本产品的 HTTP 响应头中将添加对应的 CSP 和 X-Frame-Options 配置。默认 false。 | `true` |
| `ui.allowed_origins` | list[string] | 否 | 允许嵌入本产品的父产品域名列表（当 embed_enabled=true 时至少需要一条）。每项为完整协议+域名，如 `https://parent.example.com`。 | `["https://parent.example.com"]` |
| `ui.primary_color` | string | 否 | 主题色，用于按钮、链接、选中态等强调元素。需为有效的 hex 颜色值。本产品界面将自动适配此颜色。 | `#2563EB` |
| `ui.logo_url` | string | 否 | 本产品嵌入时在页面左上角显示的 Logo 图片完整 URL。建议使用 SVG 或 PNG 格式，尺寸不超过 200x50 像素。 | `https://parent.example.com/assets/logo.svg` |
| `ui.favicon_url` | string | 否 | 本产品嵌入页面的 favicon 图标 URL。 | `https://parent.example.com/favicon.ico` |
| `ui.locale` | string | 否 | 界面默认语言。可选：zh-CN/en。默认 zh-CN。 | `zh-CN` |

#### 13.2.5 features — 功能开关

控制本产品在作为子组件时启用哪些功能模块。关闭不需要的功能可以减少资源消耗和界面复杂度。

| 节点路径 | 类型 | 必填 | 说明 | 填写样例 |
|---------|------|------|------|---------|
| `features.ingestion_pipeline` | boolean | 否 | 是否启用上下文自动采集管道。关闭后仅支持手动录入和 API 推送，采集源配置 Tab 在管理端隐藏。默认 true。 | `true` |
| `features.knowledge_graph` | boolean | 否 | 是否启用知识图谱构建和可视化（图谱页面、实体关系查询、图谱检索模式）。关闭后用户端图谱相关功能全部隐藏。默认 true。 | `true` |
| `features.search` | boolean | 否 | 是否启用上下文检索功能。关闭后用户端搜索页面不可用，但采集和存储功能仍旧运行。默认 true。 | `true` |
| `features.confidence_engine` | boolean | 否 | 是否启用可信度引擎（自动评分、衰减、多源印证、矛盾检测）。关闭后所有上下文统一以默认分数入库，不进行自动评分变更。默认 true。 | `true` |
| `features.review_workflow` | boolean | 否 | 是否启用人工审核工作流（待验证队列、待裁决队列、审核任务分配）。关闭后上下文入库不经过审核流程。默认 true。 | `true` |
| `features.push_notification` | boolean | 否 | 是否启用事件推送（本产品主动向父产品 Webhook 推送上下文变更事件）。关闭后父产品无法接收实时上下文事件。默认 false。 | `false` |
| `features.data_export` | boolean | 否 | 是否启用数据导出功能（CSV/JSON/PDF）。关闭后用户端和管理端的导出入口均隐藏。默认 true。 | `true` |
| `features.api_access` | boolean | 否 | 是否开放 REST API 供父产品服务端调用。关闭后仅允许本产品自身前端访问 API，外部调用返回 403。默认 true。 | `true` |

#### 13.2.6 quotas — 资源配额

为本子组件设置使用上限，防止资源过度消耗影响父产品整体运行。

| 节点路径 | 类型 | 必填 | 说明 | 填写样例 |
|---------|------|------|------|---------|
| `quotas.max_contexts` | integer | 否 | 上下文条目总数上限。达到上限后新上下文入库将被拒绝（返回 429），已有上下文不受影响。留空表示不限制。 | `100000` |
| `quotas.max_entities` | integer | 否 | 实体总数上限。包括客户、项目、联系人等所有实体类型。留空表示不限制。 | `10000` |
| `quotas.max_users` | integer | 否 | 可创建的用户数上限。父产品通过 JWT 委托认证自动创建用户时也受此限制。留空表示不限制。 | `500` |
| `quotas.max_storage_gb` | integer | 否 | 向量数据库和全文索引的磁盘占用上限（GB）。达到上限后系统发出告警并暂停新数据的向量化入库，但文本存储不受影响。留空表示不限制。 | `50` |
| `quotas.api_rate_limit_per_minute` | integer | 否 | API 每分钟最大总调用次数。包括来自父产品前端的代理请求和父产品后端的直接 API 调用。默认 600。 | `600` |
| `quotas.llm_token_budget_daily` | integer | 否 | LLM 每日 Token 消耗预算上限。用于控制 AI 提取、摘要、审核辅助等功能的成本。达到上限后 LLM 调用降级为规则引擎处理。留空表示使用系统级默认值。 | `1000000` |

### 13.3 完整配置样例

以下是一个完整的 `config/integrations/context-platform.yaml` 样例，展示了本产品作为一个 SaaS 产品的子组件时的典型配置：

```yaml
# ============================================================
# config/integrations/context-platform.yaml
# 统一上下文管理中心 — 作为父产品子组件的集成配置文件
# 
# 说明：
# 1. 本文件由父产品运维人员在部署时创建和维护
# 2. 首次部署时，将本文件放置于 config/integrations/ 目录
# 3. 本产品启动时自动读取此文件完成与父产品的对接
# 4. 修改此文件后需要重启本产品服务以生效
# ============================================================

# ---------- 本产品基本信息 ----------
platform:
  name: "上下文管理中心"          # 必填：在父产品中显示的名称
  slug: "context-platform"       # 必填：唯一标识，建议全小写+连字符
  version: "1.0.0"                # 必填：当前部署版本号
  description: >-                 # 选填：在父产品子组件管理页面展示的简介
    统一管理项目上下文信息，支持多源采集、可信度评估、
    知识图谱检索和上下文生命周期管理
  contact_email: "ops@example.com"  # 选填：运维联系人

# ---------- 网络与地址 ----------
network:
  host: "127.0.0.1"               # 必填：监听地址（与父产品同机部署时用127.0.0.1）
  port: 8000                      # 必填：监听端口
  # public_url: "https://context.example.com"  # 选填：独立外部访问地址
  health_check_path: "/api/v1/health"  # 选填：健康检查端点，默认/api/v1/health
  health_check_interval_seconds: 30     # 选填：父产品健康检查间隔，默认30

# ---------- 双向认证 ----------
auth:
  # === outbound：本产品验证来自父产品的请求 ===
  outbound:
    type: "jwt"                    # 必填：认证方式（api_key / jwt / custom）
    
    # JWT 委托认证配置（type=jwt 时填写以下内容）
    jwt:
      issuer: "https://parent-product.example.com"  # 必填：信任的 JWT 签发者
      jwks_url: "https://parent-product.example.com/.well-known/jwks.json"  # 必填：JWKS端点
      audience: "context-platform"                  # 必填：期望的受众
      claim_mapping:
        sub: "sub"                  # 用户标识映射
        email: "email"              # 邮箱映射
        username: "preferred_username"  # 用户名映射
        role: "custom:role"         # 角色映射（父产品 JWT 中 custom:role 声明的值）
      default_role: "consultant"    # 当 JWT 中无角色声明时的默认角色
    
    # api_key 模式配置（type=api_key 时填写以下内容，启动时自动生成 value）
    # api_key:
    #   value: ""  # 留空，首次启动时自动生成并写入，生成后仅显示一次
    
    # custom 模式配置（type=custom 时填写以下内容）
    # custom:
    #   verification_url: "https://parent.example.com/api/verify-token"
    #   verification_method: "POST"
    #   header_name: "X-Parent-Token"
    #   cache_ttl_seconds: 300

  # === inbound：本产品向父产品发请求时使用的认证 ===
  inbound:
    type: "api_key"                # 必填：向父产品请求时的认证方式
    api_key_header_name: "X-Context-Platform-Key"  # type=api_key 时填写
    # api_key_value: ""  # 留空，首次启动时自动生成并写入

# ---------- UI 嵌入外观 ----------
ui:
  embed_enabled: true              # 是否允许 iframe 嵌入
  allowed_origins:                 # 允许嵌入的父产品域名
    - "https://parent-product.example.com"
  primary_color: "#2563EB"        # 主题色（hex格式）
  logo_url: "https://parent-product.example.com/assets/context-logo.svg"  # Logo URL
  favicon_url: "https://parent-product.example.com/favicon.ico"           # Favicon URL
  locale: "zh-CN"                  # 默认语言

# ---------- 功能开关 ----------
features:
  ingestion_pipeline: true        # 自动采集管道
  knowledge_graph: true           # 知识图谱
  search: true                    # 上下文检索
  confidence_engine: true         # 可信度引擎
  review_workflow: true           # 人工审核工作流
  push_notification: false        # 事件推送（暂不启用）
  data_export: true               # 数据导出
  api_access: true                # API 开放访问

# ---------- 资源配额 ----------
quotas:
  max_contexts: 100000            # 上下文总数上限
  max_entities: 10000             # 实体总数上限
  max_users: 500                  # 用户数上限
  max_storage_gb: 50              # 存储上限（GB）
  api_rate_limit_per_minute: 600  # API 限流（次/分钟）
  llm_token_budget_daily: 1000000 # LLM 每日 Token 预算
```

### 13.4 api_key 模式配置样例

当父产品希望使用最简单的 API Key 方式接入时（推荐用于内部系统间集成），配置如下：

```yaml
# 使用 API Key 认证的简洁配置（单租户模式）
platform:
  name: "上下文管理中心"
  slug: "context-platform"
  version: "1.0.0"

network:
  host: "127.0.0.1"
  port: 8000

auth:
  outbound:
    type: "api_key"
    api_key:
      value: ""  # 首次启动自动生成，生成后记录此值并配置到父产品侧

  inbound:
    type: "api_key"
    api_key_header_name: "X-Context-Platform-Key"

ui:
  embed_enabled: true
  allowed_origins:
    - "https://parent-product.example.com"

features:
  ingestion_pipeline: true
  knowledge_graph: true
  search: true
  confidence_engine: true
  review_workflow: true
  push_notification: false
  data_export: true
  api_access: true

quotas:
  max_contexts: 100000
  max_entities: 10000
  max_users: 500
  max_storage_gb: 50
```

### 13.5 首次启动时自动生成的值

以下配置项在首次启动时由本产品自动生成为随机安全值，并回写到配置文件中。父产品运维人员需要将这些值记录并配置到父产品侧的对应位置：

| 自动生成项 | 生成规则 | 使用场景 |
|-----------|---------|---------|
| `auth.outbound.api_key.value` | 50 字符随机字符串，前缀 `kp_` | 父产品调用本产品 API 时在请求头中携带此 Key。若 type=api_key，本产品将此 Key 提供给父产品管理员配置到父产品侧的请求代码中。 |
| `auth.inbound.api_key_value` | 32 字符 hex 随机字符串 | 本产品调用父产品 API 时携带的凭证。父产品需将此值加入其 API Key 白名单。 |

**重要提醒**：API Key 值在自动生成后仅在启动日志中显示一次，之后在配置文件中以哈希形式存储（不可反查原文）。运维人员必须在首次启动后立即记录这两个 Key 值。如果丢失，需要通过管理端 API 或重新生成的方式获取新 Key。

### 13.6 配置文件加载与校验

本产品在启动时按以下顺序加载配置文件：

1. 检查环境变量 `CONTEXT_PLATFORM_CONFIG_PATH` 指定的路径（最高优先级）
2. 检查当前工作目录下的 `config/integrations/context-platform.yaml`
3. 检查 `/etc/context-platform/integration.yaml`（Linux 系统路径）

找到第一个存在的文件即停止搜索，使用该文件作为配置源。

加载时执行以下校验：
- YAML 语法校验：格式错误则启动失败，输出具体错误行号
- 必填字段校验：platform.name、platform.slug、platform.version、network.host、network.port、auth.outbound.type 未填写时启动失败
- 枚举值校验：auth.outbound.type 必须为 api_key/jwt/custom 之一
- 端口范围校验：network.port 必须在 1024-65535 之间
- 域名格式校验：ui.allowed_origins 中每项必须是合法的 URL 格式（以 http:// 或 https:// 开头）
- 依赖校验：auth.outbound.type=jwt 时，jwt.issuer、jwt.jwks_url、jwt.audience 必须全部填写
- 依赖校验：auth.outbound.type=custom 时，custom.verification_url 必须填写

校验通过后，配置数据加载到 ConfigService 内存中，替换对应系统配置项的默认值（配置优先级：数据库值 > 本配置文件 > defaults.yaml）。

### 13.7 配置文件变更后的操作

修改 `context-platform.yaml` 后不会自动热加载，需要执行以下步骤使配置生效：

1. 修改配置文件并保存
2. 重启本产品服务：`systemctl restart context-platform` 或 `docker restart context-platform`
3. 检查启动日志中是否有配置加载错误
4. 在父产品侧验证子组件连通性（访问健康检查端点或通过父产品管理端查看子组件状态）

如果仅修改功能开关（features 节点）和资源配额（quotas 节点），可以在管理端 Web UI 的配置管理页面中直接修改对应系统配置项，无需重启服务。认证方式、网络地址和 UI 嵌入配置的变更则必须重启生效。

---
