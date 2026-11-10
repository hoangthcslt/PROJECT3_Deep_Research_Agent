/** Research question setup for Quick research and user-selected sources. */

import { useRef, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { Link2, Search, Sparkles, UploadCloud } from "lucide-react";
import { api } from "../services/api";
import {
  parseResearchUrls,
  validatePdfSelection,
  type ResearchInputError,
} from "../services/researchInputs";
import type { ResearchSearchMode, ResearchStartRequest } from "../types/research";

type Depth = "quick" | "standard" | "deep";

const DEPTH_OPTIONS: { value: Depth; label: string; description: string; loops: string; available: boolean }[] = [
  { value: "quick", label: "⚡ Nhanh", description: "Tổng quan nhanh", loops: "1 vòng", available: true },
  { value: "standard", label: "📊 Tiêu chuẩn (chưa hỗ trợ)", description: "Chưa khả dụng", loops: "2 vòng", available: false },
  { value: "deep", label: "🔬 Chuyên sâu (chưa hỗ trợ)", description: "Chưa khả dụng", loops: "3 vòng", available: false },
];

const SEARCH_MODES: { value: ResearchSearchMode; label: string; description: string }[] = [
  { value: "web", label: "Web", description: "Tìm bài viết và tài liệu trên web." },
  { value: "academic", label: "Học thuật", description: "Tìm bài báo học thuật." },
  { value: "mixed", label: "Kết hợp", description: "Tìm cả nguồn web và bài báo học thuật." },
  { value: "provided", label: "Nguồn của tôi", description: "Chỉ đọc URL và PDF bạn cung cấp; không tự tìm kiếm." },
];

const INPUT_ERROR_MESSAGES: Record<ResearchInputError, string> = {
  too_many_urls: "Chỉ có thể thêm tối đa 8 URL.",
  url_too_long: "Mỗi URL được giới hạn 2.048 ký tự.",
  invalid_url: "Mỗi URL phải bắt đầu bằng http:// hoặc https:// và không chứa thông tin đăng nhập.",
  too_many_pdfs: "Chỉ có thể tải lên tối đa 3 tệp PDF.",
  not_pdf: "Mỗi tệp phải là PDF.",
  pdf_too_large: "Mỗi tệp PDF phải nhỏ hơn hoặc bằng 10 MiB.",
};

export default function ResearchInput() {
  const navigate = useNavigate();
  const [question, setQuestion] = useState("");
  const [depth, setDepth] = useState<Depth>("quick");
  const [searchMode, setSearchMode] = useState<ResearchSearchMode>("web");
  const [urlText, setUrlText] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<File[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const isSubmittingRef = useRef(false);
  const sessionIdRef = useRef<string | null>(null);
  const uploadedFilesRef = useRef(new Set<File>());
  const inputsLocked = sessionId !== null;

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (isSubmittingRef.current) return;
    if (question.trim().length < 10) {
      setError("Câu hỏi nghiên cứu cần ít nhất 10 ký tự.");
      return;
    }

    const parsedUrls = parseResearchUrls(urlText);
    if (parsedUrls.error) {
      setError(INPUT_ERROR_MESSAGES[parsedUrls.error]);
      return;
    }
    if (searchMode === "provided" && parsedUrls.urls.length === 0 && files.length === 0) {
      setError("Hãy thêm ít nhất một URL hoặc PDF khi chọn Nguồn của tôi.");
      return;
    }

    isSubmittingRef.current = true;
    setIsLoading(true);
    setError("");

    try {
      let activeSessionId = sessionIdRef.current;
      if (!activeSessionId) {
        const request: ResearchStartRequest = {
          question: question.trim(),
          depth: "quick",
          urls: parsedUrls.urls,
          search_mode: searchMode,
        };
        const response = await api.startResearch(request);
        activeSessionId = response.session_id;
        sessionIdRef.current = activeSessionId;
        setSessionId(activeSessionId);
      }

      for (const file of files) {
        if (uploadedFilesRef.current.has(file)) continue;
        await api.uploadPdf(activeSessionId, file);
        uploadedFilesRef.current.add(file);
        setUploadedFiles([...uploadedFilesRef.current]);
      }

      await api.runResearch(activeSessionId);
      navigate("/research/" + activeSessionId);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể bắt đầu nghiên cứu.");
    } finally {
      isSubmittingRef.current = false;
      setIsLoading(false);
    }
  };

  const handleFilesChange = (selected: FileList | null) => {
    if (!selected || inputsLocked || isLoading) return;
    const nextFiles = [...files, ...Array.from(selected)];
    const invalid = validatePdfSelection(nextFiles);
    if (invalid) setError(INPUT_ERROR_MESSAGES[invalid]);
    else {
      setFiles(nextFiles);
      setError("");
    }
  };

  const resetSession = () => {
    sessionIdRef.current = null;
    uploadedFilesRef.current.clear();
    setSessionId(null);
    setUploadedFiles([]);
    setError("");
  };

  return (
    <div className="research-input-page">
      <div className="input-container">
        <header className="input-header">
          <Search size={32} />
          <h1>Deep Research Agent</h1>
          <p className="subtitle">Trợ lý nghiên cứu và tổng hợp tri thức đa nguồn</p>
        </header>

        <form onSubmit={handleSubmit} className="research-form">
          <div className="form-group">
            <label htmlFor="research-question">Câu hỏi nghiên cứu</label>
            <textarea
              id="research-question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Ví dụ: Ứng dụng của LangGraph trong hệ thống Multi-Agent, tổng hợp thành báo cáo tiếng Việt..."
              rows={3}
              className="query-textarea"
              disabled={isLoading || inputsLocked}
              required
              minLength={10}
            />
          </div>

          <fieldset className="form-group source-mode-group" disabled={isLoading || inputsLocked}>
            <legend className="form-label">Nguồn tìm kiếm</legend>
            <div className="source-mode-selector">
              {SEARCH_MODES.map((mode) => (
                <label key={mode.value} className={"source-mode-card " + (searchMode === mode.value ? "active" : "")}>
                  <input
                    type="radio"
                    name="search-mode"
                    value={mode.value}
                    checked={searchMode === mode.value}
                    onChange={() => setSearchMode(mode.value)}
                  />
                  <span className="depth-label">{mode.label}</span>
                  <span className="depth-desc">{mode.description}</span>
                </label>
              ))}
            </div>
          </fieldset>

          <div className="form-group">
            <span id="depth-label" className="form-label">Độ sâu nghiên cứu</span>
            <div className="depth-selector" role="group" aria-labelledby="depth-label">
              {DEPTH_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  type="button"
                  className={"depth-card " + (depth === option.value ? "active" : "")}
                  onClick={() => setDepth(option.value)}
                  disabled={isLoading || inputsLocked || !option.available}
                  aria-pressed={depth === option.value}
                >
                  <span className="depth-label">{option.label}</span>
                  <span className="depth-desc">{option.description}</span>
                  <span className="depth-loops">{option.loops}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="research-urls" className="form-label"><Link2 size={16} /> URL cụ thể (tùy chọn)</label>
            <textarea
              id="research-urls"
              value={urlText}
              onChange={(event) => setUrlText(event.target.value)}
              placeholder={"https://example.org/paper\nhttps://example.org/article"}
              rows={3}
              className="query-textarea url-textarea"
              disabled={isLoading || inputsLocked}
              aria-describedby="research-urls-help"
            />
            <p id="research-urls-help" className="placeholder-text">Mỗi dòng một URL http hoặc https; tối đa 8 URL, mỗi URL tối đa 2.048 ký tự.</p>
          </div>

          <div className="form-group">
            <label htmlFor="pdf-input" className="form-label"><UploadCloud size={16} /> Tải tệp PDF</label>
            <div className="pdf-dropzone" aria-disabled={inputsLocked || isLoading}>
              <p>Chọn tối đa 3 tệp PDF, mỗi tệp không quá 10 MiB.</p>
              <input
                id="pdf-input"
                type="file"
                accept="application/pdf,.pdf"
                multiple
                className="pdf-input"
                disabled={isLoading || inputsLocked || files.length >= 3}
                aria-describedby="pdf-input-help"
                onChange={(event) => {
                  handleFilesChange(event.currentTarget.files);
                  event.currentTarget.value = "";
                }}
              />
            </div>
            <p id="pdf-input-help" className="placeholder-text">Tệp tải lên chỉ được dùng trong phiên nghiên cứu này.</p>
            {files.length > 0 && (
              <ul className="file-chips" aria-label="Tệp PDF đã chọn">
                {files.map((file, index) => {
                  const uploaded = uploadedFiles.includes(file);
                  return (
                    <li key={index} className="file-chip">
                      <span>📄 {file.name}{uploaded ? " · Đã tải lên" : " · Chưa tải lên"}</span>
                      <button
                        type="button"
                        className="btn-remove"
                        onClick={() => setFiles((current) => current.filter((item) => item !== file))}
                        disabled={isLoading || inputsLocked}
                        aria-label={"Xóa " + file.name}
                      >×</button>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {sessionId && (
            <div className="upload-recovery" role="status" aria-live="polite">
              <p>
                Phiên tạm {sessionId.slice(0, 8)}: {uploadedFiles.length}/{files.length} PDF đã tải lên.
                {" "}Graph chỉ chạy sau khi mọi tệp đã tải thành công. Nếu gặp lỗi, hãy thử lại để tiếp tục phiên này.
              </p>
              <button type="button" className="btn-modify" onClick={resetSession} disabled={isLoading}>
                Bắt đầu phiên mới
              </button>
            </div>
          )}

          {error && <div className="error-message" role="alert">{error}</div>}

          <button
            type="submit"
            className="btn-start"
            disabled={isLoading || question.trim().length < 10}
          >
            <Sparkles size={20} />
            {isLoading ? "Đang tải nguồn và khởi chạy..." : sessionId ? "Thử lại và bắt đầu nghiên cứu" : "Bắt đầu nghiên cứu"}
          </button>
        </form>
      </div>
    </div>
  );
}
