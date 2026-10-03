## Deep Research Agent — Trợ Lý Nghiên Cứu & Tổng Hợp Tri Thức Đa Nguồn

### Vấn đề thực tế

Sinh viên, nghiên cứu sinh, và nhân viên phân tích đều gặp chung 1 nỗi đau: **Nghiên cứu một chủ đề mới mất rất nhiều thời gian**. Quy trình truyền thống:
1. Tìm kiếm hàng chục bài báo / tài liệu trên Google Scholar, arXiv, web
2. Đọc lướt từng bài, đánh giá độ liên quan
3. Trích xuất ý chính, ghi chú
4. Tổng hợp thành bài phân tích / literature review có trích dẫn
5. Phát hiện lỗ hổng kiến thức, tìm thêm nguồn → lặp lại từ bước 1

→ **AI Deep Research Agent tự động hóa toàn bộ quy trình trên bằng vòng lặp Plan → Search → Read → Synthesize → Reflect.**

### Tại sao đề tài này xuất sắc cho Đồ án 3?

**1. Kỹ thuật agentic ở mức cao nhất — vượt xa RAG đơn giản:**

| Khía cạnh | Đồ án 2 (RAG Chatbot) | Đồ án 3 (Deep Research Agent) |
|:---|:---|:---|
| Workflow | 1 bước: Query → Retrieve → Generate | **Vòng lặp đa bước**: Plan → Search → Read → Extract → Synthesize → Reflect → (lặp lại nếu thiếu) |
| Data source | 3 file CSV tĩnh | **Đa nguồn động**: Web search API (Tavily/SerpAPI), PDF upload, URL scraping |
| Knowledge building | DB nạp 1 lần, không thay đổi | **Tích lũy tri thức**: Mỗi tài liệu đọc được → chunk → embed → thêm vào vector DB → agent ngày càng "biết nhiều hơn" |
| Reasoning | Extract intent → retrieve → answer | **Plan-Execute-Reflect loop**: Agent tự lập kế hoạch nghiên cứu, tự đánh giá kết quả, tự quyết định cần tìm thêm gì |
| Output | Câu trả lời text | **Báo cáo có cấu trúc** với sections, citations, concept map |
| Tool-use | Không | **Nhiều tools**: `search_web()`, `search_papers()`, `read_url()`, `parse_pdf()`, `extract_key_findings()` |
| Graph DB | Lưu specs sản phẩm | **Knowledge Graph**: Đồ thị quan hệ giữa các khái niệm, nguồn tài liệu, tác giả (Neo4j!) |

**2. Nguồn data hoàn toàn thật và miễn phí:**
- **Semantic Scholar API** (miễn phí, không cần auth): Tìm kiếm bài báo học thuật, lấy abstract, citations, metadata
- **Tavily Search API** (miễn phí 1000 requests/tháng): Web search cho nội dung phổ thông
- **PDF upload**: User upload tài liệu của mình → agent đọc, chunk, embed
- **URL scraping**: Agent tự đọc nội dung từ các trang web được user chỉ định

→ **Không có data giả, không mock API, 100% thật và kiểm chứng được.**

**3. Demo flow cực kỳ ấn tượng:**

Ví dụ: User hỏi *"Nghiên cứu về ứng dụng của LangGraph trong hệ thống Multi-Agent, tổng hợp thành báo cáo tiếng Việt"*

Agent tự động thực hiện:
```
Bước 1 (Plan):     "Tôi sẽ tìm 3 mảng: (a) LangGraph architecture,
                     (b) Multi-Agent patterns, (c) Case studies thực tế"

Bước 2 (Search):    Gọi search_papers("LangGraph multi-agent") → 15 kết quả
                     Gọi search_web("LangGraph vs CrewAI vs AutoGen") → 8 kết quả

Bước 3 (Read):      Đọc top 5 bài liên quan nhất, trích xuất key findings

Bước 4 (Reflect):   "Tôi đã có đủ về architecture & patterns, nhưng thiếu
                      case studies thực tế. Cần tìm thêm..."

Bước 5 (Search+):   Gọi search_web("LangGraph production case study 2025")

Bước 6 (Synthesize): Tạo báo cáo 5 phần + bảng so sánh + Knowledge Graph
                      → User review & duyệt trước khi xuất final
```

**4. HITL tự nhiên và hợp lý:**
- User duyệt kế hoạch nghiên cứu trước khi agent bắt đầu tìm kiếm
- User chọn lọc nguồn nào đáng tin để agent đọc sâu
- User review và chỉnh sửa báo cáo tổng hợp trước khi xuất bản
- Governance: Kiểm soát chi phí API (giới hạn số lượt search/phiên)

**5. Tận dụng kỹ năng ĐA2 một cách tự nhiên (không phải "nâng cấp" gượng gạo):**
- **Vector DB (Qdrant)**: Lưu embeddings các tài liệu đã đọc → semantic search trong knowledge base tích lũy
- **Knowledge Graph (Neo4j)**: Concept → liên kết → Source → Author (thay vì Product → Brand)
- **FastAPI + React**: Giữ nguyên stack, nâng cấp UI
- **Embedding Model**: Tái sử dụng hoặc nâng cấp lên multilingual model

### Kiến trúc đề xuất

```
User → React UI (Research Dashboard + Report Editor + Knowledge Graph Viz)
         ↓
     FastAPI Backend + WebSocket (streaming progress)
         ↓
   LangGraph Stateful Workflow:
     ┌─────────────────────────────────────────────────┐
     │                                                  │
     │  [1. Research Planner]                           │
     │     LLM phân tích câu hỏi → lập kế hoạch       │
     │     nghiên cứu (sub-questions, search strategy)  │
     │              ↓                                   │
     │  [2. HITL: User duyệt kế hoạch]                │
     │              ↓                                   │
     │  [3. Multi-Source Searcher]  ← Tool-calling      │
     │     ├─ search_papers()     (Semantic Scholar API) │
     │     ├─ search_web()        (Tavily API)          │
     │     ├─ read_url()          (Web scraper)         │
     │     └─ parse_pdf()         (User uploads)        │
     │              ↓                                   │
     │  [4. Document Reader & Extractor]                │
     │     Chunk documents → Embed → Store to Qdrant    │
     │     Extract key findings, entities, citations     │
     │              ↓                                   │
     │  [5. Knowledge Graph Builder]                    │
     │     Concepts, entities, sources → Neo4j           │
     │              ↓                                   │
     │  [6. Reflection & Gap Analysis]                  │
     │     LLM đánh giá: Đã đủ thông tin chưa?         │
     │     → Nếu chưa: quay lại bước 3 (loop)          │
     │     → Nếu đủ: sang bước 7                       │
     │              ↓                                   │
     │  [7. Report Synthesizer]                         │
     │     LLM tổng hợp báo cáo có cấu trúc            │
     │     + trích dẫn nguồn + concept map              │
     │              ↓                                   │
     │  [8. HITL: User review & export]                 │
     │                                                  │
     └─────────────────────────────────────────────────┘
         ↓
   Qdrant (document embeddings) + Neo4j (knowledge graph) + PostgreSQL (sessions, reports, user data)
```

### Tech Stack cụ thể

| Layer | Công nghệ | Ghi chú |
|:---|:---|:---|
| LLM | Google Gemini 2.x | Đã quen từ ĐA2, hỗ trợ long context (1M tokens) |
| Agent Framework | **LangGraph** | Stateful workflow với cycles (Plan-Execute-Reflect loop) |
| Web Search | **Tavily API** (free tier) | Trả về content sạch, tối ưu cho LLM |
| Academic Search | **Semantic Scholar API** | Miễn phí, giàu metadata (citations, abstract, authors) |
| PDF Parsing | **PyMuPDF / pdfplumber** | Trích xuất text + bảng từ PDF upload |
| Web Scraping | **httpx + BeautifulSoup** | Đọc nội dung URL do user chỉ định |
| Vector DB | **Qdrant** (đã quen) | Tích lũy tri thức qua các phiên nghiên cứu |
| Graph DB | **Neo4j** (đã quen) | Knowledge graph: Concept-Source-Author relationships |
| Database | **PostgreSQL** | Sessions, reports, user preferences |
| Backend | **FastAPI** + WebSocket | Streaming progress real-time |
| Frontend | **React** + **@nivo/network** (graph viz) + **react-markdown** (report render) | Rich UI với graph visualization |
| Deploy | Docker + Vercel/Railway | |

### Tại sao đề tài này khác biệt hoàn toàn với ĐA2?

| Đồ án 2 | Deep Research Agent |
|:---|:---|
| Trả lời câu hỏi dựa trên DB tĩnh | **Tự đi tìm kiến thức mới** từ internet |
| 1 bước: hỏi → đáp | **Vòng lặp tự chủ**: lập kế hoạch → tìm → đọc → đánh giá → tìm tiếp |
| Data nạp 1 lần bởi developer | **Data tích lũy liên tục** bởi chính agent |
| Output: chat text | **Output: báo cáo có cấu trúc** + knowledge graph + trích dẫn |
| Không có reflection | **Self-reflection**: agent tự biết mình thiếu gì |






