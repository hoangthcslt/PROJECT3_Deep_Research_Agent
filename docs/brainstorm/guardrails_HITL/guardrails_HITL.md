Dưới đây là thiết kế chi tiết toàn bộ hệ thống **Guardrails (Hàng rào kiểm soát & Bảo vệ)** cho AI Deep Research Agent, được cấu trúc theo 4 trụ cột: **HITL, Tài nguyên, Nội dung, và Chất lượng**.

---

### TRỤ CỘT 1: HITL CHECKPOINTS (TƯƠNG TÁC NGƯỜI - MÁY)

Áp dụng cơ chế `interrupt()` của LangGraph v0.2+ kết hợp `PostgresSaver` để đóng băng pipeline và chờ phản hồi từ UI React.

```
[Agent lập Plan] ──► (HITL 1: Duyệt Plan) ──► [Agent tìm kiếm] ──► (HITL 2: Chọn Nguồn) 
                                                                           │
[Agent xuất bản] ◄── (HITL 3: Review Report) ◄── [Agent tổng hợp] ◄────────┘
```

#### Checkpoint 1: Duyệt Research Plan (Trước khi Search)
* **Thời điểm kích hoạt:** Sau node `planner`.
* **Dữ liệu gửi lên UI (Interrupt Payload):**
  ```json
  {
    "checkpoint": "PLAN_APPROVAL",
    "question": "Ứng dụng của LangGraph trong Multi-Agent",
    "sub_questions": [
      {"id": "sq_1", "query": "LangGraph state management", "source": "academic"},
      {"id": "sq_2", "query": "LangGraph production latency", "source": "web"}
    ],
    "estimated_cost": {"tavily_calls": 2, "scholar_calls": 2}
  }
  ```
* **Hành động của User:** Thêm, xóa hoặc chỉnh sửa câu hỏi phụ; thay đổi nguồn ưu tiên (Học thuật vs. Web).
* **Resume Logic:** Bấm "Bắt đầu nghiên cứu" $\rightarrow$ Client gửi `Command(resume={"action": "approve", "plan": updated_plan})`.

#### Checkpoint 2: Chọn lọc Nguồn đáng tin (Trước khi Read sâu)
* **Thời điểm kích hoạt:** Sau node `searcher` (Agent đã có danh sách 10–15 links/papers nhưng **chưa đọc nội dung full**).
* **Lý do:** Đọc và parse full-text tốn rất nhiều token và thời gian cào. Người dùng cần đóng vai trò "người gác cổng" lọc các bài rác hoặc bài bị paywall.
* **Dữ liệu gửi lên UI:** Danh sách tài liệu kèm badge uy tín (Tier 1: Học thuật, Tier 2: Docs chính thức, Tier 3: Blog cá nhân), số lượng trích dẫn (citation count), ngày xuất bản.
* **Hành động của User:** Checkbox chọn 3–6 nguồn ưng ý nhất để agent tiến hành đọc sâu.
* **Resume Logic:** Trả về danh sách `approved_source_ids`. Các nguồn bị bỏ chọn sẽ bị xóa khỏi State.

#### Checkpoint 3: Review & Tinh chỉnh Báo cáo (Trước khi Export)
* **Thời điểm kích hoạt:** Sau node `synthesizer`.
* **Dữ liệu gửi lên UI:** Bản nháp Markdown hoàn chỉnh, danh sách trích dẫn tương tác (click vào trích dẫn sẽ highlight đoạn văn bản gốc), đồ thị Neo4j tương ứng.
* **Hành động của User:**
  1. *Chấp thuận (Approve):* Xuất ra PDF/Markdown/Notion.
  2. *Yêu cầu viết lại (Feedback Loop):* Nhập ghi chú (VD: *"Phần so sánh với CrewAI còn ngắn quá, hãy phân tích sâu hơn về memory sharing"*).
* **Resume Logic:** Nếu có feedback $\rightarrow$ LangGraph quay lại `synthesizer` với prompt kèm `user_feedback`.

---

### TRỤ CỘT 2: RESOURCE GUARDRAILS (QUẢN TRỊ NGÂN SÁCH & CHI PHÍ)

Để ngăn việc "cháy ví" API và sập hệ thống do vòng lặp vô tận, xây dựng một module `BudgetTracker` kiểm soát tập trung:

```python
from pydantic import BaseModel, Field
from fastapi import HTTPException

class SessionBudget(BaseModel):
    # API Limits (Per Session)
    max_tavily_calls: int = 4
    current_tavily_calls: int = 0
    
    max_scholar_calls: int = 6
    current_scholar_calls: int = 0
    
    # Loop & Document Limits
    max_loop_iterations: int = 3
    current_loop: int = 0
    
    max_documents_to_read: int = 8
    current_documents_read: int = 0
    
    # Token Budget (Gemini 2.0 Flash)
    max_total_input_tokens: int = 150_000
    current_total_input_tokens: int = 0

    def check_and_increment_search(self, provider: str):
        if provider == "tavily":
            if self.current_tavily_calls >= self.max_tavily_calls:
                raise HTTPException(status_code=429, detail="Vượt quá ngân sách tìm kiếm Web (Tavily) cho phiên này.")
            self.current_tavily_calls += 1
        elif provider == "scholar":
            if self.current_scholar_calls >= self.max_scholar_calls:
                raise HTTPException(status_code=429, detail="Vượt quá ngân sách tìm kiếm học thuật cho phiên này.")
            self.current_scholar_calls += 1
```

* **Max Tokens per LLM Call:**
  * Node `extractor`: Cắt tỉa ngữ cảnh đầu vào tối đa `15,000 tokens` (dùng thư viện `tiktoken` đếm trước khi gửi).
  * Node `synthesizer`: Giới hạn `max_output_tokens = 4096`.
* **Circuit Breaker cho Reflect Loop:**
  * Bắt buộc dừng khi `loop_count >= 3` bất kể LLM có báo "vẫn còn lỗ hổng kiến thức" hay không.

---

### TRỤ CỘT 3: CONTENT GUARDRAILS (CHỐNG ẢO GIÁC & AN TOÀN NỘI DUNG)

#### 1. Ngăn chặn Ảo giác (Hallucination Prevention) & Ép trích dẫn
* **Nguyên tắc "No Citation, No Claim":** Mọi luận điểm thực tế (factual claim) sinh ra ở node `synthesizer` bắt buộc phải kèm tag trích dẫn dạng `[^REF_ID]`.
* **Citation Verification Guardrail Node (Kiểm tra chéo tự động):**
  Thêm một hàm kiểm tra logic trước khi hiển thị báo cáo:
  ```python
  import re

  def citation_guardrail_node(state: DeepResearchState) -> dict:
      report = state.get("report_draft", "")
      valid_source_ids = {s.source_id for s in state.get("sources_found", [])}
      
      # Tìm tất cả trích dẫn dạng [^REF_1], [^REF_2]...
      citations_in_text = set(re.findall(r'\[\^(REF_\d+)\]', report))
      
      # Kiểm tra trích dẫn "ma" (hallucinated sources)
      invalid_citations = citations_in_text - valid_source_ids
      if invalid_citations:
          # Ép LLM chỉnh sửa lại, gỡ bỏ các nguồn không tồn tại
          return {"errors": [f"Phát hiện trích dẫn không hợp lệ: {invalid_citations}"]}
      
      return {"report_approved_by_guardrail": True}
  ```

#### 2. Phân cấp Độ tin cậy Nguồn (Source Credibility Scoring)
Agent tự động gán nhãn uy tín cho mọi link thu thập được:
* **Tier 1 (Độ tin cậy cao - High Trust):** Tên miền `.edu`, `.gov`, DOI URLs, arXiv, IEEE, ACM, Nature, Semantic Scholar.
* **Tier 2 (Độ tin cậy trung bình - Medium Trust):** Blog kỹ thuật từ công ty lớn (Google AI, Meta Engineering, AWS), tài liệu chính thức (Official Docs, GitHub Repos > 1k stars).
* **Tier 3 (Cần cảnh báo - Low Trust / Unverified):** Blog cá nhân (Medium, Dev.to không tên tuổi), Reddit, diễn đàn.
* **Hành vi Guardrail:** Nếu báo cáo phải dùng thông tin từ nguồn **Tier 3**, hệ thống tự động chèn một khối cảnh báo:
  > *⚠️ **Lưu ý:** Luận điểm [X] được trích dẫn từ nguồn blog cá nhân chưa qua bình duyệt học thuật.*

#### 3. Bộ lọc Nội dung Gây hại / Bất hợp pháp (Safety Guardrail)
* **Khai thác Safety Settings của Gemini:** Thiết lập chặn `HARM_CATEGORY_DANGEROUS_CONTENT`, `HARM_CATEGORY_HATE_SPEECH` ở mức `BLOCK_MEDIUM_AND_ABOVE`.
* **System Prompt Guardrail từ chối ngay tại Node Planner:**
  ```text
  Nhiệm vụ của bạn là nghiên cứu học thuật và công nghệ. 
  TUYỆT ĐỐI TỪ CHỐI các yêu cầu:
  - Hướng dẫn chế tạo vũ khí, chất nổ, chất độc hại.
  - Tấn công mạng, bẻ khóa hệ thống (hacking/cracking exploits).
  - Nghiên cứu phục vụ mục đích lừa đảo, thông tin sai lệch có chủ đích.
  Nếu phát hiện, trả về cờ "REJECTED_UNSAFE_TOPIC" và dừng luồng.
  ```

---

### TRỤ CỘT 4: QUALITY GUARDRAILS (ĐẢM BẢO CHẤT LƯỢNG NGHIÊN CỨU)

Trước khi hệ thống chuyển từ giai đoạn Thu thập (`reader`/`reflector`) sang Tổng hợp (`synthesizer`), dữ liệu phải vượt qua bài kiểm tra chất lượng (Quality Gatekeeper):

```
                  ┌─────────────────────────────────────────┐
                  │          QUALITY GATEKEEPER             │
                  └────────────────────┬────────────────────┘
                                       │
            ┌──────────────────────────┴──────────────────────────┐
            ▼                                                     ▼
 [Điều kiện 1: Số lượng]                                [Điều kiện 2: Đa dạng]
  Ít nhất 3 nguồn độc lập?                                Không nguồn nào chiếm > 50%
            │                                             luận điểm cốt lõi?
            ├── ĐẠT ───────────► SANG SYNTHESIZER                 │
            │                                                     │
            └── KHÔNG ĐẠT ─────► ÉP TÌM KIẾM THÊM ◄───────────────┘
```

#### 1. Minimum Number of Sources (Ngưỡng tối thiểu)
* **Quy tắc:** Báo cáo không được phép tổng hợp nếu số nguồn hợp lệ đã đọc `< 3`.
* **Xử lý:** Nếu sau vòng lặp mà vẫn chỉ có 1–2 nguồn $\rightarrow$ Bắt buộc kích hoạt Node `searcher` lần nữa với query mở rộng. Nếu vẫn không tìm được $\rightarrow$ Báo lỗi cho người dùng và yêu cầu người dùng upload file PDF thủ công.

#### 2. Diversity Check (Kiểm tra Tính Đa dạng & Khách quan)
* **Vấn đề "Thiên kiến một nguồn" (Single-source Bias):** Tránh trường hợp đọc 5 bài nhưng 90% nội dung chỉ lấy từ đúng 1 bài viết dài của một tác giả.
* **Giải thuật Diversity Check:**
  ```python
  def check_source_diversity(findings: list[ExtractedFinding]) -> bool:
      source_counts = {}
      total_findings = len(findings)
      
      if total_findings == 0:
          return False
          
      for f in findings:
          for s_id in f.source_ids:
              source_counts[s_id] = source_counts.get(s_id, 0) + 1
              
      # Kiểm tra: Có nguồn nào áp đảo (> 50% tổng findings) không?
      for s_id, count in source_counts.items():
          if (count / total_findings) > 0.5 and len(source_counts) > 1:
              return False # Thiếu đa dạng, cần bổ sung góc nhìn khác
              
      return True
  ```

---

### TỔNG KẾT BẢNG QUẢN TRỊ GUARDRAILS CHO ĐỒ ÁN

| Danh mục | Cơ chế Guardrail | Mức độ can thiệp | Phạt / Xử lý khi vi phạm |
|:---|:---|:---|:---|
| **HITL** | Duyệt Plan & Chọn Nguồn | Chặn luồng (Blocker) | Tạm dừng pipeline, chờ tín hiệu từ React UI |
| **Chi phí** | Tavily / Scholar API Budget | Cứng (Hard limit) | Cắt tìm kiếm, ép chuyển sang Synthesizer |
| **Chi phí** | Max 3 loops Reflect | Cứng (Hard limit) | Dừng lặp, xuất báo cáo với dữ liệu hiện có |
| **Nội dung**| Citation Guardrail | Tự động sửa | Gỡ bỏ luận điểm không có nguồn chứng minh |
| **Nội dung**| Nguồn kém tin cậy (Tier 3) | Cảnh báo mềm | Gắn cờ Disclaimer trực tiếp trên giao diện |
| **Chất lượng**| Ít nhất 3 nguồn + Đa dạng | Chặn luồng (Blocker) | Kích hoạt tìm kiếm bù hoặc báo cho User |