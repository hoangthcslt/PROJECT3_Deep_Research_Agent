/**
 * API service — handles REST communication with the FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

import type {
  ResearchStartRequest,
  ResearchStartResponse,
  ResearchResumeRequest,
  GraphData,
  ResearchSessionStatusResponse,
  ResearchReportResponse,
  UploadPdfResponse,
} from "../types/research";
import { resolveSourceLink } from "./researchInputs";

function responseError(status: number, statusText: string, payload: unknown): Error {
  const body = payload && typeof payload === "object"
    ? payload as Record<string, unknown>
    : {};
  const detail = body.detail;
  const message = Array.isArray(detail)
    ? detail.map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object") {
          const error = item as Record<string, unknown>;
          const location = Array.isArray(error.loc)
            ? error.loc.filter((part): part is string | number => typeof part === "string" || typeof part === "number").join(".")
            : "";
          const reason = typeof error.msg === "string" ? error.msg : JSON.stringify(item);
          return location ? `${location}: ${reason}` : reason;
        }
        return String(item);
      }).join("; ")
    : typeof detail === "string"
      ? detail
      : typeof body.message === "string"
        ? body.message
        : detail == null
          ? `HTTP ${status}${statusText ? `: ${statusText}` : ""}`
          : JSON.stringify(detail);

  return new Error(message);
}

class ApiService {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      throw responseError(response.status, response.statusText, await response.json().catch(() => null));
    }

    return response.json();
  }

  /** POST /research/start — Create a session without starting the graph */
  async startResearch(data: ResearchStartRequest): Promise<ResearchStartResponse> {
    return this.request<ResearchStartResponse>("/research/start", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /** GET /research/{sessionId} — Read the latest session snapshot */
  async getResearchStatus(sessionId: string, signal?: AbortSignal): Promise<ResearchSessionStatusResponse> {
    return this.request<ResearchSessionStatusResponse>(`/research/${sessionId}`, { signal });
  }

  /** POST /research/{sessionId}/run — Explicitly start the graph */
  async runResearch(sessionId: string): Promise<ResearchSessionStatusResponse> {
    return this.request<ResearchSessionStatusResponse>(`/research/${sessionId}/run`, {
      method: "POST",
    });
  }

  /** POST /research/upload-pdf — Upload a PDF file */
  async uploadPdf(sessionId: string, file: File): Promise<UploadPdfResponse> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("session_id", sessionId);

    const response = await fetch(`${this.baseUrl}/research/upload-pdf`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw responseError(response.status, response.statusText, await response.json().catch(() => null));
    }

    return response.json() as Promise<UploadPdfResponse>;
  }

  sourceHref(url: string | undefined): string | null {
    return resolveSourceLink(url, this.baseUrl);
  }

  /** POST /research/{sessionId}/resume — Send HITL decision */
  async resumeResearch(
    sessionId: string,
    data: ResearchResumeRequest
  ): Promise<ResearchSessionStatusResponse> {
    return this.request<ResearchSessionStatusResponse>(`/research/${sessionId}/resume`, {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /** GET /research/{sessionId}/report — Read the saved draft or final report */
  async getResearchReport(sessionId: string, signal?: AbortSignal): Promise<ResearchReportResponse> {
    return this.request<ResearchReportResponse>(`/research/${sessionId}/report`, { signal });
  }

  /** GET /research/{sessionId}/graph — Fetch knowledge graph data */
  async getKnowledgeGraph(sessionId: string): Promise<GraphData> {
    return this.request<GraphData>(`/research/${sessionId}/graph`);
  }

  /** GET /research/{sessionId}/export — Download report */
  async exportReport(sessionId: string, format: "md" | "pdf" | "docx"): Promise<Blob> {
    const response = await fetch(
      `${this.baseUrl}/research/${sessionId}/export?format=${format}`
    );

    if (!response.ok) {
      throw responseError(response.status, response.statusText, await response.json().catch(() => null));
    }

    return response.blob();
  }
}

export const api = new ApiService(API_BASE);
