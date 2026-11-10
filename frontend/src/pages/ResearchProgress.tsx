import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { useResearchWebSocket } from "../hooks/useResearchWebSocket";
import { api } from "../services/api";
import type { ResearchResumeRequest, ResearchStep, ResearchSubQuestion, SourceMetadata } from "../types/research";

const STEP_LABELS: Record<string, string> = {
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

const STATUS_LABELS = {
  created: "Chờ bắt đầu",
  running: "Đang chạy",
  awaiting_plan: "Chờ duyệt kế hoạch",
  awaiting_sources: "Chờ chọn nguồn",
  awaiting_report: "Chờ duyệt báo cáo",
  completed: "Hoàn tất",
  error: "Lỗi",
} as const;

const PIPELINE_STEPS: ResearchStep[] = [
  "planning",
  "searching",
  "reading",
  "extracting",
  "reflecting",
  "synthesizing",
];

function sourceTypeLabel(source: SourceMetadata): string {
  if (source.source_type === "paper") return "Bài báo học thuật";
  if (source.source_type === "uploaded_pdf") return "PDF đã tải";
  return "Trang web";
}

function contentKindLabel(source: SourceMetadata): string {
  if (source.content_kind === "abstract") return "Tóm tắt";
  if (source.content_kind === "pdf_excerpt") {
    return source.page_count ? "Trích đoạn PDF · " + source.page_count + " trang" : "Trích đoạn PDF";
  }
  return source.truncated ? "Nội dung trang · đã rút gọn" : "Nội dung trang";
}

function SourceLink({ url, label }: { url?: string | null; label: string }) {
  const href = api.sourceHref(url ?? undefined);
  return href
    ? <a href={href} target="_blank" rel="noopener noreferrer">{label}</a>
    : <span>{label}</span>;
}

export default function ResearchProgress() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const { isConnected, snapshot, error: statusError, activity, acceptSnapshot } = useResearchWebSocket(sessionId ?? null);
  const [plan, setPlan] = useState<ResearchSubQuestion[]>([]);
  const [selectedSourceIds, setSelectedSourceIds] = useState<string[]>([]);
  const [actionError, setActionError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const submittingRef = useRef(false);
  const currentSessionRef = useRef(sessionId);
  const activeInterruptRef = useRef<string | null>(null);
  const sourceSelectionInterruptRef = useRef<string | null>(null);
  currentSessionRef.current = sessionId;

  const pending = snapshot?.pending_interrupt ?? null;
  const planInterrupt = snapshot?.status === "awaiting_plan" && pending?.type === "PLAN_APPROVAL_REQUIRED"
    ? pending
    : null;
  const sourceInterrupt = snapshot?.status === "awaiting_sources" && pending?.type === "SOURCE_SELECTION_REQUIRED"
    ? pending
    : null;
  const planInterruptId = planInterrupt?.interrupt_id ?? null;
  const sourceInterruptId = sourceInterrupt?.interrupt_id ?? null;
  const originalPlan = planInterrupt?.plan ?? snapshot?.research_plan ?? [];
  const isPlanDirty = JSON.stringify(plan) !== JSON.stringify(originalPlan);

  useEffect(() => {
    activeInterruptRef.current = null;
    sourceSelectionInterruptRef.current = null;
    submittingRef.current = false;
    setPlan([]);
    setSelectedSourceIds([]);
    setActionError("");
    setIsSubmitting(false);
  }, [sessionId]);

  useEffect(() => {
    if (!planInterruptId) {
      activeInterruptRef.current = null;
      return;
    }
    if (activeInterruptRef.current === planInterruptId) return;
    activeInterruptRef.current = planInterruptId;
    setPlan((planInterrupt.plan ?? snapshot?.research_plan ?? []).map((question) => ({ ...question })));
    setActionError("");
  }, [planInterruptId, planInterrupt?.plan, snapshot?.research_plan]);

  useEffect(() => {
    if (!sourceInterruptId) {
      sourceSelectionInterruptRef.current = null;
      return;
    }
    if (sourceSelectionInterruptRef.current === sourceInterruptId) return;
    sourceSelectionInterruptRef.current = sourceInterruptId;
    setSelectedSourceIds(snapshot?.selected_source_ids ?? []);
    setActionError("");
  }, [sourceInterruptId, snapshot?.selected_source_ids]);

  const beginRequest = () => {
    if (submittingRef.current) return false;
    submittingRef.current = true;
    setIsSubmitting(true);
    setActionError("");
    return true;
  };

  const finishRequest = (requestSessionId: string) => {
    if (currentSessionRef.current !== requestSessionId) return;
    submittingRef.current = false;
    setIsSubmitting(false);
  };

  const handleStart = async () => {
    if (!sessionId || snapshot?.status !== "created" || !beginRequest()) return;
    const requestSessionId = sessionId;
    try {
      const response = await api.runResearch(requestSessionId);
      if (currentSessionRef.current === requestSessionId) acceptSnapshot(response);
    } catch (error) {
      if (currentSessionRef.current === requestSessionId) {
        setActionError(error instanceof Error ? error.message : "Không thể bắt đầu nghiên cứu.");
      }
    } finally {
      finishRequest(requestSessionId);
    }
  };

  const handleDecision = async (action: "approve" | "modify") => {
    if (!sessionId || !pending || !beginRequest()) return;
    const requestSessionId = sessionId;
    let request: ResearchResumeRequest = { action: "approve", interrupt_id: pending.interrupt_id };

    if (action === "modify") {
      if (snapshot?.status !== "awaiting_plan" || pending.type !== "PLAN_APPROVAL_REQUIRED") {
        finishRequest(requestSessionId);
        return;
      }
      const normalizedPlan = plan.map((question) => ({
        ...question,
        id: question.id.trim(),
        question: question.question.trim(),
      }));
      const ids = normalizedPlan.map((question) => question.id);
      const duplicateIds = new Set(ids.filter((id, index) => id && ids.indexOf(id) !== index));
      if (!normalizedPlan.length) setActionError("Kế hoạch cần có ít nhất một câu hỏi.");
      else if (normalizedPlan.some((question) => !question.id)) setActionError("Một câu hỏi thiếu mã nội bộ; hãy xóa câu đó rồi thêm lại.");
      else if (duplicateIds.size > 0) setActionError("Một số câu hỏi bị trùng mã nội bộ; hãy sửa mã bị trùng.");
      else if (normalizedPlan.some((question) => !question.question)) setActionError("Nội dung câu hỏi không được để trống.");
      else request = { action: "modify", interrupt_id: pending.interrupt_id, plan: normalizedPlan };
      if (request.action !== "modify") {
        finishRequest(requestSessionId);
        return;
      }
    } else if (snapshot?.status !== "awaiting_plan" || pending.type !== "PLAN_APPROVAL_REQUIRED") {
      if (snapshot?.status !== "awaiting_report" || pending.type !== "REPORT_APPROVAL_REQUIRED") {
        finishRequest(requestSessionId);
        return;
      }
    }

    try {
      const response = await api.resumeResearch(requestSessionId, request);
      if (currentSessionRef.current === requestSessionId) acceptSnapshot(response);
    } catch (error) {
      if (currentSessionRef.current === requestSessionId) {
        setActionError(error instanceof Error ? error.message : "Không thể gửi quyết định.");
      }
    } finally {
      finishRequest(requestSessionId);
    }
  };

  const handleSourceSelection = async () => {
    if (!sessionId || !sourceInterrupt) return;
    const selected = [...new Set(selectedSourceIds)];
    const allowedIds = new Set(sourceInterrupt.sources.map((source) => source.source_id));
    if (selected.length === 0) {
      setActionError("Hãy chọn ít nhất một nguồn.");
      return;
    }
    if (selected.length > 8 || selected.some((sourceId) => !allowedIds.has(sourceId))) {
      setActionError("Hãy chọn tối đa 8 nguồn trong danh sách hiện tại.");
      return;
    }
    if (!beginRequest()) return;

    const requestSessionId = sessionId;
    const request: ResearchResumeRequest = {
      action: "select_sources",
      interrupt_id: sourceInterrupt.interrupt_id,
      selected_source_ids: selected,
    };
    try {
      const response = await api.resumeResearch(requestSessionId, request);
      if (currentSessionRef.current === requestSessionId) acceptSnapshot(response);
    } catch (error) {
      if (currentSessionRef.current === requestSessionId) {
        setActionError(error instanceof Error ? error.message : "Không thể gửi lựa chọn nguồn.");
      }
    } finally {
      finishRequest(requestSessionId);
    }
  };

  const toggleSource = (sourceId: string, checked: boolean) => {
    if (!checked) {
      setActionError("");
      setSelectedSourceIds((current) => current.filter((item) => item !== sourceId));
      return;
    }
    if (selectedSourceIds.includes(sourceId)) return;
    if (selectedSourceIds.length >= 8) {
      setActionError("Có thể chọn tối đa 8 nguồn.");
      return;
    }
    setActionError("");
    setSelectedSourceIds((current) => current.includes(sourceId) ? current : [...current, sourceId]);
  };

  const addQuestion = () => setPlan((current) => {
    let suffix = 1;
    while (current.some((question) => question.id.trim() === "sq_" + suffix)) suffix += 1;
    return [...current, { id: "sq_" + suffix, question: "", target_source: "web", status: "pending" }];
  });

  const updateQuestion = (index: number, update: Partial<ResearchSubQuestion>) => {
    setPlan((current) => current.map((question, i) => i === index ? { ...question, ...update } : question));
  };

  const submitModifiedPlan = (event: FormEvent) => {
    event.preventDefault();
    void handleDecision("modify");
  };

  if (!sessionId) {
    return <main className="research-progress-page"><p className="error-message" role="alert">Không tìm thấy mã phiên nghiên cứu.</p></main>;
  }

  const progress = snapshot?.progress_percent ?? 0;
  const activeStep = snapshot?.current_step ?? "idle";
  const currentStepIndex = PIPELINE_STEPS.indexOf(activeStep as ResearchStep);
  const stepLabel = STEP_LABELS[activeStep] ?? activeStep;
  const sourceCandidates = sourceInterrupt?.sources ?? [];
  const candidateIds = new Set(sourceCandidates.map((source) => source.source_id));
  const historicalSources = (snapshot?.sources_found ?? []).filter(
    (source) => !sourceInterrupt || !candidateIds.has(source.source_id),
  );

  return (
    <main className="research-progress-page">
      <header className="progress-header">
        <div>
          <div className="progress-title">
            <span className={"status-dot " + (isConnected ? "connected" : "disconnected")} aria-hidden="true" />
            <h1>Tiến độ nghiên cứu</h1>
          </div>
          <p className="connection-status" role="status" aria-live="polite">
            {snapshot ? STATUS_LABELS[snapshot.status] : "Đang tải trạng thái phiên..."}
            {" · "}{isConnected ? "Đã kết nối trực tiếp" : "Chưa kết nối trực tiếp"}
          </p>
        </div>
      </header>

      {statusError && <p className="error-message" role="alert">{statusError}</p>}
      {actionError && <p className="error-message" role="alert">{actionError}</p>}
      {snapshot?.status === "error" && snapshot.error && <p className="error-message" role="alert">{snapshot.error}</p>}
      {snapshot && snapshot.source_errors.length > 0 && (
        <section className="source-errors" aria-labelledby="source-errors-heading" role="alert">
          <h2 id="source-errors-heading">Một số nguồn chưa đọc được</h2>
          <ul>{snapshot.source_errors.map((message, index) => <li key={index}>{message}</li>)}</ul>
        </section>
      )}

      {snapshot && (
        <>
          <section aria-label="Tiến độ các bước nghiên cứu">
            <div className="pipeline-stepper">
              {PIPELINE_STEPS.map((step, index) => {
                const isActive = step === activeStep;
                const isCompleted = snapshot.status === "completed" || (currentStepIndex >= 0 && index < currentStepIndex);
                return (
                  <div key={step} className={"step " + (isActive ? "active " : "") + (isCompleted ? "completed" : "")}>
                    <span className="step-indicator" aria-hidden="true">{isCompleted ? "✔" : index + 1}</span>
                    <span className="step-label">{STEP_LABELS[step]}</span>
                  </div>
                );
              })}
            </div>
            <div
              className="progress-bar-container"
              role="progressbar"
              aria-label="Phần trăm hoàn thành"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress}
              aria-valuetext={progress + "%"}
            >
              <div className="progress-bar" style={{ width: progress + "%" }} />
              <span className="progress-text">{progress}%</span>
            </div>
            <p className="current-step">Bước hiện tại: {stepLabel}</p>
          </section>

          <div className="progress-content">
            <section className="activity-feed" aria-labelledby="activity-heading">
              <h2 id="activity-heading">Hoạt động gần đây</h2>
              <div className="feed-scroll" aria-live="polite">
                {activity.length === 0 ? <p>Đang chờ cập nhật từ phiên nghiên cứu...</p> : activity.map((entry, index) => (
                  <div key={entry.timestamp + "-" + index} className={"log-entry log-" + entry.type}>
                    <time className="log-time" dateTime={entry.timestamp}>{new Date(entry.timestamp).toLocaleTimeString()}</time>
                    <span className="log-message">{entry.message}</span>
                  </div>
                ))}
              </div>
            </section>

            <section className="sources-panel" aria-labelledby="plan-heading">
              <h2 id="plan-heading">Kế hoạch nghiên cứu</h2>
              {planInterrupt ? (
                <>
                  <p>{planInterrupt.message}</p>
                  <form className="plan-editor" onSubmit={submitModifiedPlan}>
                    {plan.map((question, index) => (
                      <fieldset className="plan-question" key={question.id + "-" + index} disabled={isSubmitting}>
                        <legend>Câu hỏi {index + 1}</legend>
                        <label htmlFor={"question-text-" + index}>Nội dung câu hỏi</label>
                        <textarea
                          id={"question-text-" + index}
                          rows={2}
                          value={question.question}
                          onChange={(event) => updateQuestion(index, { question: event.target.value })}
                        />
                        <label htmlFor={"question-source-" + index}>Loại nguồn</label>
                        <select
                          id={"question-source-" + index}
                          value={question.target_source}
                          onChange={(event) => updateQuestion(index, { target_source: event.target.value as ResearchSubQuestion["target_source"] })}
                        >
                          <option value="web">Web</option>
                          <option value="academic">Học thuật</option>
                        </select>
                        <button
                          type="button"
                          className="btn-remove"
                          onClick={() => setPlan((current) => current.filter((_, i) => i !== index))}
                          aria-label={"Xóa câu hỏi " + (index + 1)}
                        >Xóa câu hỏi</button>
                      </fieldset>
                    ))}
                    <div className="plan-actions">
                      <button type="button" className="btn-modify" onClick={addQuestion} disabled={isSubmitting}>Thêm câu hỏi</button>
                      <button
                        type="button"
                        className="btn-approve"
                        onClick={() => void handleDecision("approve")}
                        disabled={isSubmitting || isPlanDirty}
                      >{isSubmitting ? "Đang gửi..." : "Phê duyệt kế hoạch gốc"}</button>
                      <button type="submit" className="btn-modify" disabled={isSubmitting}>
                        {isSubmitting ? "Đang gửi..." : "Gửi kế hoạch đã sửa"}
                      </button>
                    </div>
                    {isPlanDirty && <p>Hãy gửi kế hoạch đã sửa để áp dụng thay đổi.</p>}
                  </form>
                </>
              ) : snapshot.research_plan.length > 0 ? (
                <ol className="research-plan-list">
                  {snapshot.research_plan.map((question, index) => (
                    <li key={question.id + "-" + index}>
                      <strong>{question.id}</strong>
                      <p>{question.question}</p>
                      <span>{question.target_source === "academic" ? "Học thuật" : "Web"} · {question.status}</span>
                    </li>
                  ))}
                </ol>
              ) : <p className="placeholder-text">Kế hoạch sẽ xuất hiện sau khi agent lập xong.</p>}

              {snapshot.status === "created" && (
                <div className="plan-actions">
                  <p>Phiên đã tạo và đang chờ lệnh bắt đầu.</p>
                  <button type="button" className="btn-start" onClick={() => void handleStart()} disabled={isSubmitting}>
                    {isSubmitting ? "Đang bắt đầu..." : "Bắt đầu nghiên cứu"}
                  </button>
                </div>
              )}

              {snapshot.status === "completed" && (
                <div className="plan-actions">
                  <p>Nghiên cứu đã hoàn tất; báo cáo cuối đã sẵn sàng.</p>
                  <Link className="btn-start" to={"/report/" + sessionId}>Xem báo cáo cuối</Link>
                </div>
              )}

              {snapshot.status === "awaiting_report" && pending?.type === "REPORT_APPROVAL_REQUIRED" && (
                <div className="report-approval">
                  <p>{pending.message}</p>
                  {pending.report_draft && <pre className="report-draft">{pending.report_draft}</pre>}
                  <Link to={"/report/" + sessionId}>Mở bản nháp đầy đủ</Link>
                  <button type="button" className="btn-approve" onClick={() => void handleDecision("approve")} disabled={isSubmitting}>
                    {isSubmitting ? "Đang gửi..." : "Phê duyệt báo cáo"}
                  </button>
                </div>
              )}
            </section>
          </div>

          {sourceInterrupt && (
            <section className="source-selection-panel" aria-labelledby="source-selection-heading">
              <h2 id="source-selection-heading">Chọn nguồn để đọc</h2>
              <p>{sourceInterrupt.message} Chọn từ 1 đến 8 nguồn rồi gửi lựa chọn.</p>
              {sourceCandidates.length > 0 ? (
                <div className="source-table-wrap">
                  <table className="source-table">
                    <thead>
                      <tr><th scope="col">Chọn</th><th scope="col">Tiêu đề và liên kết</th><th scope="col">Loại nguồn</th><th scope="col">Nội dung</th></tr>
                    </thead>
                    <tbody>
                      {sourceCandidates.map((source) => {
                        const checked = selectedSourceIds.includes(source.source_id);
                        const checkboxId = "source-choice-" + source.source_id;
                        return (
                          <tr key={source.source_id}>
                            <td>
                              <input
                                id={checkboxId}
                                type="checkbox"
                                checked={checked}
                                disabled={isSubmitting || (!checked && selectedSourceIds.length >= 8)}
                                onChange={(event) => toggleSource(source.source_id, event.target.checked)}
                                aria-label={"Chọn nguồn " + source.title}
                              />
                            </td>
                            <td>
                              <label htmlFor={checkboxId}><strong>{source.title}</strong></label>
                              <div className="source-links">
                                {source.url && <SourceLink url={source.url} label={source.source_type === "uploaded_pdf" ? "Mở PDF đã tải" : "Mở nguồn"} />}
                                {source.open_access_pdf && <SourceLink url={source.open_access_pdf} label="PDF truy cập mở" />}
                              </div>
                            </td>
                            <td>{sourceTypeLabel(source)}</td>
                            <td>
                              <strong>{contentKindLabel(source)}</strong>
                              {source.content_snippet && <p className="source-snippet">{source.content_snippet}</p>}
                              {source.truncated && source.content_kind === "pdf_excerpt" && <span className="source-truncated">Trích đoạn được rút gọn</span>}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : <p className="placeholder-text">Chưa có nguồn khả dụng để chọn.</p>}
              <div className="plan-actions">
                <p>{selectedSourceIds.length}/8 nguồn đã chọn</p>
                <button
                  type="button"
                  className="btn-approve"
                  onClick={() => void handleSourceSelection()}
                  disabled={isSubmitting || selectedSourceIds.length === 0 || sourceCandidates.length === 0}
                >{isSubmitting ? "Đang gửi..." : "Gửi lựa chọn nguồn"}</button>
              </div>
            </section>
          )}

          {historicalSources.length > 0 && (
            <section className="source-history-panel" aria-labelledby="source-history-heading">
              <h2 id="source-history-heading">Lịch sử nguồn ({historicalSources.length})</h2>
              <ul className="source-history-list">
                {historicalSources.map((source) => (
                  <li key={source.source_id}>
                    <div>
                      <strong>{source.title}</strong>
                      <span>{sourceTypeLabel(source)} · {contentKindLabel(source)}</span>
                      {snapshot.selected_source_ids.includes(source.source_id) && <span className="source-selected-label">Đã chọn để đọc</span>}
                    </div>
                    <div className="source-links">
                      {source.url && <SourceLink url={source.url} label={source.source_type === "uploaded_pdf" ? "Mở PDF đã tải" : "Mở nguồn"} />}
                      {source.open_access_pdf && <SourceLink url={source.open_access_pdf} label="PDF truy cập mở" />}
                    </div>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </>
      )}
    </main>
  );
}
