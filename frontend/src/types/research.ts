/**
 * TypeScript type definitions for the Deep Research Agent frontend.
 * Mirrors the Pydantic models from the backend API.
 */

// ═══════════════════════════════════════════════
//  Research Planning
// ═══════════════════════════════════════════════

export interface ResearchSubQuestion {
  id: string;
  question: string;
  target_source: "academic" | "web";
  status: "pending" | "completed" | "failed";
}

// ═══════════════════════════════════════════════
//  Sources & Documents
// ═══════════════════════════════════════════════

export interface SourceMetadata {
  source_id: string;
  url?: string;
  open_access_pdf?: string | null;
  title: string;
  authors: string[];
  year?: number;
  source_type: "paper" | "webpage" | "uploaded_pdf";
  content_kind: "webpage" | "abstract" | "pdf_excerpt";
  content_snippet?: string;
  page_count?: number | null;
  truncated: boolean;
  credibility_tier: 1 | 2 | 3;
  citation_count?: number;
}

// ═══════════════════════════════════════════════
//  Findings
// ═══════════════════════════════════════════════

export interface ExtractedFinding {
  claim: string;
  evidence: string;
  source_ids: string[];
  confidence_score: number;
}

export interface KnowledgeGap {
  missing_aspect: string;
  suggested_query: string;
  target_source: "academic" | "web";
}

// ═══════════════════════════════════════════════
//  API Request / Response
// ═══════════════════════════════════════════════

export interface ResearchStartRequest {
  question: string;
  depth: "quick";
  urls: string[];
  search_mode: ResearchSearchMode;
}

export type ResearchSearchMode = "web" | "academic" | "mixed" | "provided";

export interface ResearchStartResponse {
  session_id: string;
  status: "created";
}

export type ResearchResumeRequest =
  | { action: "approve"; interrupt_id: string }
  | { action: "modify"; interrupt_id: string; plan: ResearchSubQuestion[] }
  | { action: "select_sources"; interrupt_id: string; selected_source_ids: string[] };

export interface UploadPdfResponse {
  file_id: string;
  status: "uploaded";
  source: SourceMetadata;
}

export type ResearchSessionStatus =
  | "created"
  | "running"
  | "awaiting_plan"
  | "awaiting_sources"
  | "awaiting_report"
  | "completed"
  | "error";

export type PendingResearchInterrupt =
  | {
      interrupt_id: string;
      type: "PLAN_APPROVAL_REQUIRED";
      message: string;
      plan?: ResearchSubQuestion[];
    }
  | {
      interrupt_id: string;
      type: "SOURCE_SELECTION_REQUIRED";
      message: string;
      sources: SourceMetadata[];
    }
  | {
      interrupt_id: string;
      type: "REPORT_APPROVAL_REQUIRED";
      message: string;
      report_draft?: string;
    };

export interface ResearchSessionStatusResponse {
  session_id: string;
  status: ResearchSessionStatus;
  revision: number;
  current_step: string;
  progress_percent: number;
  research_plan: ResearchSubQuestion[];
  sources_found: SourceMetadata[];
  selected_source_ids: string[];
  source_errors: string[];
  pending_interrupt: PendingResearchInterrupt | null;
  error: string | null;
}

export interface ResearchReportResponse {
  session_id: string;
  status: ResearchSessionStatus;
  report_markdown: string;
  approved: boolean;
}

export interface LogEntry {
  timestamp: string;
  message: string;
  type: "info" | "warning" | "error";
}

// ═══════════════════════════════════════════════
//  WebSocket Protocol
// ═══════════════════════════════════════════════

export type WSEventType =
  | "SNAPSHOT"
  | "STEP_UPDATE"
  | "HITL_TRIGGER"
  | "DONE"
  | "ERROR";

export interface WSMessage {
  event: WSEventType;
  timestamp?: string;
  data: ResearchSessionStatusResponse;
}

// ═══════════════════════════════════════════════
//  Knowledge Graph (Neo4j visualization)
// ═══════════════════════════════════════════════

export interface GraphNode {
  id: string;
  label: string;
  properties: Record<string, unknown>;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

// ═══════════════════════════════════════════════
//  UI State
// ═══════════════════════════════════════════════

export type ResearchStep =
  | "idle"
  | "planning"
  | "searching"
  | "reading"
  | "extracting"
  | "reflecting"
  | "synthesizing"
  | "done"
  | "error";
