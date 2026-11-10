# Phase 2 status

2026-11-09: **code/test accepted**. Phase 3 has completed its code/test scope;
the user chose to defer live provider/database integration.

Luna max implemented the session, graph approval and frontend changes. Astra
reviewed callers and ran the available checks. The earlier installation
blockers have been resolved: frontend dependencies and backend/.venv are installed.

## Implemented and reviewed

- One in-memory manager owns session state, locks, revisions and graph tasks.
  Session creation does not start research; REST is the sole command path.
- Run/resume/status/report/export share the manager. Duplicate starts and
  duplicate/stale approval IDs are rejected. Snapshots exclude private file
  paths and raw document bodies.
- Plan/report generation is checkpointed before separate approval nodes.
  Plan edits are validated, applied and normalized to pending.
- Read-only WebSocket observers receive safe snapshots. Multiple tabs work;
  sends are bounded and disconnected observers are removed.
- The frontend recovers snapshots on reconnect, rejects stale revisions and
  responses from another session, preserves edits for the current interrupt,
  and shows request errors. Reconnect does not run the graph.
- Shutdown cancels graph tasks before closing database clients.

The four earlier blockers (missing API wiring, incompatible progress-page hook
caller, omitted draft, old-session callbacks) were fixed and reviewed.
Phase 3 intentionally disables PDF upload and non-Quick/non-web inputs until
their later phases.

## Current evidence

The combined backend suite passed **60 tests with no skips** in backend/.venv.
It includes a real LangGraph approval/checkpoint test, API/WebSocket tests,
and a connected Quick workflow through the actual nodes with in-memory Qdrant.
Provider outputs and Neo4j transport are deterministic fixtures.

Frontend production build passed; lint exits 0 with seven React/hook warnings.
The revision/session snapshot regression passed. Backend basic F/E9 static
checks and package consistency checks passed.

## Deferred acceptance

Live API/database startup and browser visual acceptance were not completed.
The user explicitly selected code/test acceptance first. See PHASE3_STATUS.md
for the exact evidence and limitations. Sessions/checkpoints still live in one
process and are lost on restart; shared persistence remains Phase 7.
