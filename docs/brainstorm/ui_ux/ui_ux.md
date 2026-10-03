Dưới đây là bản thiết kế UI/UX toàn diện cho **AI Deep Research Agent**, được tối ưu theo phong cách hiện đại (tương tự Perplexity Pro / Genspark), phân tách rõ ràng theo 4 màn hình chính kèm danh sách React Components và thư viện khuyến nghị.

---

### MÀN HÌNH 1: RESEARCH INPUT (KHỞI TẠO NGHIÊN CỨU)

Màn hình đón tiếp người dùng với giao diện tối giản, tập trung vào việc cấu hình phạm vi nghiên cứu.

```
┌─────────────────────────────────────────────────────────────┐
│  🔍 Deep Research Agent               [⚙️ API Settings]    │
│                                                             │
│  [  Nhập câu hỏi nghiên cứu của bạn...                   ]  │
│  [  (ví dụ: Ứng dụng của LangGraph trong Multi-Agent...)   ]  │
│                                                             │
│  Research Depth:                                            │
│  ( ) Quick (1 loop)   (•) Standard (2 loops)   ( ) Deep (3) │
│                                                             │
│  ┌─── Upload PDF ───────┐   ┌─── Specific URLs ──────────┐  │
│  │ 📄 Kéo thả file PDF   │   │ 🔗 https://arxiv.org/...   │  │
│  │    hoặc bấm để chọn  │   │ 🔗 https://langchain.com.. │  │
│  └──────────────────────┘   └────────────────────────────┘  │
│                                                             │
│                    [ 🚀 Start Research ]                    │
└─────────────────────────────────────────────────────────────┘
```

#### 1. Cấu trúc React Components:
* `ResearchInputContainer`: Bọc toàn bộ layout, căn giữa màn hình.
* `QueryTextArea`: Textarea tự động co giãn theo nội dung (`auto-resize`), hỗ trợ phím tắt `Ctrl + Enter` để submit.
* `DepthSelector`: Dạng Radio Card Group (3 mức: **Quick** - 1 loop/tổng quan, **Standard** - 2 loops/so sánh, **Deep** - 3 loops/học thuật chuyên sâu).
* `PdfDropzone`: Khung kéo thả file PDF, hiển thị badge danh sách file đã tải lên kèm nút Xóa (`Chip` component).
* `UrlInputList`: Danh sách input cho phép người dùng dán các URL chỉ định sẵn để agent đọc ưu tiên.
* `StartButton`: Nút bấm kích hoạt pipeline, disable khi chưa nhập query.

#### 2. Thư viện UI đề xuất:
* **UI Base:** `shadcn/ui` (dùng các primitive của Radix UI: `Textarea`, `RadioGroup`, `Button`, `Badge`).
* **Kéo thả File:** `react-dropzone` (xử lý kéo thả PDF mượt mà, kiểm tra dung lượng < 10MB).
* **Icons:** `lucide-react` (`Search`, `UploadCloud`, `Link2`, `FileText`, `Sparkles`).
* **Animation:** `framer-motion` (hiệu ứng mở rộng các vùng options).

---

### MÀN HÌNH 2: RESEARCH PROGRESS (THEO DÕI THỜI GIAN THỰC & HITL)

Màn hình quan trọng nhất thể hiện tính chất **Autonomous Agent** — hiển thị trực tiếp suy nghĩ của LLM và kích hoạt các điểm tương tác HITL.

```
┌────────────────────────────────────────────────────────────────────────┐
│  ● Đang nghiên cứu: "Ứng dụng LangGraph trong Multi-Agent..." [Hủy]    │
├────────────────────────────────────────────────────────────────────────┤
│  [✔] Plan ──── [🟡] Search ──── [ ] Read & Extract ──── [ ] Synthesize │
├───────────────────────────────────┬────────────────────────────────────┤
│  📝 LIVE ACTIVITY FEED            │  📚 DISCOVERED SOURCES (12)        │
│  [10:02:15] 🔍 Lập xong kế hoạch  │  ┌──────────────────────────────┐  │
│  [10:02:18] 🌐 Query Tavily...    │  │ 📄 LangGraph: Multi-Agent    │  │
│  [10:02:22] 📚 Tìm Semantic Scholar│ │    arXiv:2408.xxxx • 2024    │  │
│  [10:02:25] ⚙️ Đang đọc 5 bài báo..│ │    Tier 1 [Học thuật] ⭐ 45   │  │
│  > Agent: Cần tìm thêm case study │  └──────────────────────────────┘  │
│  [=====================>    ] 65% │  ┌──────────────────────────────┐  │
│                                   │  │ 🌐 CrewAI vs LangGraph Docs  │  │
│                                   │  │    Tier 2 [Kỹ thuật]         │  │
│                                   │  └──────────────────────────────┘  │
└───────────────────────────────────┴────────────────────────────────────┘
```

#### 1. Cấu trúc React Components:
* `ProgressBarStepper`: Thanh trạng thái quy trình (Plan $\rightarrow$ Search $\rightarrow$ Read $\rightarrow$ Reflect $\rightarrow$ Synthesize).
* `LiveTerminalFeed`: Ô cửa sổ Terminal đen/xám ghi log real-time qua WebSocket (stream từng hành động của Agent).
* `DiscoveredSourcesGrid`: Lưới hiển thị các thẻ tài liệu đã tìm thấy:
  * `SourceCard`: Hiển thị Favicon, Tiêu đề, Badge phân hạng nguồn (Tier 1/2/3), Citation count, Link gốc.
* **HITL Modal 1 — `PlanApprovalModal`:**
  * Bật lên khi agent lập xong plan.
  * Hiển thị danh sách các Sub-questions dạng checklist cho phép: Sửa text, Thêm câu hỏi, Xóa bỏ câu hỏi rác.
* **HITL Modal 2 — `SourceSelectionModal`:**
  * Bật lên sau bước search: Bảng danh sách URL/Paper kèm Checkbox để user tick chọn bài nào đáng tin trước khi Agent tốn quota đọc sâu.

#### 2. Thư viện UI đề xuất:
* **Giao tiếp Real-time:** Sử dụng `WebSocket` native hoặc React hook `useWebSocket` để hứng message từ FastAPI.
* **Log Streaming:** `@xterm/xterm` (hoặc custom component với `overflow-y-auto` cuộn mượt bằng `react-scroll-to-bottom`).
* **Modal / Dialog:** `shadcn/ui` (`Dialog`, `Checkbox`, `ScrollArea`).

---

### MÀN HÌNH 3: REPORT VIEW (XEM BÁO CÁO TỔNG HỢP)

Trình bày báo cáo cấu trúc hoàn chỉnh như một bài báo nghiên cứu chuyên sâu, có mục lục và trích dẫn tương tác.

```
┌──────────────────┬─────────────────────────────────────────────────────┐
│ MỤC LỤC          │ 📄 BÁO CÁO NGHIÊN CỨU TOÀN DIỆN                     │
│                  │ [ Xuất PDF ]  [ Xuất Markdown ]  [ Xuất DOCX ]       │
│ • Tóm tắt        ├─────────────────────────────────────────────────────┤
│ • Kiến trúc      │ 1. Tổng quan Kiến trúc LangGraph                     │
│ • Case Studies   │ LangGraph sử dụng mô hình Pregel Graph [^REF_1] để  │
│ • So sánh        │ điều phối trạng thái...                             │
│ • Thảo luận      │                                                     │
│ • Tài liệu [8]   │ 2. Ma trận So sánh Tính năng                        │
│                  │ | Tiêu chí   | LangGraph | CrewAI | AutoGen |       │
│                  │ |------------|-----------|--------|---------|       │
│                  │ | Vòng lặp   | Mạnh [^1] | Yếu    | Khá     |       │
│                  │                                                     │
│                  │ ─────────────────────────────────────────────────── │
│                  │ 📚 Danh mục trích dẫn:                              │
│                  │ [^REF_1]: LangGraph Documentation (2024). [Link]    │
└──────────────────┴─────────────────────────────────────────────────────┘
```

#### 1. Cấu trúc React Components:
* `ReportHeaderBar`: Chứa tiêu đề báo cáo, metadata (thời gian tạo, số nguồn tham khảo) và bộ nút **Export**.
* `TableOfContents`: Sidebar bên trái tự động bóc tách từ các thẻ `<h2>`, `<h3>` trong nội dung; tự highlight mục đang đọc khi cuộn chuột (`Scrollspy`).
* `MarkdownViewer`: Component render nội dung chính.
* `InlineCitationBadge`: Component tùy biến cho các thẻ trích dẫn `[^id]`:
  * Rê chuột (Hover): Hiện Popup tooltip tóm tắt nội dung trích dẫn.
  * Bấm chuột (Click): Cuộn mượt xuống đúng nguồn đó ở mục *References*.
* `ExportDropdown`: Menu xổ xuống hỗ trợ xuất ra: `.pdf`, `.md`, `.docx`.

#### 2. Thư viện UI đề xuất:
* **Markdown Parsing & Syntax Highlighting:**
  * `react-markdown` + `remark-gfm` (hỗ trợ vẽ Table, Checklist).
  * `rehype-slug` & `rehype-autolink-headings` (tự gán ID cho tiêu đề để làm Table of Contents).
  * `rehype-highlight` hoặc `prismjs` (làm đẹp các khối code snippet).
* **Xuất Tài liệu:**
  * **Markdown:** Dùng `file-saver` xuất thẳng file raw `.md`.
  * **DOCX:** Thư viện `docx` (biến Markdown AST thành file Word).
  * **PDF:** Thư viện `html2pdf.js` hoặc dùng CSS `@media print` của trình duyệt để có chất lượng dàn trang đẹp nhất.

---

### MÀN HÌNH 4: KNOWLEDGE GRAPH VISUALIZATION (TRỰC QUAN HÓA ĐỒ THỊ)

Không gian tương tác trực quan 2D giúp người dùng khám phá mạng lưới liên kết giữa Khái niệm, Bài báo và Tác giả từ Neo4j.

```
┌────────────────────────────────────────────────────────────────────────┐
│  🕸️ Đồ thị Tri thức Nghiên cứu        [🔍 Search Node] [Bộ lọc: All ▼]  │
├───────────────────────────────────────────────────┬────────────────────┤
│                                                   │ ℹ️ CHI TIẾT THỰC THỂ│
│        (Author: LangChain)                        │                    │
│                 │                                 │ [Concept]          │
│             [:WROTE]                              │ LangGraph          │
│                 ▼                                 │                    │
│        [Paper: LangGraph WP]                      │ Loại: Framework    │
│            /          \                           │ Tần suất xuất hiện:│
│       [:PROPOSES]   [:USES]                       │ 18 lần trong 4 bài │
│          /              \                         │                    │
│   (Pregel Model)    (StateGraph)                  │ Nguồn liên quan:   │
│                             │                     │ • REF_1 (Doc)      │
│                        [:EXTENDS]                 │ • REF_3 (arXiv)    │
│                             ▼                     │                    │
│                       (Agent Loop)                │ [ Xem các liên kết]│
└───────────────────────────────────────────────────┴────────────────────┘
```

#### 1. Cấu trúc React Components:
* `GraphToolbar`: 
  * Ô tìm kiếm node (`SearchInput`).
  * Bộ lọc loại node (`FilterPills`: Toggle hiển thị `Concept`, `Paper`, `Author`).
  * Nút điều khiển đồ thị: Zoom In, Zoom Out, Fit to Screen, Re-center.
* `InteractiveCanvas`: Không gian vẽ mạng lưới (Nodes có màu và kích thước khác nhau tùy theo mức độ quan trọng/độ tập trung kết nối - Degree Centrality).
* `NodeDetailDrawer`: Thanh Slide-over mở từ bên phải khi click vào 1 Node bất kỳ, hiển thị toàn bộ thuộc tính của node và các liên kết kề.

#### 2. Thư viện UI đề xuất:
* **Vẽ Graph tương tác (Quan trọng nhất):**
  * **`react-force-graph-2d`**: Lựa chọn số 1 cho Đồ án. Vẽ bằng HTML5 Canvas/WebGL cực mượt, tích hợp sẵn thuật toán vật lý lò xo (force-directed), zoom/pan, bắt sự kiện `onNodeClick`, kéo thả node dễ dàng.
  * *(Phương án dự phòng)*: `@xyflow/react` (React Flow) nếu muốn đồ thị theo dạng khối sơ đồ hộp có quy củ hơn.
* **Drawer / Sheet hiển thị chi tiết:** `shadcn/ui` (`Sheet` component).

---

### BẢNG TỔNG HỢP TECH STACK FRONTEND

| Nghiệp vụ UI | Công nghệ / Thư viện đề xuất | Lý do lựa chọn cho Đồ án 3 |
|:---|:---|:---|
| **Core Framework** | **React (Vite) + TypeScript** | Build nhanh, type safety chuẩn chỉ cho state phức tạp. |
| **Component System** | **Tailwind CSS + shadcn/ui** | Đẹp chuẩn phong cách AI hiện đại, dễ can thiệp code. |
| **Realtime Pipeline** | **WebSockets (`react-use-websocket`)** | Nhận log stream mượt mà từ FastAPI mà không bị giật lag. |
| **Markdown View** | **`react-markdown` + `remark-gfm`** | Hiển thị bảng biểu, trích dẫn học thuật hoàn hảo. |
| **Graph Visualization**| **`react-force-graph-2d`** | Tương tác vật lý sống động, trực quan hóa tốt dữ liệu Neo4j. |
| **Export Formats** | **`docx` + `file-saver` + Print CSS** | Hỗ trợ trọn vẹn Word, Markdown và in PDF chuẩn bìa. |