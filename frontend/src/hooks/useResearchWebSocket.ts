import { useCallback, useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import { isNewerSnapshot, isResearchSnapshot } from "./researchSnapshot";
import type {
  ResearchSessionStatusResponse,
  LogEntry,
  WSMessage,
} from "../types/research";

const WS_BASE = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
const WS_EVENTS = ["SNAPSHOT", "STEP_UPDATE", "HITL_TRIGGER", "DONE", "ERROR"];

interface UseResearchWebSocketReturn {
  isConnected: boolean;
  snapshot: ResearchSessionStatusResponse | null;
  error: string | null;
  activity: LogEntry[];
  acceptSnapshot: (snapshot: ResearchSessionStatusResponse) => boolean;
}

function activityFor(snapshot: ResearchSessionStatusResponse): LogEntry {
  const message = snapshot.status === "running"
    ? `Đang nghiên cứu: ${snapshot.current_step} (${snapshot.progress_percent}%).`
    : snapshot.status === "awaiting_plan"
      ? "Đang chờ bạn duyệt kế hoạch nghiên cứu."
      : snapshot.status === "awaiting_sources"
        ? "Đang chờ bạn chọn nguồn để đọc."
      : snapshot.status === "awaiting_report"
        ? "Đang chờ bạn duyệt bản nháp báo cáo."
        : snapshot.status === "completed"
          ? "Nghiên cứu đã hoàn tất."
          : snapshot.status === "error"
            ? `Nghiên cứu gặp lỗi: ${snapshot.error ?? "Lỗi không xác định."}`
            : "Phiên nghiên cứu đã được tạo.";
  const type = snapshot.status === "error" ? "error" : snapshot.status.startsWith("awaiting_") ? "warning" : "info";
  return { timestamp: new Date().toISOString(), message, type };
}

export function useResearchWebSocket(sessionId: string | null): UseResearchWebSocketReturn {
  const currentSessionRef = useRef(sessionId);
  currentSessionRef.current = sessionId;
  const snapshotRef = useRef<ResearchSessionStatusResponse | null>(null);
  const [snapshot, setSnapshot] = useState<ResearchSessionStatusResponse | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activity, setActivity] = useState<LogEntry[]>([]);

  const acceptSnapshot = useCallback((next: ResearchSessionStatusResponse) => {
    const activeSessionId = currentSessionRef.current;
    if (!activeSessionId
      || !isResearchSnapshot(next, activeSessionId)
      || !isNewerSnapshot(next, snapshotRef.current, activeSessionId)) return false;
    snapshotRef.current = next;
    setSnapshot(next);
    setActivity((previous) => [...previous, activityFor(next)].slice(-40));
    return true;
  }, []);

  useEffect(() => {
    let active = true;
    let socket: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let retryDelay = 500;
    let hasOpened = false;
    let terminalClose = false;
    let statusRequest: AbortController | null = null;

    snapshotRef.current = null;
    setSnapshot(null);
    setIsConnected(false);
    setError(null);
    setActivity([]);

    if (!sessionId) return;

    const fetchSnapshot = () => {
      statusRequest?.abort();
      statusRequest = new AbortController();
      api.getResearchStatus(sessionId, statusRequest.signal).then((status) => {
        if (active) {
          if (!isResearchSnapshot(status, sessionId)) {
            setError("Máy chủ trả về trạng thái phiên không hợp lệ.");
          } else {
            acceptSnapshot(status);
            if (!terminalClose) setError(null);
          }
        }
      }).catch((reason: unknown) => {
        if (active && !(reason instanceof DOMException && reason.name === "AbortError")) {
          setError(reason instanceof Error ? reason.message : "Không thể tải trạng thái phiên nghiên cứu.");
        }
      });
    };

    const connect = () => {
      if (!active) return;
      const currentSocket = new WebSocket(`${WS_BASE}/ws/research/${sessionId}`);
      socket = currentSocket;
      currentSocket.onopen = () => {
        if (!active) return;
        setIsConnected(true);
        retryDelay = 500;
        if (hasOpened) fetchSnapshot();
        hasOpened = true;
      };
      currentSocket.onmessage = (event) => {
        if (!active) return;
        try {
          const message = JSON.parse(event.data) as WSMessage;
          if (WS_EVENTS.includes(message.event) && isResearchSnapshot(message.data, sessionId)) {
            acceptSnapshot(message.data);
            setError(null);
          }
        } catch {
          setError("Máy chủ gửi cập nhật phiên không đọc được.");
        }
      };
      currentSocket.onerror = () => {
        if (active) {
          setIsConnected(false);
          setError("Lỗi kết nối WebSocket; đang thử kết nối lại.");
        }
        currentSocket.close();
      };
      currentSocket.onclose = (event) => {
        if (!active) return;
        setIsConnected(false);
        if (event.code === 4404 || event.code === 1008) {
          terminalClose = true;
          setError(event.code === 4404
            ? "Không tìm thấy phiên nghiên cứu trên máy chủ."
            : "Máy chủ từ chối kết nối WebSocket cho phiên này.");
          return;
        }
        reconnectTimer = window.setTimeout(connect, retryDelay);
        retryDelay = Math.min(retryDelay * 2, 10000);
      };
    };

    fetchSnapshot();
    connect();

    return () => {
      active = false;
      statusRequest?.abort();
      if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
      if (socket) {
        socket.onclose = null;
        socket.close();
      }
    };
  }, [acceptSnapshot, sessionId]);

  return { isConnected, snapshot, error, activity, acceptSnapshot };
}
