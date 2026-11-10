import { useEffect, useRef, useState, type ComponentProps } from "react";
import { Link, useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Download } from "lucide-react";
import { api } from "../services/api";
import type { ResearchReportResponse } from "../types/research";

const markdownComponents = {
  a: ({ href, children }: ComponentProps<"a">) => {
    const safeHref = api.sourceHref(href);
    if (!safeHref) return <span>{children}</span>;
    if (safeHref.startsWith("#")) return <a href={safeHref}>{children}</a>;
    return <a href={safeHref} target="_blank" rel="noopener noreferrer">{children}</a>;
  },
};

export default function ReportView() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const currentSessionRef = useRef(sessionId);
  currentSessionRef.current = sessionId;
  const [report, setReport] = useState<ResearchReportResponse | null>(null);
  const [loadError, setLoadError] = useState<{ sessionId: string; message: string } | null>(null);
  const [downloadError, setDownloadError] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isDownloading, setIsDownloading] = useState(false);
  const downloadInFlightRef = useRef(false);

  useEffect(() => {
    setReport(null);
    setLoadError(null);
    setDownloadError("");
    setIsLoading(true);
    setIsDownloading(false);
    downloadInFlightRef.current = false;

    if (!sessionId) {
      setLoadError({ sessionId: "", message: "Không tìm thấy mã phiên nghiên cứu." });
      setIsLoading(false);
      return;
    }

    const controller = new AbortController();
    let active = true;
    api.getResearchReport(sessionId, controller.signal).then((result) => {
      if (!active) return;
      if (result.session_id !== sessionId
        || typeof result.report_markdown !== "string"
        || typeof result.approved !== "boolean") {
        setLoadError({ sessionId, message: "Máy chủ trả về báo cáo không hợp lệ." });
        return;
      }
      setReport(result);
    }).catch((error: unknown) => {
      if (active && !(error instanceof DOMException && error.name === "AbortError")) {
        setLoadError({
          sessionId,
          message: error instanceof Error ? error.message : "Không thể tải báo cáo.",
        });
      }
    }).finally(() => {
      if (active) setIsLoading(false);
    });

    return () => {
      active = false;
      controller.abort();
    };
  }, [sessionId]);

  const currentReport = report?.session_id === sessionId ? report : null;
  const error = loadError?.sessionId === (sessionId ?? "") ? loadError.message : "";
  const markdown = currentReport?.report_markdown ?? "";

  const handleExport = async () => {
    if (!sessionId || !currentReport?.approved || downloadInFlightRef.current) return;
    downloadInFlightRef.current = true;
    setIsDownloading(true);
    setDownloadError("");
    try {
      const blob = await api.exportReport(sessionId, "md");
      if (currentSessionRef.current !== sessionId) return;
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `research_report_${sessionId.slice(0, 8)}.md`;
      document.body.append(anchor);
      anchor.click();
      anchor.remove();
      window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (error) {
      if (currentSessionRef.current === sessionId) {
        setDownloadError(error instanceof Error ? error.message : "Không thể tải báo cáo Markdown.");
      }
    } finally {
      if (currentSessionRef.current === sessionId) {
        downloadInFlightRef.current = false;
        setIsDownloading(false);
      }
    }
  };

  return (
    <main className="report-view-page">
      <section className="report-content" aria-busy={isLoading}>
        <header className="export-bar">
          <div>
            <h1>Báo cáo nghiên cứu</h1>
            {currentReport && <p role="status">{currentReport.approved ? "Báo cáo đã được phê duyệt." : "Bản nháp — cần phê duyệt trước khi tải xuống."}</p>}
          </div>
          <div className="export-buttons" aria-label="Tải báo cáo">
            <button onClick={() => void handleExport()} className="btn-export" disabled={!currentReport?.approved || isDownloading}>
              <Download size={14} /> {isDownloading ? "Đang tải..." : "Tải Markdown"}
            </button>
            <button className="btn-export" disabled title="Xuất PDF chưa được hỗ trợ">PDF (chưa hỗ trợ)</button>
            <button className="btn-export" disabled title="Xuất DOCX chưa được hỗ trợ">DOCX (chưa hỗ trợ)</button>
          </div>
        </header>

        {currentReport && !currentReport.approved && (
          <p className="draft-notice">
            <Link to={`/research/${sessionId}`}>Quay lại tiến độ để phê duyệt bản nháp</Link>
          </p>
        )}
        {currentReport?.approved && <p className="draft-notice"><Link to={`/research/${sessionId}`}>Quay lại tiến độ nghiên cứu</Link></p>}
        {error && <p className="error-message" role="alert">{error}</p>}
        {downloadError && <p className="error-message" role="alert">{downloadError}</p>}

        <article className="markdown-body">
          {isLoading ? <p role="status">Đang tải báo cáo...</p>
            : error ? null
              : currentReport ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
                  {markdown}
                </ReactMarkdown>
              ) : <p>Báo cáo chưa sẵn sàng.</p>}
        </article>
      </section>
    </main>
  );
}
