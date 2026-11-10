# 🔬 Deep Research Agent (Mowsis)

**AI-powered research assistant** that automates the entire research workflow through an autonomous **Plan → Search → Read → Synthesize → Reflect** loop.

**Problem, scope and acceptance:** start with the Vietnamese
[system analysis dossier](docs/system-analysis/README.md) and its
[offline UML gallery](docs/system-analysis/index.html). The agreed primary user
is an IT student preparing a technology survey for a project proposal.
The dossier distinguishes current behavior, proposed features and unmeasured
benefits; the original brainstorm is historical design material.

## Current Phase 3 scope

Quick web research is implemented: enter a question, approve or edit the plan,
review the report draft, approve it, and download Markdown. Standard/Deep,
academic search, supplied URLs, PDF inputs and PDF/DOCX export remain unavailable.

Sessions and checkpoints stay in one backend process. Reloading the browser can
recover progress while that process is running; restarting it loses sessions.
Use one backend worker until the persistence phase.

## Architecture (overall design)

```
User → React UI (Research Dashboard + Report Editor + Knowledge Graph Viz)
         ↓
     FastAPI Backend + WebSocket (streaming progress)
         ↓
   LangGraph Stateful Workflow:
     ┌─────────────────────────────────────────┐
     │  [1. Planner] → [HITL: Approve Plan]    │
     │  [2. Searcher] (Tavily + Scholar)        │
     │  [3. Reader] (Jina + PyMuPDF)            │
     │  [4. Extractor] (LLM Structured Output)  │
     │  [5. KG Builder] (Neo4j)                 │
     │  [6. Reflector] → Loop or Continue       │
     │  [7. Synthesizer] → [HITL: Review]       │
     └─────────────────────────────────────────┘
         ↓
   Qdrant (embeddings) + Neo4j (knowledge graph) + PostgreSQL (sessions)
```

## Tech Stack

| Layer | Technology |
|:---|:---|
| LLM | Configurable Google Gemini; defaults in `backend/.env.example` |
| Agent Framework | LangGraph |
| Web Search | Tavily API |
| Academic Search | Semantic Scholar API (later phase) |
| PDF Parsing | PyMuPDF4LLM (later phase) |
| Vector DB | Qdrant |
| Graph DB | Neo4j |
| Database | PostgreSQL (persistence phase; current sessions use RAM) |
| Backend | FastAPI + WebSocket |
| Frontend | React + Vite + TypeScript |

## Quick Start

Start each setup block in a separate terminal from the repository root.

### 1. Start Infrastructure

```powershell
docker compose up -d
```

This starts PostgreSQL, Qdrant, and Neo4j.

### 2. Backend Setup (Windows PowerShell)

```powershell
cd backend
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
# Add your API keys (GOOGLE_API_KEY, TAVILY_API_KEY) to .env

python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`

### Backend Setup (macOS/Linux)

```bash
cd backend
test -f .env || cp .env.example .env
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

### 3. Frontend Setup (Windows PowerShell)

```powershell
cd frontend
npm.cmd ci
npm.cmd run build
npm.cmd run lint
npm.cmd run dev
```

### Frontend Setup (macOS/Linux)

```bash
cd frontend
npm ci
npm run build
npm run lint
npm run dev
```

Frontend runs at `http://localhost:5173`

## Phase 3 checks

The backend tests use deterministic provider responses and local/in-memory
storage fixtures. They do not spend provider credits or prove live service
integration. From the repository root on Windows:

```powershell
cd backend
.\.venv\Scripts\python.exe -m pytest tests -q -p no:cacheprovider -o asyncio_default_fixture_loop_scope=function
```

From a separate terminal at the repository root:

```powershell
cd frontend
npm.cmd run build
npm.cmd run lint
node --test src/hooks/researchSnapshot.test.mjs
```

The snapshot self-check uses Node's native TypeScript support (Node 22.18+).
For macOS/Linux, use `.venv/bin/python` and `npm` in the equivalent commands.
Live Gemini/Tavily and database verification is tracked separately in
`docs/PHASE3_STATUS.md`.

Quick indexing keeps at most 8,000 UTF-8 bytes per page. Input budget accounting
uses a conservative UTF-8 byte estimate; citation checks verify reference IDs
and formatting, with phrase checks for uncited claims. They do not establish
that a source semantically proves every claim.

## Project Structure

```
Deep Research Agent/
├── docs/                    # Design documents & brainstorm
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entrypoint
│   │   ├── config.py        # Environment settings
│   │   ├── models/          # Pydantic schemas
│   │   ├── graph/           # LangGraph workflow
│   │   │   ├── state.py     # DeepResearchState
│   │   │   ├── workflow.py  # Graph builder
│   │   │   ├── edges.py     # Conditional routing
│   │   │   └── nodes/       # 7 pipeline nodes
│   │   ├── tools/           # Search, scrape, parse tools
│   │   ├── services/        # Qdrant, Neo4j, Embedding
│   │   ├── guardrails/      # Citation, safety, quality checks
│   │   └── api/             # REST routes + WebSocket
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/           # 4 main screens
│       ├── hooks/           # WebSocket hook
│       ├── services/        # API client
│       └── types/           # TypeScript types
├── docker-compose.yml
└── README.md
```

## API Endpoints

| Method | Endpoint | Description |
|:---|:---|:---|
| POST | `/api/v1/research/start` | Create a Quick session without starting it |
| POST | `/api/v1/research/{id}/run` | Start the created session once |
| GET | `/api/v1/research/{id}` | Latest revisioned session snapshot |
| POST | `/api/v1/research/upload-pdf` | Unavailable in Quick mode (501) |
| POST | `/api/v1/research/{id}/resume` | Approve/modify using the current interrupt ID |
| GET | `/api/v1/research/{id}/report` | Stored report draft or approved final report |
| GET | `/api/v1/research/{id}/graph` | Knowledge graph data |
| GET | `/api/v1/research/{id}/export` | Download approved Markdown; PDF/DOCX unavailable |
| WS | `/ws/research/{id}` | Read-only snapshots/progress; commands use REST |

## License

Academic project — not for commercial use.
