import assert from "node:assert/strict";
import test from "node:test";
import { isNewerSnapshot, isResearchSnapshot } from "./researchSnapshot.ts";

test("accepts a newer revision for the active session only", () => {
  assert.equal(isNewerSnapshot({ session_id: "a", revision: 4 }, { session_id: "a", revision: 3 }, "a"), true);
  assert.equal(isNewerSnapshot({ session_id: "a", revision: 3 }, { session_id: "a", revision: 3 }, "a"), false);
  assert.equal(isNewerSnapshot({ session_id: "a", revision: 2 }, { session_id: "a", revision: 3 }, "a"), false);
  assert.equal(isNewerSnapshot({ session_id: "a", revision: 9 }, null, "b"), false);
  assert.equal(isNewerSnapshot({ session_id: "b", revision: 0 }, { session_id: "a", revision: 9 }, "b"), true);
});

const source = {
  source_id: "REF_1",
  url: "https://example.org/paper",
  title: "Example paper",
  authors: ["Researcher"],
  source_type: "paper",
  content_kind: "abstract",
  content_snippet: "Abstract text",
  truncated: false,
  credibility_tier: 1,
};

function snapshot(overrides = {}) {
  return {
    session_id: "session-a",
    status: "awaiting_sources",
    revision: 2,
    current_step: "searching",
    progress_percent: 25,
    research_plan: [],
    sources_found: [source],
    selected_source_ids: ["REF_1"],
    source_errors: [],
    pending_interrupt: {
      interrupt_id: "interrupt-a",
      type: "SOURCE_SELECTION_REQUIRED",
      message: "Select sources.",
      sources: [source],
    },
    error: null,
    ...overrides,
  };
}

test("accepts source-selection snapshots and validates bounded source metadata", () => {
  assert.equal(isResearchSnapshot(snapshot(), "session-a"), true);
  assert.equal(isResearchSnapshot(snapshot({
    pending_interrupt: {
      ...snapshot().pending_interrupt,
      sources: [{ ...source, content_snippet: "x".repeat(16001) }],
    },
  }), "session-a"), false);
  assert.equal(isResearchSnapshot(snapshot({
    source_errors: ["x".repeat(501)],
  }), "session-a"), false);
});
