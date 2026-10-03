/**
 * useResearchWebSocket — Custom React hook for WebSocket communication.
 * Manages real-time connection to the FastAPI backend for streaming
 * agent progress, HITL triggers, and report chunks.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import type { WSMessage, LogEntry, ResearchStep } from "../types/research";

const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:8000";

interface UseResearchWebSocketReturn {
  /** Whether WebSocket is connected */
  isConnected: boolean;
  /** Current pipeline step */
  currentStep: ResearchStep;
  /** Progress percentage (0-100) */
  progress: number;
  /** Live activity log entries */
  logs: LogEntry[];
  /** Latest HITL trigger data (null when no HITL pending) */
  hitlTrigger: WSMessage | null;
  /** Report chunks received so far */
  reportChunks: string[];
  /** Send a message to the server */
  sendMessage: (event: string, data: Record<string, unknown>) => void;
  /** Clear HITL trigger after user responds */
  clearHitl: () => void;
}

export function useResearchWebSocket(
  sessionId: string | null
): UseResearchWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [currentStep, setCurrentStep] = useState<ResearchStep>("idle");
  const [progress, setProgress] = useState(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [hitlTrigger, setHitlTrigger] = useState<WSMessage | null>(null);
  const [reportChunks, setReportChunks] = useState<string[]>([]);

  // ── Connect / Disconnect ──
  useEffect(() => {
    if (!sessionId) return;

    const ws = new WebSocket(`${WS_BASE}/ws/research/${sessionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setIsConnected(true);
      addLog("info", "Kết nối WebSocket thành công");
    };

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        handleMessage(message);
      } catch (err) {
        console.error("Failed to parse WS message:", err);
      }
    };

    ws.onclose = () => {
      setIsConnected(false);
      addLog("warning", "WebSocket đã ngắt kết nối");
    };

    ws.onerror = () => {
      addLog("error", "Lỗi kết nối WebSocket");
    };

    return () => {
      ws.close();
    };
  }, [sessionId]);

  // ── Message Handler ──
  const handleMessage = useCallback((message: WSMessage) => {
    switch (message.event) {
      case "STEP_UPDATE": {
        const step = message.data.current_step as ResearchStep;
        const pct = (message.data.progress_percent as number) || 0;
        setCurrentStep(step);
        setProgress(pct);
        addLog("info", message.data.message as string || `Step: ${step}`);
        break;
      }

      case "LOG_STREAM":
        addLog("agent", message.data.message as string);
        break;

      case "HITL_TRIGGER":
        setHitlTrigger(message);
        addLog("warning", `⏸️ Cần tương tác: ${message.data.message}`);
        break;

      case "REPORT_CHUNK":
        setReportChunks((prev) => [...prev, message.data.chunk as string]);
        break;

      case "DONE":
        setCurrentStep("done");
        setProgress(100);
        addLog("info", "✅ Nghiên cứu hoàn tất!");
        break;

      case "ERROR":
        setCurrentStep("error");
        addLog("error", message.data.message as string || "Đã xảy ra lỗi");
        break;
    }
  }, []);

  // ── Send Message ──
  const sendMessage = useCallback(
    (event: string, data: Record<string, unknown>) => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send(
          JSON.stringify({
            event,
            data,
            timestamp: new Date().toISOString(),
          })
        );
      }
    },
    []
  );

  // ── Helpers ──
  const addLog = (type: LogEntry["type"], message: string) => {
    setLogs((prev) => [
      ...prev,
      {
        timestamp: new Date().toISOString(),
        message,
        type,
      },
    ]);
  };

  const clearHitl = useCallback(() => {
    setHitlTrigger(null);
  }, []);

  return {
    isConnected,
    currentStep,
    progress,
    logs,
    hitlTrigger,
    reportChunks,
    sendMessage,
    clearHitl,
  };
}
