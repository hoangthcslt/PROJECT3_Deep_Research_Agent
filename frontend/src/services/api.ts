/**
 * API service — handles REST communication with the FastAPI backend.
 */

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

import type {
  ResearchStartRequest,
  ResearchStartResponse,
  ResearchResumeRequest,
  GraphData,
} from "../types/research";

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
      const error = await response.json().catch(() => ({ detail: "Unknown error" }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  /** POST /research/start — Start a new research session */
  async startResearch(data: ResearchStartRequest): Promise<ResearchStartResponse> {
    return this.request<ResearchStartResponse>("/research/start", {
      method: "POST",
      body: JSON.stringify(data),
    });
  }

  /** POST /research/upload-pdf — Upload a PDF file */
  async uploadPdf(sessionId: string, file: File): Promise<{ file_id: string; status: string }> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("session_id", sessionId);

    const response = await fetch(`${this.baseUrl}/research/upload-pdf`, {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error("Failed to upload PDF");
    }

    return response.json();
  }

  /** POST /research/{sessionId}/resume — Send HITL decision */
  async resumeResearch(
    sessionId: string,
    data: ResearchResumeRequest
  ): Promise<{ status: string }> {
    return this.request(`/research/${sessionId}/resume`, {
      method: "POST",
      body: JSON.stringify(data),
    });
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
      throw new Error("Export failed");
    }

    return response.blob();
  }
}

export const api = new ApiService(API_BASE);
