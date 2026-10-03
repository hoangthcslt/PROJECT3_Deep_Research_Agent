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
  title: string;
  authors: string[];
  year?: number;
  source_type: "paper" | "webpage" | "uploaded_pdf";
  content_snippet?: string;
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
  depth: "quick" | "standard" | "deep";
  urls: string[];
}

export interface ResearchStartResponse {
  session_id: string;
  status: string;
}

export interface ResearchResumeRequest {
  action: "approve" | "modify" | "feedback";
  payload: Record<string, unknown>;
}

// ═══════════════════════════════════════════════
//  WebSocket Protocol
// ═══════════════════════════════════════════════

export type WSEventType =
  | "STEP_UPDATE"
  | "LOG_STREAM"
  | "HITL_TRIGGER"
  | "REPORT_CHUNK"
  | "DONE"
  | "ERROR";

export interface WSMessage {
  event: WSEventType;
  timestamp: string;
  data: Record<string, unknown>;
}

export type HITLType =
  | "PLAN_APPROVAL_REQUIRED"
  | "SOURCE_SELECTION_REQUIRED"
  | "REPORT_APPROVAL_REQUIRED";

export interface HITLTriggerData {
  type: HITLType;
  plan?: ResearchSubQuestion[];
  sources?: SourceMetadata[];
  report_draft?: string;
  message: string;
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

export interface LogEntry {
  timestamp: string;
  message: string;
  type: "info" | "warning" | "error" | "agent";
}
