import type { ResearchSessionStatusResponse, SourceMetadata } from "../types/research";

type SnapshotRevision = Pick<ResearchSessionStatusResponse, "session_id" | "revision">;

const MAX_SNAPSHOT_SOURCES = 100;
const MAX_SELECTABLE_SOURCES = 8;

function isRecord(value: unknown): value is Record<string, unknown> {
  return Boolean(value) && typeof value === "object" && !Array.isArray(value);
}

function isOptionalString(value: unknown, maxLength: number): boolean {
  return value === undefined || value === null || (typeof value === "string" && value.length <= maxLength);
}

export function isSourceMetadata(value: unknown): value is SourceMetadata {
  if (!isRecord(value)) return false;
  return typeof value.source_id === "string"
    && value.source_id.length > 0 && value.source_id.length <= 128
    && typeof value.title === "string" && value.title.length > 0 && value.title.length <= 1000
    && (value.source_type === "paper" || value.source_type === "webpage" || value.source_type === "uploaded_pdf")
    && (value.content_kind === "webpage" || value.content_kind === "abstract" || value.content_kind === "pdf_excerpt")
    && Array.isArray(value.authors) && value.authors.length <= 100
    && value.authors.every((author) => typeof author === "string" && author.length <= 500)
    && (value.year === undefined || value.year === null || Number.isSafeInteger(value.year))
    && isOptionalString(value.url, 2048)
    && isOptionalString(value.open_access_pdf, 2048)
    && isOptionalString(value.content_snippet, 16000)
    && (value.page_count === undefined || value.page_count === null
      || (Number.isSafeInteger(value.page_count) && Number(value.page_count) >= 0))
    && typeof value.truncated === "boolean"
    && (value.credibility_tier === 1 || value.credibility_tier === 2 || value.credibility_tier === 3)
    && (value.citation_count === undefined || value.citation_count === null
      || (Number.isSafeInteger(value.citation_count) && Number(value.citation_count) >= 0));
}

export function isResearchSnapshot(value: unknown, sessionId: string): value is ResearchSessionStatusResponse {
  if (!isRecord(value)) return false;
  const snapshot = value as Partial<ResearchSessionStatusResponse>;
  const interrupt: unknown = snapshot.pending_interrupt;
  const validInterrupt = interrupt === null || (isRecord(interrupt)
    && typeof interrupt.interrupt_id === "string"
    && typeof interrupt.message === "string"
    && (interrupt.type === "PLAN_APPROVAL_REQUIRED"
      ? interrupt.plan === undefined || Array.isArray(interrupt.plan)
      : interrupt.type === "REPORT_APPROVAL_REQUIRED"
        ? interrupt.report_draft === undefined || typeof interrupt.report_draft === "string"
        : interrupt.type === "SOURCE_SELECTION_REQUIRED"
          && Array.isArray(interrupt.sources)
          && interrupt.sources.length <= MAX_SNAPSHOT_SOURCES
          && interrupt.sources.every(isSourceMetadata)));

  return snapshot.session_id === sessionId
    && Number.isSafeInteger(snapshot.revision)
    && (snapshot.revision ?? -1) >= 0
    && (snapshot.status === "created" || snapshot.status === "running" || snapshot.status === "awaiting_plan"
      || snapshot.status === "awaiting_sources" || snapshot.status === "awaiting_report"
      || snapshot.status === "completed" || snapshot.status === "error")
    && typeof snapshot.current_step === "string"
    && typeof snapshot.progress_percent === "number"
    && Number.isFinite(snapshot.progress_percent)
    && snapshot.progress_percent >= 0
    && snapshot.progress_percent <= 100
    && Array.isArray(snapshot.research_plan)
    && Array.isArray(snapshot.sources_found)
    && snapshot.sources_found.length <= MAX_SNAPSHOT_SOURCES
    && snapshot.sources_found.every(isSourceMetadata)
    && Array.isArray(snapshot.selected_source_ids)
    && snapshot.selected_source_ids.length <= MAX_SELECTABLE_SOURCES
    && snapshot.selected_source_ids.every((id) => typeof id === "string" && id.length > 0 && id.length <= 128)
    && Array.isArray(snapshot.source_errors)
    && snapshot.source_errors.length <= MAX_SNAPSHOT_SOURCES
    && snapshot.source_errors.every((error) => typeof error === "string" && error.length <= 500)
    && validInterrupt
    && (snapshot.error === null || typeof snapshot.error === "string");
}

export function isNewerSnapshot(
  next: SnapshotRevision,
  current: SnapshotRevision | null,
  activeSessionId: string,
): boolean {
  return next.session_id === activeSessionId
    && Number.isSafeInteger(next.revision)
    && next.revision >= 0
    && (!current || current.session_id !== activeSessionId || next.revision > current.revision);
}
