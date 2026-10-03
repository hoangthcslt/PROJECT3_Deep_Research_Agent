/**
 * ResearchProgress Page — Screen 2: Real-time Progress & HITL
 * 
 * Displays pipeline progress, live activity feed, discovered sources,
 * and HITL modals for plan approval and source selection.
 * Maps from brainstorm: ui_ux.md (Screen 2).
 */

import { useParams } from "react-router-dom";
import { useResearchWebSocket } from "../hooks/useResearchWebSocket";
import type { ResearchStep } from "../types/research";

const STEP_LABELS: Record<ResearchStep, string> = {
  idle: "Chờ",
  planning: "Lập kế hoạch",
  searching: "Tìm kiếm",
  reading: "Đọc tài liệu",
  extracting: "Trích xuất",
  reflecting: "Phản tư",
  synthesizing: "Tổng hợp",
  done: "Hoàn tất",
  error: "Lỗi",
};

const PIPELINE_STEPS: ResearchStep[] = [
  "planning",
  "searching",
  "reading",
  "extracting",
  "reflecting",
  "synthesizing",
];

export default function ResearchProgress() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const {
    isConnected,
    currentStep,
    progress,
    logs,
    hitlTrigger,
    sendMessage,
    clearHitl,
  } = useResearchWebSocket(sessionId ?? null);

  const handleApproveHitl = (action: string, payload: Record<string, unknown> = {}) => {
    sendMessage("HITL_RESPONSE", { action, ...payload });
    clearHitl();
  };

  return (
    <div className="research-progress-page">
      {/* Header */}
      <header className="progress-header">
        <div className="progress-title">
          <span className={`status-dot ${isConnected ? "connected" : "disconnected"}`} />
          <h2>Đang nghiên cứu...</h2>
        </div>
      </header>

      {/* Pipeline Stepper */}
      <div className="pipeline-stepper">
        {PIPELINE_STEPS.map((step, i) => {
          const stepIndex = PIPELINE_STEPS.indexOf(currentStep);
          const isActive = step === currentStep;
          const isCompleted = i < stepIndex;

          return (
            <div
              key={step}
              className={`step ${isActive ? "active" : ""} ${isCompleted ? "completed" : ""}`}
            >
              <div className="step-indicator">
                {isCompleted ? "✔" : isActive ? "🟡" : (i + 1)}
              </div>
              <span className="step-label">{STEP_LABELS[step]}</span>
            </div>
          );
        })}
      </div>

      {/* Progress Bar */}
      <div className="progress-bar-container">
        <div className="progress-bar" style={{ width: `${progress}%` }} />
        <span className="progress-text">{progress}%</span>
      </div>

      {/* Main Content: Activity Feed + Sources */}
      <div className="progress-content">
        {/* Live Activity Feed */}
        <div className="activity-feed">
          <h3>📝 Live Activity Feed</h3>
          <div className="feed-scroll">
            {logs.map((log, i) => (
              <div key={i} className={`log-entry log-${log.type}`}>
                <span className="log-time">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className="log-message">{log.message}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Discovered Sources (placeholder) */}
        <div className="sources-panel">
          <h3>📚 Discovered Sources</h3>
          <p className="placeholder-text">Nguồn tài liệu sẽ xuất hiện khi agent tìm kiếm...</p>
        </div>
      </div>

      {/* HITL Modal */}
      {hitlTrigger && (
        <div className="hitl-modal-overlay">
          <div className="hitl-modal">
            <h3>⏸️ Cần xác nhận</h3>
            <p>{hitlTrigger.data.message as string}</p>

            {/* TODO: Render specific HITL UI based on hitlTrigger.data.type */}

            <div className="hitl-actions">
              <button
                className="btn-approve"
                onClick={() => handleApproveHitl("approve")}
              >
                ✅ Phê duyệt & Tiếp tục
              </button>
              <button
                className="btn-modify"
                onClick={() => handleApproveHitl("modify")}
              >
                ✏️ Chỉnh sửa
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
