/**
 * ResearchInput Page — Screen 1: Research Configuration
 * 
 * User enters research question, selects depth, uploads PDFs, and provides URLs.
 * Maps from brainstorm: ui_ux.md (Screen 1).
 */

import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Search, UploadCloud, Link2, Sparkles } from "lucide-react";
import { api } from "../services/api";
import type { ResearchStartRequest } from "../types/research";

type Depth = "quick" | "standard" | "deep";

const DEPTH_OPTIONS: { value: Depth; label: string; description: string; loops: string }[] = [
  { value: "quick", label: "⚡ Quick", description: "Tổng quan nhanh", loops: "1 loop" },
  { value: "standard", label: "📊 Standard", description: "So sánh & phân tích", loops: "2 loops" },
  { value: "deep", label: "🔬 Deep", description: "Học thuật chuyên sâu", loops: "3 loops" },
];

export default function ResearchInput() {
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");
  const [depth, setDepth] = useState<Depth>("standard");
  const [urls, setUrls] = useState<string[]>([""]);
  const [files, setFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!question.trim() || question.length < 10) {
      setError("Câu hỏi nghiên cứu cần ít nhất 10 ký tự.");
      return;
    }

    setIsLoading(true);
    setError("");

    try {
      const request: ResearchStartRequest = {
        question: question.trim(),
        depth,
        urls: urls.filter((u) => u.trim()),
      };

      const response = await api.startResearch(request);

      // Upload PDFs if any
      for (const file of files) {
        await api.uploadPdf(response.session_id, file);
      }

      // Navigate to progress page
      navigate(`/research/${response.session_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Đã xảy ra lỗi");
    } finally {
      setIsLoading(false);
    }
  };

  const addUrl = () => setUrls([...urls, ""]);
  const removeUrl = (index: number) => setUrls(urls.filter((_, i) => i !== index));
  const updateUrl = (index: number, value: string) => {
    const updated = [...urls];
    updated[index] = value;
    setUrls(updated);
  };

  const handleFileDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const droppedFiles = Array.from(e.dataTransfer.files).filter(
      (f) => f.type === "application/pdf"
    );
    setFiles((prev) => [...prev, ...droppedFiles]);
  };

  return (
    <div className="research-input-page">
      <div className="input-container">
        <header className="input-header">
          <Search size={32} />
          <h1>Deep Research Agent</h1>
          <p className="subtitle">Trợ lý nghiên cứu & tổng hợp tri thức đa nguồn</p>
        </header>

        <form onSubmit={handleSubmit} className="research-form">
          {/* Query Input */}
          <div className="form-group">
            <label htmlFor="research-question">Câu hỏi nghiên cứu</label>
            <textarea
              id="research-question"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ví dụ: Ứng dụng của LangGraph trong hệ thống Multi-Agent, tổng hợp thành báo cáo tiếng Việt..."
              rows={3}
              className="query-textarea"
            />
          </div>

          {/* Depth Selector */}
          <div className="form-group">
            <label>Độ sâu nghiên cứu</label>
            <div className="depth-selector">
              {DEPTH_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  type="button"
                  className={`depth-card ${depth === opt.value ? "active" : ""}`}
                  onClick={() => setDepth(opt.value)}
                >
                  <span className="depth-label">{opt.label}</span>
                  <span className="depth-desc">{opt.description}</span>
                  <span className="depth-loops">{opt.loops}</span>
                </button>
              ))}
            </div>
          </div>

          {/* PDF Upload */}
          <div className="form-group">
            <label><UploadCloud size={16} /> Upload PDF</label>
            <div
              className="pdf-dropzone"
              onDrop={handleFileDrop}
              onDragOver={(e) => e.preventDefault()}
            >
              <p>Kéo thả file PDF hoặc <label htmlFor="pdf-input" className="browse-link">bấm để chọn</label></p>
              <input
                id="pdf-input"
                type="file"
                accept=".pdf"
                multiple
                style={{ display: "none" }}
                onChange={(e) => {
                  if (e.target.files) {
                    setFiles((prev) => [...prev, ...Array.from(e.target.files!)]);
                  }
                }}
              />
            </div>
            {files.length > 0 && (
              <div className="file-chips">
                {files.map((f, i) => (
                  <span key={i} className="file-chip">
                    📄 {f.name}
                    <button type="button" onClick={() => setFiles(files.filter((_, j) => j !== i))}>×</button>
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* URL Inputs */}
          <div className="form-group">
            <label><Link2 size={16} /> URLs cụ thể (tùy chọn)</label>
            {urls.map((url, i) => (
              <div key={i} className="url-input-row">
                <input
                  type="url"
                  value={url}
                  onChange={(e) => updateUrl(i, e.target.value)}
                  placeholder="https://arxiv.org/abs/..."
                />
                {urls.length > 1 && (
                  <button type="button" onClick={() => removeUrl(i)} className="btn-remove">×</button>
                )}
              </div>
            ))}
            <button type="button" onClick={addUrl} className="btn-add-url">+ Thêm URL</button>
          </div>

          {/* Error */}
          {error && <div className="error-message">{error}</div>}

          {/* Submit */}
          <button
            type="submit"
            className="btn-start"
            disabled={isLoading || question.length < 10}
          >
            <Sparkles size={20} />
            {isLoading ? "Đang khởi tạo..." : "Bắt đầu nghiên cứu"}
          </button>
        </form>
      </div>
    </div>
  );
}
