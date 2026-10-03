/**
 * ReportView Page — Screen 3: Structured Research Report
 * 
 * Renders the markdown report with table of contents, inline citations,
 * and export buttons (MD, PDF, DOCX).
 * Maps from brainstorm: ui_ux.md (Screen 3).
 */

import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { FileText, Download } from "lucide-react";
import { api } from "../services/api";

export default function ReportView() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const [report, setReport] = useState<string>("");
  const [headings, setHeadings] = useState<{ id: string; text: string; level: number }[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!sessionId) return;

    // TODO: Fetch report from API or WebSocket accumulated chunks
    // For now, use placeholder
    setReport("# Báo cáo đang được tải...\n\nVui lòng chờ agent hoàn tất nghiên cứu.");
    setIsLoading(false);
  }, [sessionId]);

  // Extract headings for Table of Contents
  useEffect(() => {
    const matches = report.matchAll(/^(#{1,3})\s+(.+)$/gm);
    const toc = Array.from(matches).map((m, i) => ({
      id: `heading-${i}`,
      text: m[2],
      level: m[1].length,
    }));
    setHeadings(toc);
  }, [report]);

  const handleExport = async (format: "md" | "pdf" | "docx") => {
    if (!sessionId) return;
    try {
      const blob = await api.exportReport(sessionId, format);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `research_report.${format}`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  return (
    <div className="report-view-page">
      {/* Sidebar: Table of Contents */}
      <aside className="report-toc">
        <h3><FileText size={16} /> Mục lục</h3>
        <nav>
          {headings.map((h) => (
            <a
              key={h.id}
              href={`#${h.id}`}
              className={`toc-item toc-level-${h.level}`}
            >
              {h.text}
            </a>
          ))}
        </nav>
      </aside>

      {/* Main Report Content */}
      <main className="report-content">
        {/* Export Bar */}
        <div className="export-bar">
          <h2>📄 Báo cáo Nghiên cứu</h2>
          <div className="export-buttons">
            <button onClick={() => handleExport("md")} className="btn-export">
              <Download size={14} /> Markdown
            </button>
            <button onClick={() => handleExport("pdf")} className="btn-export">
              <Download size={14} /> PDF
            </button>
            <button onClick={() => handleExport("docx")} className="btn-export">
              <Download size={14} /> DOCX
            </button>
          </div>
        </div>

        {/* Markdown Renderer */}
        <article className="markdown-body">
          {isLoading ? (
            <p>Đang tải báo cáo...</p>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report}
            </ReactMarkdown>
          )}
        </article>
      </main>
    </div>
  );
}
