# Phase 4 — thiết kế và phạm vi triển khai

Ngày 09/11/2026, người dùng yêu cầu nghiệm thu Phase 3 rồi triển khai Phase 4.
Phase 3 đã được nghiệm thu code/test; kiểm tra lại baseline: **60 passed**.
Người dùng tiếp tục chọn Luna max triển khai, agent chính review và chạy kiểm tra.
Đây là cho phép triển khai của người dùng; không ghi nhận như cô đã duyệt đề tài.
Phạm vi tích hợp thật vẫn hoãn theo lựa chọn trước đó.

## Kết quả cần có

Sinh viên CNTT có thể khảo sát công nghệ từ web, bài báo, URL cung cấp và PDF
tải lên. Sau khi duyệt kế hoạch, sinh viên chọn nguồn trước khi hệ thống đọc
sâu/index, rồi duyệt bản nháp và xuất Markdown như Phase 3.

Không mở Standard/Deep, vòng lặp nâng cao, sửa báo cáo bằng feedback, OCR,
lưu phiên qua khởi động lại hoặc xuất PDF/DOCX trong phase này.

## Luồng và hợp đồng

1. Tạo session với `question`, `depth: quick`, `urls` và `search_mode`.
   Chế độ `web`, `academic`, `mixed` hoặc `provided`; mặc định `web` giữ tương
   thích caller cũ. `provided` chỉ dùng URL/PDF cung cấp.
2. Upload trước khi run, khóa cùng session để tránh upload/run đua nhau. Tên
   lưu do server tạo; giới hạn 3 PDF, mỗi file 10 MiB. Kiểm tra MIME, signature
   và parser thật. PDF mã hóa, hỏng, không có chữ hoặc quá 100 trang bị từ chối.
3. Lấy preview PDF giới hạn trước khi lập kế hoạch. Preview này phục vụ lập
   kế hoạch, chưa embedding/index. Không hứa rằng PDF bỏ chọn chưa từng được
   parse: bước chọn kiểm soát đọc sâu và indexing sau preview.
4. Duyệt/sửa kế hoạch qua REST với interrupt ID như cũ. Query web và academic
   dùng ngân sách provider tương ứng; không retry HTTP ngầm ngoài bộ đếm.
5. Tập hợp candidate từ URL, PDF và search; giữ lịch sử `sources_found`.
   Node `source_approval` checkpoint riêng phát `SOURCE_SELECTION_REQUIRED`.
6. Resume bằng `action: select_sources`, `selected_source_ids` duy nhất,
   không rỗng, thuộc candidate và không vượt ngân sách đọc. Status mới là
   `awaiting_sources`. Không gửi lệnh qua WebSocket; ID stale bị từ chối.
7. Reader chỉ index nguồn được chọn, tối đa 8.000 byte UTF-8/nguồn. PDF chỉ lấy
   tối đa 10 trang đầu. Paper có OA PDF thì thử đọc excerpt; nếu chỉ có abstract
   phải gắn nhãn `abstract`, không gọi đó là toàn văn.
8. Findings/citation chỉ trỏ tới nguồn đã index trong session. PDF upload có
   endpoint tải theo session/source; không đưa đường dẫn filesystem ra UI.
   Canonical references chỉ chấp nhận đúng URL nội bộ được server cấp.
9. Duyệt báo cáo và xuất Markdown tiếp tục dùng luồng cũ.

Nguồn công khai có `source_id`, title, URL, loại, preview, `content_kind`
(`webpage`, `abstract`, `pdf_excerpt`), OA PDF URL nếu có, số trang và cờ
`truncated`. Snapshot chứa metadata và ID đã chọn; không chứa nội dung đầy đủ
hoặc đường dẫn riêng của upload. Preview/chữ tải lên là nội dung không tin cậy,
không phải chỉ dẫn hệ thống cho model.

## Phân công thay đổi

| Phần | Nơi phải đồng bộ |
|---|---|
| Hợp đồng, vòng đời | schemas, state, routes, session manager, snapshot/WebSocket |
| Điều phối | planner, searcher, source approval, reader, workflow, budget |
| IO | parser PDF, lưu upload, safe fetch HTML/PDF, Semantic Scholar |
| Bằng chứng | metadata trong index/prompt, citation guard, đường dẫn tải PDF |
| Giao diện | input/upload, sửa plan, bảng chọn nguồn, reload/resume, lỗi |
| Nghiệm thu | regression Phase 2/3, IO security, source selection, workflow, build |

Tái sử dụng FastAPI UploadFile, PyMuPDF, httpx, LangGraph và Qdrant đã cài;
không thêm framework hay dependency. Giữ cơ chế DNS validation từng redirect,
IP pinning và giới hạn thời gian/dung lượng khi mở rộng fetch PDF.

## Điều kiện nghiệm thu code/test

- Web cũ vẫn chạy, có thêm checkpoint chọn nguồn; reload không gọi lại search
  hoặc generation đã checkpoint.
- Paper-only, URL-only, PDF-only và hỗn hợp đi qua index → draft → approve.
- Nguồn bỏ chọn không bị fetch sâu/index; abstract và PDF excerpt được phân biệt
  trong thông tin đưa cho model và thông tin trả cho người dùng.
- File hỏng/quá lớn, unsafe URL, trang không đọc được, chọn ID lạ/trùng/stale
  được xử lý rõ; file/session không thể truy cập chéo bằng source ID.
- Ingest lại không tạo chunk trùng; giữ giới hạn token/search/document và cô lập
  dữ liệu giữa session. PDF citation không làm lộ path hoặc nhận URL giả.
- Toàn bộ regression backend, frontend build và kiểm tra logic frontend đạt.

Kết quả thực tế sẽ ghi tại `PHASE4_STATUS.md` sau review, không suy ra từ thiết kế
này. Tài liệu UML 01–09 giữ mốc hiện trạng Phase 3; sơ đồ Phase 4 bổ sung riêng.
