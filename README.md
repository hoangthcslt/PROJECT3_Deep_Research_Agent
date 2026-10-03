# 🔬 Deep Research Agent (Mowsis)

**AI-powered research assistant** that automates the entire research workflow through an autonomous **Plan → Search → Read → Synthesize → Reflect** loop.

## Architecture

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
| LLM | Google Gemini 2.x |
| Agent Framework | LangGraph |
| Web Search | Tavily API |
| Academic Search | Semantic Scholar API |
| PDF Parsing | PyMuPDF4LLM |
| Vector DB | Qdrant |
| Graph DB | Neo4j |
| Database | PostgreSQL |
| Backend | FastAPI + WebSocket |
| Frontend | React + Vite + TypeScript |

## Quick Start

### 1. Start Infrastructure

```bash
docker-compose up -d
```

This starts PostgreSQL, Qdrant, and Neo4j.

### 2. Backend Setup

```bash
cd backend
cp .env.example .env
# Edit .env with your API keys (GOOGLE_API_KEY, TAVILY_API_KEY)

python -m venv venv
source venv/bin/activate   # Linux/Mac
# venv\Scripts\activate    # Windows

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend runs at `http://localhost:8000`

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`

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
| POST | `/api/v1/research/start` | Start research session |
| POST | `/api/v1/research/upload-pdf` | Upload PDF file |
| POST | `/api/v1/research/{id}/resume` | HITL response |
| GET | `/api/v1/research/{id}/graph` | Knowledge graph data |
| GET | `/api/v1/research/{id}/export` | Export report |
| WS | `/ws/research/{id}` | Real-time streaming |

## License

Academic project — not for commercial use.
