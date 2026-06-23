[README_EN.md](https://github.com/user-attachments/files/29241650/README_EN.md)
# Context Platform — Unified Context Management Center

> **Context-as-a-Service** — Every piece of context your company accumulates can be precisely retrieved, trusted, and kept fresh by AI Agents and team members — exactly when needed.

---

## Why Context Platform?

Fragmented enterprise information is the #1 obstacle to AI adoption:

- Critical client details scattered across chat threads, unsearchable
- Project decisions locked in personal notes, lost when people leave
- AI Agents lack structured context when executing diagnostic tasks
- Managers can't quickly grasp the latest status of all clients/projects

Context Platform handles this end-to-end: **Unified Ingestion → Structured Storage → Confidence Assessment → Lifecycle Management**, becoming the company-grade context infrastructure.

---

## Core Features

### 🔍 Hybrid Search Engine

Three retrieval modes fused with weighted scoring, covering everything from exact match to cross-entity semantic association:

| Mode | Mechanism | Weight |
|------|-----------|--------|
| Keyword | BM25 exact match (client name / project name / date) | 0.3 |
| Vector Semantic | pgvector approximate match + cross-entity association | 0.4 |
| Graph Traversal | LightRAG 2-hop relationship traversal | 0.3 |

Five query modes supported: Exact, Semantic, Relational, Timeline, and Contradiction.

### 🏷️ Six-Level Confidence Engine

A proprietary core component — every context entry carries a traceable confidence rating:

| Level | Name | Score Range | Agent Citation Rule |
|-------|------|-------------|---------------------|
| L5 | Authoritative | [0.95, 1.00] | Freely cite |
| L4 | High Confidence | [0.85, 0.95) | Cite with source attribution |
| L3 | Moderate | [0.70, 0.85) | Cross-validation required |
| L2 | Pending Verification | [0.50, 0.70) | Not citable; auxiliary reference only |
| L1 | Low Confidence | [0.30, 0.50) | Not citable |
| L0 | Unusable | [0.00, 0.30) | Expired / contradictory |

Four sub-algorithms drive confidence scoring:
- **Initial Confidence Mapping** — 15 source types mapped to different starting levels (Contract L5 → Verbal L1)
- **Multi-Source Corroboration Boost** — Gradually raises confidence when multiple sources agree without contradiction (cap +0.45)
- **Temporal Decay** — Linear decay after 6 months (−0.03 per month)
- **Contradiction Penalty** — Both parties lose score when conflict is flagged (−0.10)

### 🛡️ Three-Layer Permission Model

A proprietary permission engine — each layer tightens access, the strictest rule wins:

```
Layer 1: RBAC (role-permission matrix) → Layer 2: Entity Boundary (data isolation) → Layer 3: Sensitivity (4-level classification)
```

- **RBAC**: 5 roles (admin / partner / senior_consultant / consultant / agent) × 12 operations
- **Entity Boundary**: Users can only access contexts of clients/projects they're assigned to
- **Sensitivity**: 4 levels — public / internal / confidential / top_secret; Agents cannot read top_secret

### 🕸️ Knowledge Relationship Graph

7 relationship types model cross-entity semantic associations: `drives` / `threatens` / `depends_on` / `contradicts` / `supersedes` / `informs` / `part_of`

Supports 1–2 hop traversal, path analysis, subgraph export, and graph visualization colored by domain/confidence.

### 🔄 Full Lifecycle Management

State machine covers the entire chain from creation to archival:

```
Created → Pending Verification → Active → Decaying / Superseded / Contradicted / Archived
```

- Confirmed contexts are **immutable** (append new versions only, never modify history) — inspired by Manus context engineering's "Read-Before-Decide" principle
- Auto-triggered decay (6 months without update → decay flag, confidence downgrade)
- Automatic contradiction detection + human adjudication workflow

### 📡 Multi-Source Ingestion Pipeline

Automated + manual dual-channel ingestion, covering all enterprise data sources:

| Source | Priority | Mechanism |
|--------|----------|-----------|
| Project Knowledge Base (IMA / Feishu Drive) | P0 | API full/incremental sync |
| Memory.md files | P1 | File watch + LLM parsing & import |
| Feishu Documents | P1 | Feishu Open Platform API |
| Feishu Group Messages | P1 | Bot Webhook + keyword trigger |
| Email | P2 | IMAP + rule engine |
| Public Company Financial Reports | P2 | Public API auto-fetch |
| Manual Insight Entry | P0 | Web review queue |

7-step pipeline processing: Dedup → Auto-classify → Entity Extraction → Relationship Recognition → Confidence Pre-assessment → Conflict Detection → Store as Pending Verification.

### 🤖 MCP Server (Agent Interface)

8 MCP Tools exposed externally; Agent query results automatically include **Consumption Guidance**:

```json
{
  "usage_advice": "Cite with source attribution",
  "advice_reason": "This context originates from an official financial report, confidence L4",
  "related_higher_confidence_hint": "2 L4+ related contexts exist under the same entity — recommend retrieving them together",
  "is_lesson_learned": false,
  "cross_validation_suggestion": "Related entry 'XX Audit Report' (L5) may contain more reliable information"
}
```

| Tool | Purpose |
|------|---------|
| `search_context` | Agent diagnostic search |
| `get_context_detail` | Get single context detail |
| `get_entity_graph` | Entity relationship graph |
| `get_context_timeline` | Timeline analysis |
| `get_contradictions` | Contradiction query |
| `submit_context` | Agent-submitted context (tagged L2) |
| `check_confidence` | Confidence verification |
| `submit_correction` | Agent correction suggestion |

---

## Architecture Overview

5-layer architecture + Integration Adapter Layer; Phase 1–3 uses Modular Monolith:

```
┌─ Consumption Layer ───────────────────────────────────┐
│  MCP Tool (Agent) | SDK Calls | Web Frontend          │
├─ Integration Adapter Layer ────────────────────────────┤
│  Auth Adapter | Workspace Middleware | Webhook Emitter │
│  Quota Service | UI Adapter                           │
├─ API Gateway Layer ────────────────────────────────────┤
│  FastAPI + JWT/API Key + RBAC + Rate Limit + Audit    │
├─ Business Service Layer ──────────────────────────────┤
│  Context | Ingestion | Search | Distribution          │
│  Conflict | Permission | Report | Config              │
│  Guidance | Sync                                     │
├─ Data Access Layer ────────────────────────────────────┤
│  SQLAlchemy ORM | pgvector | LightRAG | Mem0          │
├─ Storage Layer ───────────────────────────────────────┤
│  PostgreSQL 16 + pgvector | Qdrant (Mem0)             │
│  File System (iCloud)                                 │
└───────────────────────────────────────────────────────┘
```

**Architecture Decision**: Small team (<10 people) + strong data coupling + graph queries need cross-table JOINs → monolith-first, inter-module communication via Python interfaces (not HTTP). Ingestion/Search can be extracted as microservices when bottlenecks emerge.

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend Framework | **FastAPI** (Python) |
| Database | **PostgreSQL 16** + pgvector + pg_bestmatch |
| Vector DB | **Qdrant** (Mem0) |
| Knowledge Graph | **LightRAG** |
| ORM | **SQLAlchemy** + Alembic migrations |
| Authentication | JWT (access 30min / refresh 7d) + API Key |
| Rate Limiting | SlowAPI |
| Task Scheduling | **Prefect** |
| LLM | DeepSeek (classification / entity extraction / context extraction) |
| Embedding Model | BGE-M3 |
| Frontend — Admin | **Refine** + shadcn/ui |
| Frontend — User | React + shadcn/ui + Cytoscape.js |
| Agent Interface | **MCP Server** (FastMCP) |
| Client SDK | Python + TypeScript |
| Cache | Redis (permission cache, 5min TTL) |
| Containerization | Docker Compose |

---

## Project Structure

```
context-platform/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── config.py               # Configuration management
│   │   ├── api/v1/                 # Internal API routes
│   │   │   ├── context.py          # /api/v1/contexts
│   │   │   ├── search.py           # /api/v1/search
│   │   │   ├── entities.py         # /api/v1/entities
│   │   │   ├── relations.py        # /api/v1/relations
│   │   │   ├── review.py           # /api/v1/review
│   │   │   ├── permissions.py      # /api/v1/permissions
│   │   │   └── ...
│   │   ├── api/external/           # External API (component interface)
│   │   ├── api/mcp/                # MCP Server endpoint
│   │   ├── core/                   # Security + RBAC + Audit + Rate Limit
│   │   ├── services/               # Business service layer (10+ Services)
│   │   │   ├── confidence_service.py   # ⭐ Confidence Engine
│   │   │   ├── permission_service.py   # ⭐ 3-Layer Permission Model
│   │   │   ├── search_service.py       # Hybrid search
│   │   │   ├── ingestion_service.py    # Ingestion pipeline
│   │   │   ├── guidance_service.py     # Agent consumption guidance
│   │   │   └── ...
│   │   ├── integrations/           # External system integration
│   │   │   ├── adapter.py          # Integration adapter entry
│   │   │   ├── auth/               # Auth adapters
│   │   │   ├── workspace/          # Multi-tenant management
│   │   │   ├── feishu_client.py    # Feishu
│   │   │   ├── mem0_client.py      # Mem0
│   │   │   └── ...
│   │   ├── models/                 # SQLAlchemy ORM
│   │   ├── schemas/                # Pydantic models
│   │   └── pipelines/              # Prefect ingestion pipelines
│   ├── alembic/                    # Database migrations
│   ├── tests/                      # Unit + integration tests
│   └── requirements.txt
│
├── frontend/
│   ├── admin/                      # Admin portal (Refine + shadcn/ui)
│   └── user/                       # User portal (React + Cytoscape.js)
│
├── sdk/
│   ├── python/                     # Python client SDK
│   └── typescript/                 # TypeScript client SDK
│
├── plugin-manifest.json            # Component manifest
├── docker-compose.yml
└── Makefile
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 16 (with pgvector extension)

### Local Development

```bash
# 1. Clone the repo
git clone https://github.com/your-org/context-platform.git
cd context-platform

# 2. Start infrastructure (PostgreSQL + Qdrant)
docker compose up db qdrant -d

# 3. Configure environment
cp backend/.env.example backend/.env
# Edit .env — fill in DATABASE_URL, DEEPSEEK_API_KEY, etc.

# 4. Install backend dependencies
cd backend
pip install -r requirements.txt

# 5. Run database migrations
alembic upgrade head

# 6. Start backend service
uvicorn app.main:app --reload --port 8000

# 7. Install frontend dependencies and start
cd ../frontend/admin
npm install && npm run dev    # Admin portal :3001

cd ../frontend/user
npm install && npm run dev    # User portal :3002
```

### Docker Compose One-Command Start

```bash
docker compose up -d
# Backend :8000 | Admin :3001 | User :3002 | Qdrant :6333
```

---

## API Overview

### Internal API (`/api/v1/`)

| Endpoint | Description |
|----------|-------------|
| `GET/POST /contexts` | Context list / create |
| `POST /search` | Unified hybrid search entry |
| `GET/POST /entities` | Entity management |
| `GET /entities/{id}/graph` | Entity relationship graph |
| `GET/POST /relations` | Relationship management |
| `GET/POST /review/queue` | Review queue |
| `GET /metrics/overview` | Global metrics overview |

### External API (`/api/v1/external/`)

Component-style interface for parent product SDK integration; supports API Key / JWT delegation / Custom Token authentication.

### MCP Tools

Agents call via MCP protocol — `search_context` / `get_entity_graph` / `submit_context` and 5 other tools.

---

## Core Algorithms Quick Reference

### Confidence Calculation Example

```
# L2(0.60) corroborated by L4(0.90)
corroboration_weight = min(0.15, (0.90-0.5)*0.3) = 0.12
new_score = 0.60 + (1.0-0.60) * 0.12 = 0.648 → still L2

# L4(0.90) 12 months without update
effective = 0.90 - 0.03*6 = 0.72 → downgraded to L3

# Contradiction penalty
penalized = max(current_score - 0.10, 0.10)
```

### Permission Check Flow

```
User Request → Layer1 RBAC (deny → 403) → Layer2 Entity Boundary (deny → 403) → Layer3 Sensitivity (deny → 403) → 200
```

---

## Context Classification System

Four domains cover the full enterprise context landscape:

| Domain | Coverage |
|--------|----------|
| **Client Domain** | Profile / Org Structure / Business Model / Financials |
| **Project Domain** | Pre-sales / Contract Scope / Delivery / Finance |
| **Operations Domain** | Product Innovation / Capability Building / Business Management / Knowledge Assets |
| **External Environment Domain** | Industry Policy / Competitive Dynamics / Tech Trends / Ecosystem Partners |

---

## Memory.md Recommended Template

To maximize the ingestion pipeline's intelligent extraction capability, teams should maintain Memory.md using the following structure:

```markdown
# Memory.md

## 1. Goal          → context_role="goal", immutable
## 2. Phases        → context_role="progress", Checkbox auto-parsed
## 3. Findings      → context_role="finding", auto-linked to entities
## 4. Lessons       → context_role="lesson_learned", confidence auto-promoted to L3
```

The **Lessons** section carries exceptional value — converting team trial-and-error experience into searchable, citable knowledge assets; Agents auto-highlight entries tagged as "lesson learned".

---

## Contributing

Contributions welcome! Please follow this workflow:

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m 'Add your feature'`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

### Development Standards

- Backend: Follow FastAPI project structure; Service layer holds pure business logic; IO operations handled by callers
- Frontend: shadcn/ui component library + React hooks pattern
- Testing: Every Service requires unit tests; every API endpoint requires integration tests
- Database changes: Through Alembic migrations only; manual table edits prohibited

---

## License

Apache License 2.0 — See [LICENSE](LICENSE) for details.

---

> *"The end of RAG is the Knowledge Graph"* — Context Platform isn't just retrieval augmentation; it's the structured infrastructure for enterprise context.
