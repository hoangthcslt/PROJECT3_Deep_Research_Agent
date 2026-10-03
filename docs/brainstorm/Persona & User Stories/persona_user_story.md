
---

### PHẦN 1: USER PERSONAS

#### Persona 1: Sinh viên làm khóa luận / Học viên cao học
* **Đại diện:** Hoàng Minh (22 tuổi, Sinh viên năm cuối ngành Khoa học Máy tính).
* **Bối cảnh:** Đang làm khóa luận tốt nghiệp về *Agentic RAG*, bị ngập trong hàng trăm bài báo trên arXiv, Google Scholar.
* **Nỗi đau (Pain points):**
  * Đọc bài báo rất chậm, mất 3–4 tiếng mới đọc xong 1 bài nhưng không chắc nó có ích cho đề tài không.
  * Khó khăn trong việc viết chương "Tổng quan tình hình nghiên cứu" (Literature Review) và tổng hợp trích dẫn chuẩn APA/IEEE.
  * Dễ bỏ sót các nghiên cứu mới xuất bản trong 3–6 tháng gần nhất.
* **Kỳ vọng:** Agent tìm đúng các bài cốt lõi, trích xuất phương pháp & hạn chế, vẽ sơ đồ cây phả hệ phát triển của công nghệ.

#### Persona 2: Chuyên viên Phân tích Công nghệ / Thị trường (Tech Analyst)
* **Đại diện:** Lan Hương (27 tuổi, Product Analyst tại công ty giải pháp phần mềm).
* **Bối cảnh:** Được sếp giao nhiệm vụ đánh giá kiến trúc: *"Nên dùng Vector DB nào (Qdrant vs Pinecone vs Milvus) cho hệ sinh thái AI của công ty?"*.
* **Nỗi đau (Pain points):**
  * Thông tin trên mạng bị nhiễu bởi các bài PR/Marketing của các hãng.
  * Cần số liệu benchmark thực tế, case studies triển khai production thực tế chứ không phải lý thuyết suông.
  * Phải nộp báo cáo so sánh đa chiều (Chi phí, Hiệu năng, Độ trễ, License) cho CTO trong vòng 2 ngày.
* **Kỳ vọng:** Agent tổng hợp thông tin khách quan, có bảng so sánh ma trận (feature matrix), dẫn chứng nguồn cụ thể.

#### Persona 3: Giảng viên / Nghiên cứu sinh (Academic Researcher)
* **Đại diện:** TS. Lê Tuấn (35 tuổi, Giảng viên Đại học).
* **Bối cảnh:** Cần viết đề xuất nghiên cứu (Research Grant Proposal) hoặc chuẩn bị bài giảng chuyên đề mới.
* **Nỗi đau (Pain points):**
  * Cần phát hiện **"Research Gap"** (lỗ hổng nghiên cứu) — tức là các hướng đi mà các bài báo trước thừa nhận là chưa giải quyết được.
  * Cần một bức tranh toàn cảnh: Tác giả nào là key person trong mảng này? Các phương pháp này liên kết với nhau ra sao?
* **Kỳ vọng:** Agent trích xuất được Knowledge Graph về mối quan hệ giữa các khái niệm/tác giả và chỉ ra mâu thuẫn giữa các kết quả nghiên cứu.

---

### PHẦN 2 & 3: USER STORIES & THIẾT KẾ VÒNG LẶP (LOOPS MAPPING)

| ID | User Story | Luồng thực thi của Agent | Số vòng lặp dự kiến | Lý do số vòng lặp |
|:---|:---|:---|:---:|:---|
| **US1** | **Nghiên cứu chủ đề mới từ con số 0 (Cold-start Research)**<br>*"Là sinh viên, tôi muốn tìm hiểu khái niệm 'Graph RAG', nguyên lý cơ bản và tại sao nó tốt hơn Vector RAG truyền thống."* | 1. **Plan:** Lập 2 hướng (Nguyên lý Graph RAG; So sánh với Vector RAG).<br>2. **Search:** Web search các bài blog kỹ thuật uy tín + 2-3 paper nền tảng.<br>3. **Reflect:** Đã đủ định nghĩa và kiến trúc, nhưng thiếu ví dụ cụ thể.<br>4. **Search+:** Tìm thêm 1 code example hoặc case study.<br>5. **Synthesize:** Xuất báo cáo nhập môn. | **2 vòng lặp** | Vòng 1 lấy khung khái niệm; Vòng 2 tìm ví dụ minh họa trực quan. |
| **US2** | **Tổng quan tài liệu học thuật (Literature Review)**<br>*"Là nghiên cứu sinh, tôi muốn tổng hợp các phương pháp 'Agent Self-Correction' trên LLM công bố từ năm 2023–2025."* | 1. **Plan:** Chia theo taxonomy (Reflexion, Self-RAG, CRAG).<br>2. **Search:** Semantic Scholar lấy top 15 papers có trích dẫn cao.<br>3. **Reflect:** Đã có Reflexion và Self-RAG, nhưng thiếu CRAG và các benchmark chuẩn.<br>4. **Search+:** Semantic Scholar cho cụm từ "CRAG" + arXiv mới nhất.<br>5. **Reflect:** Đầy đủ, chuyển sang trích xuất Knowledge Graph.<br>6. **Synthesize:** Tạo bảng so sánh SOTA + danh mục tài liệu trích dẫn chuẩn IEEE. | **3 vòng lặp**<br>*(Chạm ngưỡng Max)* | Nghiên cứu học thuật đòi hỏi độ sâu, cần ít nhất 2 lần bổ sung nguồn để phủ hết các nhánh giải thuật. |
| **US3** | **So sánh giải pháp công nghệ (Tech Stack Comparison)**<br>*"Là Analyst, tôi muốn so sánh chi phí và hiệu năng giữa Qdrant và Milvus khi scale đến 10 triệu vector."* | 1. **Plan:** Lập tiêu chí so sánh (RAM, Indexing time, Query latency, Cloud pricing).<br>2. **Search:** Tìm kiếm benchmark reports, GitHub issues, và docs chính thức.<br>3. **Reflect:** Đã có thông số kỹ thuật, nhưng thiếu số liệu benchmark độc lập từ bên thứ ba.<br>4. **Search+:** Tìm: *"Qdrant vs Milvus benchmark 10M vectors independent"*.<br>5. **Synthesize:** Tạo báo cáo kèm bảng so sánh ma trận (Feature Matrix). | **2 vòng lặp** | Vòng 1 lấy thông số hãng; Vòng 2 tìm bài kiểm thử thực tế độc lập để đảm bảo tính khách quan. |
| **US4** | **Phân tích đối chiếu PDF nội bộ với tri thức mở (PDF Ingestion + Web Validation)**<br>*"Là sinh viên, tôi muốn upload file PDF đề cương đề tài của mình, agent hãy tìm xem đề tài này đã có ai làm chưa và gợi ý điểm mới."* | 1. **Read PDF:** Agent phân tích PDF $\rightarrow$ trích xuất: Mục tiêu, Phương pháp dự kiến.<br>2. **Plan:** Tạo các query tìm kiếm các đề tài tương tự đã xuất bản.<br>3. **Search:** Semantic Scholar tìm các bài báo có keywords trùng khớp.<br>4. **Reflect:** Đã thấy 3 bài báo có ý tưởng tương đồng $80\%$, cần tìm xem họ có hạn chế gì để user khai thác.<br>5. **Search+:** Đọc sâu vào phần "Limitations & Future Work" của 3 bài đó.<br>6. **Synthesize:** Báo cáo chỉ ra các công trình trùng lặp và đề xuất 2 điểm mới user có thể bổ sung. | **2–3 vòng lặp** | Cần đọc tài liệu đầu vào trước, sau đó mới đi tìm kiếm bên ngoài để đối chứng. |
| **US5** | **Xác minh luận điểm / Fact-checking**<br>*"Là Analyst, tôi cần kiểm chứng thông tin: 'Mô hình DeepSeek-V3 có chi phí train chỉ bằng 1/10 Llama 3 nhưng hiệu năng tương đương' xem có cơ sở không."* | 1. **Plan:** Xác định 2 vế cần chứng minh: Chi phí train thật sự và Benchmark đối đầu.<br>2. **Search:** Tìm DeepSeek-V3 technical report + các bài phân tích độc lập từ SemiAnalysis/HuggingFace.<br>3. **Reflect:** Đã có thông tin chi phí ($6M) và benchmarks. Thông tin đủ minh bạch, không cần tìm thêm.<br>4. **Synthesize:** Báo cáo Fact-check: Xác nhận đúng/sai/có điều kiện, kèm bằng chứng từ paper gốc. | **1 vòng lặp** | Mục tiêu hẹp, nhắm thẳng vào một sự thật cụ thể, thông tin dễ tìm thấy ở nguồn chính thống. |
| **US6** | **Phát hiện Khoảng trống Nghiên cứu (Research Gap Discovery)**<br>*"Là giảng viên, tôi muốn tìm hiểu: Đâu là các rào cản kỹ thuật chưa có lời giải khi ứng dụng Multi-Agent vào ngành Y tế?"* | 1. **Plan:** Chia nhỏ: Rào cản bảo mật dữ liệu (HIPAA), Ảo giác (Hallucination), Trách nhiệm pháp lý.<br>2. **Search:** Tìm các survey papers y tế mới nhất 2024.<br>3. **Reflect:** Đã có vấn đề pháp lý và bảo mật, nhưng rào cản về mặt kỹ thuật thuật toán (Consensus mechanisms) còn mờ nhạt.<br>4. **Search+:** Tìm sâu: *"Multi-agent consensus failure in medical diagnosis"*.<br>5. **Reflect:** Đủ dữ liệu.<br>6. **Synthesize:** Vẽ sơ đồ Knowledge Graph các nguyên nhân - hậu quả và đề xuất các hướng nghiên cứu mở. | **3 vòng lặp** | Bài toán mang tính trừu tượng cao, agent phải đào sâu qua nhiều tầng tài liệu mới bóc tách được "những điều chưa ai làm". |

---

### PHẦN 4: RANH GIỚI HỆ THỐNG (SYSTEM BOUNDARIES: DO vs. DO NOT)

Để bảo vệ đề tài trước hội đồng (tránh bị đánh giá là "công cụ tiếp tay cho gian lận học thuật" hoặc "scope quá rộng không kiểm soát nổi"), bạn cần vạch rõ lằn ranh đỏ sau:

```
┌───────────────────────────────────────────────┬───────────────────────────────────────────────┐
│              AGENT LÀM (DO)                   │           AGENT TUYỆT ĐỐI KHÔNG LÀM           │
│         (Scope & Core Competencies)           │             (Guardrails & Limits)             │
├───────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 1. TỔNG HỢP TRI THỨC (Synthesize)             │ 1. VIẾT HỘ BÀI LUẬN / KHÓA LUẬN (Ghostwriting)│
│    Tạo báo cáo tóm tắt, trích xuất luận điểm, │    Không sinh ra bài luận hoàn chỉnh 50 trang │
│    vẽ bảng biểu so sánh, phân loại kiến thức. │    để nộp trường. Chỉ xuất Research Dossier.  │
├───────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 2. TRÍCH DẪN MINH BẠCH (Grounded Citations)   │ 2. BỊA ĐẶT NGUỒN (No Hallucinated Sources)    │
│    Mọi claim đều có inline citation [^1] trỏ  │    Nếu không tìm thấy bằng chứng, Agent phải  │
│    về URL thật hoặc mã DOI của bài báo.       │    trả lời "Chưa đủ dữ liệu", cấm tự sinh URL│
├───────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 3. HỖ TRỢ CON NGƯỜI (HITL Collaboration)     │ 3. HOẠT ĐỘNG HOÀN TOÀN MÙ QUÁNG (No Blackbox) │
│    Người dùng phê duyệt kế hoạch nghiên cứu,  │    Không tự ý chạy ngầm tốn API; phải báo     │
│    loại bỏ nguồn rác trước khi agent đọc sâu. │    cáo trạng thái từng bước qua Activity Feed.│
├───────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 4. BIỂU DIỄN TRI THỨC ĐA CHIỀU               │ 4. ĐƯA RA QUYẾT ĐỊNH THAY CON NGƯỜI           │
│    Trực quan hóa Concept - Paper - Author qua │    Không khuyên "Bạn PHẢI dùng công nghệ X".  │
│    Knowledge Graph tương tác (Neo4j).         │    Chỉ cung cấp Pros/Cons khách quan.         │
├───────────────────────────────────────────────┼───────────────────────────────────────────────┤
│ 5. TRUY CẬP DỮ LIỆU CÔNG KHAI HỢP PHÁP        │ 5. CRACK PAYWALL HOẶC CÀO DỮ LIỆU BẤT HỢP PHÁP│
│    Chỉ dùng Official APIs (Semantic Scholar,  │    Không bẻ khóa tài liệu trả phí (Elsevier,  │
│    Tavily) hoặc các trang Open Access/arXiv.   │    Springer). Chỉ đọc abstract hoặc Open PDF. │
└───────────────────────────────────────────────┴───────────────────────────────────────────────┘
```
