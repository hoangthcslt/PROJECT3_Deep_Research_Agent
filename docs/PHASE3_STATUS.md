# Phase 3 status

2026-11-09: **accepted for code/test scope**. The user explicitly chose
“Chốt code/test trước; tích hợp thật sau”. Live provider/database acceptance
is deferred; this is not a claim that a production or live research run passed.

Luna max implemented the changes. Astra reviewed the connected callers,
requested fixes and independently ran the checks below.

## Implemented and reviewed

- Quick web workflow: create session, generate/checkpoint plan, edit/approve,
  search, safely read/index pages, extract findings, persist scoped graph data,
  reflect, synthesize, review/approve and download stored Markdown.
- Budgets are initialized per session, survive checkpoints and are checked
  before paid calls. Plans fit the search-call limit. Quick indexing caps each
  document at 8,000 UTF-8 bytes; token accounting uses a conservative byte
  estimate. Missing sources, embedding errors and exhausted budgets fail visibly.
- URL fetching validates DNS answers and every redirect, pins the checked IP
  while preserving Host/TLS SNI, separates connections and bounds content type,
  response size, redirects and time. Embeddings are async, 768-dimensional,
  normalized and validated; failures never become zero-vector success.
- Qdrant points use deterministic session/source keys and protect reserved
  metadata. Retrieval filters by session. Neo4j source/finding keys,
  relationships and graph retrieval are also scoped to the session.
- Citation validation requires actual body references to indexed sources.
  Footnote definitions, code and HTML comments do not count as body citations.
  Generated reference definitions/sections are replaced by canonical source
  titles/URLs, with valid Markdown footnotes and escaped metadata.
- Report GET returns a stored draft/final without generation. Markdown export
  requires completed approval. The frontend shows drafts, approval links,
  download errors and unavailable options explicitly.
- Config/example defaults use gemini-2.5-flash and models/gemini-embedding-001.
  Matching retired local defaults were updated without printing credentials.
  The obsolete google-generativeai dependency was removed.
- Standard/Deep, supplied URLs, PDF inputs and PDF/DOCX export remain outside
  Phase 3. No Phase 4 implementation or commit was made.

## Independent verification

| Check | Result |
|---|---|
| Backend suite in backend/.venv | **60 passed, 0 skipped**, 2.24s |
| Connected Quick workflow | Real LangGraph and in-memory Qdrant, all actual nodes; deterministic provider responses and recording Neo4j driver |
| API and WebSocket | Real FastAPI/TestClient and session manager; deterministic graph, no live service startup |
| Qdrant isolation | Actual in-memory client; deterministic IDs, metadata protection and two-session retrieval |
| Backend basic static checks | Ruff F/E9 passed |
| Installed package consistency | pip check passed |
| Frontend production build | npm.cmd run build passed |
| Frontend lint | Exit 0; seven React/hook warnings remain |
| Frontend snapshot regression | 1 passed |
| Whitespace | git diff --check passed; Git emitted line-ending notices |

Reproduce backend tests from backend with:
`.venv/Scripts/python.exe -B -m pytest tests -q -rs -p no:cacheprovider -o asyncio_default_fixture_loop_scope=function`

The connected workflow test exercises plan editing, read/index/extract,
report approval, stable source IDs, budget persistence and generation-once
behavior across checkpoints. Other regressions cover no sources, provider
failures, invalid vectors, budget exhaustion, malformed citations, duplicate
and stale commands, and cross-session data isolation.

## Deferred checks and limits

- No live Gemini/Tavily request or external Qdrant/Neo4j integration was run,
  per the user's selected scope. Neo4j tests verify query/parameter contracts,
  not execution against a Neo4j server.
- Browser visual checks could not run because the computer/browser host was
  unavailable. The production build and API tests passed independently.
- Frontend lint retains seven React/hook warnings. The broader Ruff style
  profile still reports annotation/import-style and exception-policy findings;
  basic F/E9 checks are clean. A broad formatting refactor was not part of this phase.
- Citation checks validate references and use phrase heuristics; they do not
  establish semantic support for every claim. Only the indexed page prefix is
  used for Quick research.
- Sessions/checkpoints are RAM-only and require one backend worker. Restarting
  loses sessions; shared persistence remains Phase 7.
