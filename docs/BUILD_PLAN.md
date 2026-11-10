# Kế hoạch build Deep Research Agent theo phase

Hồ sơ nghiệp vụ, use case, UML, master plan và benchmark hiện được tập hợp tại
[system-analysis/README.md](system-analysis/README.md). Đây là tài liệu cần dùng
để chốt với cô trước khi triển khai các phase tiếp theo.

Trạng thái ngày 2026-11-09: Phase 2 và Phase 3 đã nghiệm thu phần code/test.
Frontend build đạt; 60 test backend đạt, không bỏ qua test nào. Người dùng chọn
chốt code/test trước, tích hợp dịch vụ thật sau. Các gate API/database thật vẫn
được ghi là chưa kiểm chứng trong PHASE3_STATUS.md. Người dùng đã yêu cầu
triển khai Phase 4; phạm vi và thiết kế tại [PHASE4_IMPLEMENTATION.md](PHASE4_IMPLEMENTATION.md).

## Mục tiêu và cách triển khai

Giữ stack hiện tại: React/Vite/TypeScript, FastAPI, LangGraph, Gemini, Tavily,
Semantic Scholar, Qdrant, Neo4j và PostgreSQL. Tái sử dụng code đã có; sửa và nối
các phần còn thiếu theo từng mốc có thể chạy thử.

MVP ở cuối Phase 3: nhập câu hỏi, duyệt kế hoạch, nghiên cứu một vòng từ web,
xem bản nháp, phê duyệt và tải báo cáo Markdown.

Mỗi phase phải có kết quả chạy được, kiểm tra phần logic vừa thay đổi và ghi rõ
giới hạn còn lại. Chỉ chuyển phase khi tiêu chí nghiệm thu đã đạt. Test dùng dữ
liệu cố định để kiểm tra điều phối; xác nhận tích hợp thật phải dùng dịch vụ thật
và ghi rõ kết quả, không lấy test giả lập làm bằng chứng đã chạy API thật.

Ngoại lệ được người dùng cho phép ngày 2026-11-08: tiếp tục Phase 2 trong khi
các kiểm tra build/runtime của Phase 1 còn bị chặn bởi môi trường. Phần source/setup
được review chấp nhận; các tiêu chí chưa chạy vẫn được theo dõi tại PHASE1_STATUS.md,
không được đổi thành đạt chỉ vì đã chuyển phase.

Người dùng tiếp tục yêu cầu sang Phase 3 sau khi review Phase 2. Phần source và
test cục bộ Phase 2 đã được kiểm tra; build/runtime vẫn ghi là chưa xác nhận,
không dùng việc triển khai Phase 3 làm bằng chứng nghiệm thu tích hợp.

Ngày 2026-11-09, người dùng chọn “Chốt code/test trước; tích hợp thật sau”.
Nghiệm thu Phase 3 trong lần này áp dụng cho code, build và test dùng dữ liệu
cố định; không thay thế gate chạy nghiên cứu với API/database thật bên dưới.

## Hiện trạng đã xác nhận

- Frontend đã cài dependencies và build thành công; backend/.venv đã cài đủ
  requirements và pip check đạt. Các lỗi cài đặt trước đó đã được giải quyết.
- Cấu hình local có sẵn; chưa xác nhận kết nối API/database thật.
- Backend đã nối REST chạy/resume graph và WebSocket quan sát trạng thái.
- Trang báo cáo đọc bản nháp/bản đã duyệt, tải Markdown sau khi duyệt.
  PDF/DOCX chưa hỗ trợ và trả 501.
- Session và checkpoint lưu trong RAM. PostgreSQL mới có cấu hình.
- Budget và citation guard đã nối vào Quick pipeline. Quality gate nâng cao và
  nhiều vòng nghiên cứu thuộc phase sau.
- Reader bỏ qua nguồn đã đọc, giới hạn phần index mỗi trang ở 8.000 byte UTF-8.
  PDF/URL riêng và Standard/Deep được ghi rõ là chưa hỗ trợ.
- Qdrant/Neo4j dùng khóa và truy vấn gắn với session để cách ly dữ liệu.
- Test đã phủ FastAPI/WebSocket, LangGraph thật và Qdrant trong bộ nhớ; các
  provider/Neo4j dùng fixture, chưa chứng minh tích hợp dịch vụ thật hay browser.

## Phase 1 — Cài đặt, build và khởi động

**Kết quả:** mở được frontend và backend tại máy phát triển.

- Cài frontend theo package-lock; tạo môi trường Python riêng và cài requirements.
- Xử lý điều kiện truy cập registry/package index; kiểm tra Docker hoặc địa chỉ
  dịch vụ được cấu hình cho Qdrant, Neo4j và PostgreSQL.
- Tạo cấu hình local từ .env.example; kiểm tra khóa API cần thiết mà không đưa
  giá trị bí mật vào Git hoặc log.
- Xác nhận phiên bản thư viện/model thực sự dùng được. Chỉ đổi dependency hoặc
  cấu hình khi có lỗi tương thích được kiểm chứng.
- Sửa các lỗi TypeScript, import và startup được phát hiện; cập nhật hướng dẫn
  chạy trên Windows với npm.cmd.

**Phạm vi:** requirements.txt, package.json/lock khi cần, cấu hình frontend/backend,
docker-compose.yml, README và các file gây lỗi build/startup.

**Nghiệm thu:** npm.cmd run build và lint thành công; frontend mở được; backend
khởi động và trả /health; xác nhận riêng kết nối database, vì /health hiện chỉ
trả trạng thái tĩnh.

## Phase 2 — Nối session, workflow và duyệt kế hoạch

**Kết quả:** tạo phiên, nhìn thấy kế hoạch trên UI và duyệt để graph tiếp tục.

- Chốt thứ tự tạo session, upload tài liệu rồi mới khởi chạy. Không chạy graph
  trước khi các file đã chọn được upload xong.
- Nối LangGraph với session_id/thread_id và luồng phát sự kiện WebSocket.
- Chọn một đường xử lý resume dùng chung; REST/WS không có hai logic điều phối
  độc lập. Đồng bộ API client và hook frontend theo contract đó.
- Cung cấp trạng thái phiên qua API để tải lại trang vẫn đọc được trạng thái
  khi backend còn chạy. Reconnect WebSocket không tự khởi chạy lại nghiên cứu.
- Hoàn thiện UI duyệt/sửa kế hoạch; kiểm tra session và payload trước khi resume.
- Lưu kết quả LLM trước điểm chờ duyệt, để resume không gọi lại LLM ngoài ý muốn.
- Ngăn bấm chạy/duyệt lặp tạo nhiều tác vụ cho cùng phiên; phân biệt trạng thái
  đang chạy, chờ duyệt, hoàn tất và lỗi.

**Phạm vi:** api/routes/research.py, api/websocket.py, graph/state.py,
graph/workflow.py, graph/nodes/planner.py, schemas và frontend hook/progress/API.

**Nghiệm thu:** UI hiển thị kế hoạch thật; sửa kế hoạch tác động tới state;
duyệt tiếp tục đúng checkpoint. Test xác nhận reconnect/duyệt lặp không chạy
trùng và lỗi được gửi về UI. Session vẫn tạm lưu RAM đến Phase 7.

## Phase 3 — MVP nghiên cứu một vòng và xuất Markdown

**Kết quả:** dùng được từ câu hỏi đến báo cáo thật với chế độ Quick.

- Nối đường chạy một vòng: tìm web, đọc nội dung, chunk/embed vào Qdrant,
  lấy context, trích xuất findings và tổng hợp báo cáo.
- Dùng source ID ổn định và khóa lưu trữ gắn với session ngay từ đầu; áp dụng
  cho các thao tác Qdrant/Neo4j đang được workflow gọi để tránh lẫn dữ liệu.
- Nối SessionBudget trước các lệnh gọi thật: giới hạn search, tài liệu, vòng lặp
  và ngân sách LLM; tính cả các lượt gọi khi sửa kế hoạch/báo cáo.
- Kiểm tra URL HTTP(S), địa chỉ đích và redirect trước khi fetch; chặn truy cập
  mạng nội bộ/loopback qua URL đầu vào hoặc kết quả tìm kiếm.
- Không lưu vector 0 như thể embedding thành công; lỗi provider phải được ghi
  nhận rõ và xử lý thành trạng thái lỗi hoặc kết quả thiếu dữ liệu.
- Nối citation guard: reference phải trỏ tới nguồn đã thu thập và đọc được.
  Thiếu bằng chứng phải được thể hiện trong kết quả.
- Thay placeholder của ReportView bằng báo cáo từ session; hiển thị bản nháp,
  phê duyệt, chuyển sang trang kết quả và xuất Markdown đúng nội dung.

**Phạm vi:** nodes searcher/reader/extractor/synthesizer, tools/services,
models/budget.py, guardrails, API báo cáo/export và các trang frontend liên quan.

**Nghiệm thu:** một nghiên cứu Quick chạy với API thật, tạo báo cáo xem và tải
được. Test phủ cạn ngân sách, không có nguồn, embedding lỗi, citation không hợp
lệ và hai phiên không dùng chung dữ liệu. Chức năng chưa hỗ trợ được ghi rõ trên UI.

## Phase 4 — Đủ nguồn đầu vào: paper, URL và PDF

**Kết quả:** người dùng nghiên cứu bằng web, bài báo, URL riêng và PDF tải lên.

- Hoàn thiện Semantic Scholar, giữ URL PDF open access và phân biệt rõ abstract
  với full text; không xem việc đọc trang metadata là đã đọc toàn bộ paper.
- Đưa request.urls vào state và luồng đọc tài liệu; hiện dữ liệu này chưa được dùng.
- Hoàn thiện upload: session hợp lệ, giới hạn dung lượng khi đọc, kiểm tra file
  PDF, tên file lưu an toàn và thống nhất thư mục uploads.
- Đưa PDF vào danh mục SourceMetadata để findings và citation có nguồn hợp lệ.
  Khi yêu cầu dựa trên PDF, đọc phần cần thiết trước khi lập kế hoạch tìm kiếm.
- Chỉ ingest tài liệu mới; upsert chunk ổn định để retry/vòng sau không nhân bản.
- Hoàn thiện bảng nguồn và bước chọn nguồn trước khi đọc sâu; lưu lựa chọn riêng
  thay vì làm mất lịch sử nguồn đã phát hiện.

**Phạm vi:** routes upload/start, state/schemas, nodes planner/searcher/reader,
tools search_papers/read_url/parse_pdf, Qdrant và UI nhập liệu/chọn nguồn.

**Nghiệm thu:** thử riêng paper, URL, PDF và đầu vào kết hợp; nguồn bị bỏ chọn
không được đọc; PDF có citation hợp lệ; ingest lại không tăng chunk trùng.
File hỏng/quá lớn, URL không an toàn và trang không đọc được có lỗi rõ ràng.

## Phase 5 — Vòng lặp nghiên cứu, chất lượng và sửa báo cáo

**Kết quả:** Standard/Deep tìm thêm đúng phần thiếu và dừng đúng giới hạn.

- Hoàn thiện Reflector, routing và structured output; lỗi parse không được coi
  là bằng chứng đã đủ dữ liệu.
- Query bổ sung xuất phát từ knowledge gaps; không đọc/extract lại toàn bộ dữ
  liệu cũ hoặc cộng findings trùng qua các vòng.
- Thực thi giới hạn Quick/Standard/Deep và ngân sách chung; retry và resume
  không được làm bộ đếm về 0.
- Nối minimum sources và diversity gate với hành vi cụ thể: tìm thêm khi còn
  ngân sách, hoặc trả báo cáo nêu rõ giới hạn khi không thể bổ sung.
- Tách kiểm tra citation có tồn tại với kiểm tra claim có bằng chứng; không dùng
  tỷ lệ ID hợp lệ để kết luận báo cáo hoàn toàn đúng.
- Nối phản hồi sửa báo cáo quay lại Synthesizer rồi chờ duyệt lại. Hiện graph
  có report_approval rồi END, chưa có nhánh feedback để viết lại.

**Phạm vi:** graph/edges.py, workflow/state, nodes reflector/extractor/synthesizer,
budget/guardrails và UI review báo cáo.

**Nghiệm thu:** test đủ thông tin dừng sớm, thiếu thông tin tìm thêm, chạm ngân sách
dừng có lý do, feedback tạo bản nháp mới. Chạy thật ít nhất một ca cần nhiều vòng
và một ca không có đủ nguồn; ghi số lượt gọi/tài liệu/vòng thực tế.

## Phase 6 — Knowledge Graph sử dụng được

**Kết quả:** đồ thị thể hiện nguồn, tác giả, findings và khái niệm của đúng phiên.

- Hoàn thiện schema Neo4j cho cả paper, web và PDF; liên kết findings với đúng
  nguồn và giữ entities từ Extractor để tạo Concept.
- Đảm bảo truy vấn graph và quan hệ không kéo dữ liệu ngoài phiên qua node chung;
  xử lý dữ liệu cũ nếu thay đổi khóa, không tự xóa database.
- Sửa lọc graph: chỉ giữ cạnh có cả hai đầu trong tập node hiển thị; loại cạnh
  rỗng và kiểm tra cách thư viện thay đổi object node/link.
- Hoàn thiện zoom, tìm kiếm, chi tiết node, trạng thái rỗng/lỗi và bố cục co giãn.
- Thêm đường đi rõ ràng từ báo cáo tới graph.

**Phạm vi:** nodes extractor/kg_builder, graph state, neo4j_service.py,
API graph, types và KnowledgeGraph.tsx.

**Nghiệm thu:** hai phiên với nguồn cùng mã REF không ghi đè/lẫn nhau; PDF và web
có quan hệ nguồn; lọc/zoom không gây lỗi; bấm node thấy metadata đúng.

## Phase 7 — Lưu phiên và phục hồi sau restart

**Kết quả:** tải lại trang hoặc khởi động lại backend vẫn xem được phiên/báo cáo.

- Thay MemorySaver bằng checkpointer PostgreSQL; lưu metadata/status/report để
  API đọc lại được thay vì phụ thuộc RAM của SessionManager.
- Khởi tạo schema bằng cơ chế migration/setup rõ ràng và quản lý kết nối trong
  lifecycle của app; thống nhất nguồn dữ liệu trạng thái.
- Khôi phục đúng phiên đang chờ HITL. Phiên bị ngắt giữa lúc chạy phải được đánh
  dấu có thể phục hồi hoặc báo lỗi rõ, không treo vĩnh viễn ở trạng thái running.
- Resume giữ ngân sách và kết quả đã có; các bước ingest/ghi graph lặp lại không
  nhân bản dữ liệu. Không tuyên bố API ngoài được gọi đúng một lần khi chưa có bảo đảm.

**Phạm vi:** main/config, API session/export, graph checkpointer/state,
schema PostgreSQL và frontend tải trạng thái/reconnect.

**Nghiệm thu:** restart ở bước chờ duyệt kế hoạch/báo cáo vẫn resume được; báo cáo
đã xong vẫn xem/tải được; kiểm tra riêng trường hợp backend dừng giữa một bước.

## Phase 8 — Hoàn thiện demo và đánh giá

**Kết quả:** bản local ổn định, có hướng dẫn và bằng chứng kiểm thử.

- Hoàn thiện loading/error/empty states, điều hướng bốn màn hình, mục lục/citation
  và thao tác bàn phím; giao diện phản ánh đúng khả năng đã triển khai.
- Chạy build/lint và bộ test tích lũy; thử các tình huống lỗi API, timeout,
  upload hỏng, disconnect, hết ngân sách và cô lập dữ liệu giữa phiên.
- Chọn benchmark đại diện từ tài liệu evaluation: web, học thuật, PDF, tìm thêm
  theo gap và không đủ dữ liệu. Ghi thời gian, số lượt gọi, số nguồn, citation và
  đánh giá claim dựa trên bằng chứng; không khẳng định trước các tỷ lệ chất lượng.
- Viết README thực chạy được, mẫu cấu hình, cách khởi động/dừng và kịch bản demo.
- Markdown là định dạng xuất bắt buộc của MVP. Chốt nhu cầu PDF/DOCX trước khi
  triển khai exporter tương ứng; khi chưa có thì UI phải thể hiện chưa hỗ trợ.

**Nghiệm thu:** làm theo README trên môi trường sạch có thể chạy lại demo; có
báo cáo kết quả kiểm thử và danh sách giới hạn còn tồn tại.

## Thứ tự và phạm vi sau MVP

Phase 1 → 2 → 3 (MVP) → 4 → 5 → 6 → 7 → 8.

Mục tiêu trước mắt là ứng dụng local phục vụ demo/đồ án. Đăng nhập đa người dùng,
phân quyền chia sẻ, task queue, public deployment và tích hợp dịch vụ mới là các
hạng mục sau MVP; cần lập phạm vi riêng trước khi triển khai công khai.

Bước tiếp theo sau rà soát: chốt bài toán, A/B/C và rubric với cô theo hồ sơ
system-analysis; chuẩn bị tích hợp thật và protocol kiểm chứng. Dependencies
đã cài được, nhưng dịch vụ thật và lợi ích đối với người dùng chưa được chứng minh.
Người dùng đã cho phép triển khai Phase 4 ngày 2026-11-09. Việc này không thay
thế nghiệm thu tích hợp thật, benchmark hoặc xác nhận của cô về đề tài/rubric.
