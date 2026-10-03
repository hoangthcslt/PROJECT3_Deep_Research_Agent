Dưới đây là đặc tả kỹ thuật chi tiết của 5 Tools, Schema cơ sở dữ liệu (Neo4j, Qdrant), và chiến lược quản trị Rate Limit cho hệ thống Deep Research Agent.

---

### PHẦN 1: ĐẶC TẢ CHI TIẾT 5 TOOLS (PYTHON + PYDANTIC V2)

#### Tool 1: `search_papers(query: str, max_results: int = 5)`
* **Công nghệ:** Semantic Scholar Academic Graph API.
* **Mục đích:** Tìm kiếm các bài báo khoa học, lấy trích dẫn và thông tin học thuật chuẩn.
* **Output Schema & Triển khai:**

```python
import httpx
from typing import List, Optional
from pydantic import BaseModel, Field

class AuthorInfo(BaseModel):
    authorId: Optional[str] = None
    name: str

class PaperSearchResult(BaseModel):
    paper_id: str
    title: str
    abstract: Optional[str] = "No abstract available"
    authors: List[str]
    citation_count: int
    year: Optional[int] = None
    url: str

async def search_papers(query: str, max_results: int = 5) -> List[PaperSearchResult]:
    url = "https://api.semanticscholar.org/graph/v1/paper/search"
    params = {
        "query": query,
        "limit": max_results,
        "fields": "paperId,title,abstract,authors,citationCount,year,url,openAccessPdf"
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        if response.status_code == 200:
            data = response.json().get("data", [])
            results = []
            for p in data:
                authors = [a["name"] for a in p.get("authors", []) if "name" in a]
                results.append(PaperSearchResult(
                    paper_id=p.get("paperId", ""),
                    title=p.get("title", ""),
                    abstract=p.get("abstract") or "No abstract",
                    authors=authors,
                    citation_count=p.get("citationCount", 0),
                    year=p.get("year"),
                    url=p.get("url") or f"https://www.semanticscholar.org/paper/{p.get('paperId')}"
                ))
            return results
        return []
```

---

#### Tool 2: `search_web(query: str, max_results: int = 5)`
* **Công nghệ:** Tavily Search Client (`tavily-python`).
* **Mục đích:** Tìm kiếm blog công nghệ, tài liệu docs, case studies thực tế mà bài báo chưa cập nhật.
* **Output Schema & Triển khai:**

```python
from tavily import AsyncTavilyClient
import os

class WebSearchResult(BaseModel):
    title: str
    url: str
    content_snippet: str
    relevance_score: float

async def search_web(query: str, max_results: int = 5) -> List[WebSearchResult]:
    client = AsyncTavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
    response = await client.search(
        query=query, 
        max_results=max_results, 
        search_depth="advanced",
        include_answer=False
    )
    
    results = []
    for item in response.get("results", []):
        results.append(WebSearchResult(
            title=item.get("title", ""),
            url=item.get("url", ""),
            content_snippet=item.get("content", ""),
            relevance_score=item.get("score", 0.0)
        ))
    return results
```

---

#### Tool 3: `read_url(url: str)`
* **Công nghệ:** Jina Reader API (`https://r.jina.ai/`) kết hợp fallback `httpx + BeautifulSoup4`.
* **Mục đích:** Cào toàn bộ nội dung của trang web thành định dạng Clean Markdown để LLM đọc mà không bị rác (menu, ads, cookie banner).
* **Output Schema & Triển khai:**

```python
from datetime import datetime

class WebScrapeResult(BaseModel):
    url: str
    title: str
    full_text: str
    extracted_date: str

async def read_url(url: str) -> WebScrapeResult:
    jina_url = f"https://r.jina.ai/{url}"
    headers = {"Accept": "application/json"}
    
    async with httpx.AsyncClient(timeout=20.0) as client:
        try:
            res = await client.get(jina_url, headers=headers)
            if res.status_code == 200:
                data = res.json().get("data", {})
                return WebScrapeResult(
                    url=url,
                    title=data.get("title", "Untitled Webpage"),
                    full_text=data.get("content", ""),
                    extracted_date=datetime.utcnow().isoformat()
                )
        except Exception:
            pass  # Fallback nếu Jina lỗi: có thể dùng BeautifulSoup cơ bản
        
    return WebScrapeResult(url=url, title="Error", full_text="", extracted_date=datetime.utcnow().isoformat())
```

---

#### Tool 4: `parse_pdf(file_path: str)`
* **Công nghệ:** `pymupdf4llm` (thư viện tốt nhất hiện nay biến PDF thành LLM-ready markdown, giữ nguyên bảng).
* **Output Schema & Triển khai:**

```python
import fitz # PyMuPDF
import pymupdf4llm
from typing import Dict, Any

class PDFParseResult(BaseModel):
    file_path: str
    page_count: int
    metadata: Dict[str, Any]
    tables_detected: int
    full_text: str

def parse_pdf(file_path: str) -> PDFParseResult:
    doc = fitz.open(file_path)
    page_count = doc.page_count
    meta = doc.metadata
    
    # pymupdf4llm tự động chuyển PDF sang markdown chuẩn bao gồm cả markdown tables
    md_text = pymupdf4llm.to_markdown(file_path)
    
    # Ước lượng số bảng dựa vào cú pháp pipe |---|
    tables_count = md_text.count("|---|")
    
    doc.close()
    return PDFParseResult(
        file_path=file_path,
        page_count=page_count,
        metadata=meta,
        tables_detected=tables_count,
        full_text=md_text
    )
```

---

#### Tool 5: `extract_key_findings(document_text: str, research_question: str)`
* **Công nghệ:** LLM Structured Output (Gemini 2.x Flash + LangChain `with_structured_output`).
* **Mục đích:** Không nạp cả văn bản dài vào context tổng hợp; chỉ trích xuất các luận điểm quan trọng, thực thể và trích dẫn.
* **Output Schema & Triển khai:**

```python
from langchain_google_genai import ChatGoogleGenerativeAI

class Entity(BaseModel):
    name: str = Field(description="Tên thực thể (Ví dụ: LangGraph, Actor Model, ReAct)")
    type: str = Field(description="Loại thực thể: Technology, Methodology, Metric, Author")
    description: str = Field(description="Tóm tắt ngắn gọn vai trò của thực thể này")

class Finding(BaseModel):
    claim: str = Field(description="Luận điểm chính hoặc sự thật được phát hiện")
    evidence: str = Field(description="Dữ liệu/trích dẫn cụ thể chứng minh cho luận điểm")
    confidence_score: float = Field(description="Độ tin cậy từ 0.0 đến 1.0")

class ExtractedKnowledge(BaseModel):
    findings: List[Finding]
    entities: List[Entity]
    citations: List[str] = Field(description="Danh sách các tác giả/nguồn được trích dẫn trong văn bản")

async def extract_key_findings(document_text: str, research_question: str) -> ExtractedKnowledge:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    structured_llm = llm.with_structured_output(ExtractedKnowledge)
    
    prompt = f"""
    Bạn là chuyên gia trích xuất thông tin nghiên cứu.
    Câu hỏi nghiên cứu: {research_question}
    Nội dung tài liệu:
    \"\"\"{document_text[:15000]}\"\"\" # Tránh tràn context nếu tài liệu quá dài
    
    Hãy trích xuất các phát hiện quan trọng (findings), các thực thể liên quan (entities)
    và các nguồn tài liệu được bài viết trích dẫn (citations).
    """
    return await structured_llm.ainvoke(prompt)
```

---

### PHẦN 2: SCHEMAS CƠ SỞ DỮ LIỆU

#### 1. Neo4j Schema (Knowledge Graph)
Neo4j dùng để liên kết các thực thể tri thức, phục vụ hiển thị graph tương tác cho người dùng.

```
       (:Author) ──[:AUTHORED]──► (:Paper)
                                     │
           ┌───────────[:PROPOSES]───┼───[:EVALUATES]──────────┐
           ▼                         ▼                         ▼
      (:Concept)                (:Finding)                 (:Benchmark)
           │                         │
           └────[:MENTIONED_IN]──────┘
```

* **Constraints & Indexes (Cypher):**
  ```cypher
  CREATE CONSTRAINT unique_paper_id IF NOT EXISTS FOR (p:Paper) REQUIRE p.paper_id IS UNIQUE;
  CREATE CONSTRAINT unique_concept_name IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE;
  CREATE CONSTRAINT unique_author_name IF NOT EXISTS FOR (a:Author) REQUIRE a.name IS UNIQUE;
  CREATE INDEX finding_session_idx IF NOT EXISTS FOR (f:Finding) ON (f.session_id);
  ```

* **Chi tiết Node Types & Properties:**
  * `(:Paper)`: `paper_id` (STRING), `title` (STRING), `year` (INT), `citations` (INT), `url` (STRING)
  * `(:Concept)`: `name` (STRING), `type` (STRING)
  * `(:Author)`: `name` (STRING)
  * `(:Finding)`: `claim` (STRING), `confidence` (FLOAT), `session_id` (STRING)

* **Relationship Types:**
  * `(:Author)-[:AUTHORED]->(:Paper)`
  * `(:Paper)-[:PROPOSES]->(:Concept)`
  * `(:Paper)-[:CITES]->(:Paper)`
  * `(:Finding)-[:EXTRACTED_FROM]->(:Paper)`
  * `(:Concept)-[:RELATED_TO]->(:Concept)`

---

#### 2. Qdrant Collection Schema (Vector Database)
Qdrant dùng để lưu trữ toàn bộ các đoạn văn bản (chunks) đã cào được từ Web/PDF, phục vụ tìm kiếm ngữ nghĩa theo từng sub-question.

* **Collection Config:**
  * **Collection Name:** `research_knowledge_base`
  * **Vector Dimensions:** `768` (tương thích với model `text-embedding-004` của Google Gemini).
  * **Distance Metric:** `Cosine`.
* **Payload Fields & Indexes:**
  * `session_id`: `keyword` (Đánh index để cô lập dữ liệu giữa các phiên nghiên cứu).
  * `source_id`: `keyword` (ví dụ: "REF_1", "REF_2").
  * `source_type`: `keyword` ("academic_paper", "web_article", "uploaded_pdf").
  * `source_url`: `keyword`.
  * `chunk_index`: `integer`.
  * `page_number`: `integer` (dành cho PDF).
  * `content`: `text` (nội dung text của chunk).

```python
from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance, PayloadSchemaType

client = QdrantClient(url="http://localhost:6333")

# Tạo collection
client.recreate_collection(
    collection_name="research_knowledge_base",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE),
)

# Tạo Payload Indexes để filter cực nhanh theo session_id
client.create_payload_index(
    collection_name="research_knowledge_base",
    field_name="session_id",
    field_schema=PayloadSchemaType.KEYWORD
)
```

---

### PHẦN 3: CHIẾN LƯỢC QUẢN TRỊ RATE LIMITS VÀ CHI PHÍ

| API | Giới hạn Free Tier | Vấn đề tiềm ẩn | Giải pháp kỹ thuật xử lý |
|:---|:---|:---|:---|
| **Tavily Search** | **1,000 requests/tháng** | Dễ cạn quota sau vài chục lần test vòng lặp. | **Budget Control & SQLite Cache** |
| **Semantic Scholar** | **100 requests / 5 phút** (không API key) | Bị mã lỗi `429 Too Many Requests` khi search hàng loạt. | **Token Bucket Rate Limiter + Tenacity Backoff** |

#### 1. Xử lý giới hạn Tavily (Bảo toàn 1000 requests/tháng):
* **Request Budget Guardrail:** Giới hạn mỗi Research Session chỉ được gọi tối đa **4 requests Tavily** (2 ở vòng đầu, tối đa 2 ở vòng Reflect).
* **Aggressive Query Caching (SQLite/Redis):** Lưu hash SHA256 của `query` vào local DB. Nếu search lại cụm từ tương tự $\rightarrow$ lấy từ cache, không tốn 1 request API nào.

#### 2. Xử lý giới hạn Semantic Scholar (100 req / 5 min):
* Sử dụng thư viện `aiolimiter` để làm **Client-side Leaky Bucket** (giới hạn cứng tối đa 15 requests/phút).
* Bọc hàm bằng `tenacity` để tự động Retry với **Exponential Backoff**:

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from aiolimiter import AsyncLimiter

# Khống chế không bao giờ vượt quá 15 req/phút (an toàn tuyệt đối dưới ngưỡng 100 req/5 min)
scholarly_rate_limiter = AsyncLimiter(max_rate=15, time_period=60)

class RateLimitException(Exception):
    pass

@retry(
    reraise=True,
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=2, max=16), # Đợi 2s, 4s, 8s, 16s nếu dính 429
    retry=retry_if_exception_type(RateLimitException)
)
async def safe_paper_search(query: str, max_results: int = 5):
    async with scholarly_rate_limiter:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://api.semanticscholar.org/graph/v1/paper/search",
                params={"query": query, "limit": max_results}
            )
            if res.status_code == 429:
                raise RateLimitException("Semantic Scholar Rate limit reached. Backing off...")
            if res.status_code == 200:
                return res.json()
            return {}
```