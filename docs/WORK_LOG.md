# Work log — handoff Phase 4 and pull request

**Cập nhật:** 10/11/2026, Asia/Bangkok
**Mục tiêu phiên:** lưu trạng thái Phase 4 đã làm dở; tạo Draft PR theo yêu cầu.
**Base lúc bắt đầu:** `main` / `c97f3ce` / `origin/main`.
**Branch dự kiến:** `feature/multi-source-research-phase4`.

## Trạng thái

- Phase 3 đã nghiệm thu riêng ở mốc trước: **60 backend test passed**, frontend
  production build passed. API/provider/database thật chưa chạy theo lựa chọn
  “chốt code/test trước, tích hợp thật sau”.
- Phase 4 có nhiều thay đổi chưa review xong: tìm bài báo, URL/PDF riêng,
  upload PDF giới hạn, duyệt chọn nguồn, cập nhật citation và giao diện.
- **Không nghiệm thu Phase 4.** Workflow/test cũ chưa cập nhật hết checkpoint
  chọn nguồn; frontend build đang lỗi TypeScript; helper đọc URL theo
  `Content-Type` chưa hoàn tất; chưa có browser visual QA.
- Luna max được chọn làm implementation; Astra dừng ở review/checkpoint. Không
  đánh dấu cô đã duyệt đề tài hoặc benchmark.

## Thay đổi chính đang có trong workspace

Backend: `app/models/schemas.py`, `app/graph/state.py`, các node planner,
searcher, source approval, reader, extractor, synthesizer, workflow và
`session_manager.py`; routes cho URL/PDF, upload theo session và tải PDF chỉ
trong session sở hữu. `parse_pdf.py`, `read_url.py`, `search_papers.py`,
`pdf_storage.py` và citation guard đang nối IO cho PDF/URL/bài báo. Upload
được giới hạn tối đa 3 tệp, 10 MiB/tệp, 100 trang; excerpt tối đa 10 trang và
8 KB, không OCR. Source picker mới có node riêng; chỉ nguồn được chọn mới được
đọc/index. Metadata/citation phân biệt abstract và PDF excerpt.

Frontend: `ResearchInput`, `ResearchProgress`, `ReportView`, API/types và
WebSocket snapshot cho phép nhập URL/PDF, chọn nguồn, reload checkpoint và mở
citation PDF nội bộ an toàn. Có helper kiểm tra URL/tệp trong
`frontend/src/services/researchInputs.ts`.

Tài liệu: `docs/PHASE4_IMPLEMENTATION.md` ghi hợp đồng và phạm vi; sơ đồ Phase 4
là hình 12 trong `docs/system-analysis/diagrams/`. Gallery tài liệu được sửa
lỗi mất dấu tiếng Việt. Các hình 01–09 và source fingerprint giữ baseline
Check summaries are committed in docs/phase4-checks/.

## Kiểm tra gần nhất (9/11, trước khi dừng)

| Kiểm tra | Kết quả | Ghi chú |
|---|---:|---|
| Backend tests | **74 passed, 7 failed** | Some older assertions expect the Phase 3 contract; one stale/duplicate-resume failure still needs review. |
| Node snapshot + input tests | **6/6 passed** | Logic snapshot, URL, giới hạn PDF và link citation. |
| Frontend build | **Failed** | `ResearchProgress.tsx:101`: TypeScript báo `planInterrupt` có thể null trong effect. |
| Frontend lint | Exit 0 | 6 React/hooks warnings còn lại. |
| Ruff `F,E9` | **Failed** | 1 `F541` thừa tiền tố f-string ở `graph/nodes/synthesizer.py:154`. |
| `git diff --check` | Passed | Git hiện cảnh báo line ending LF/CRLF. |

Một lượt tập trung do Luna chạy báo **52 passed** trước các lần sửa cuối. Lượt
review độc lập kế tiếp đạt **43 passed, 3 failed**: 2 lỗi trong test transport
do test tự bọc `AsyncClient` đã bị monkeypatch lần trước; 1 fixture PDF dài
không sinh được text trên trang nên parser đúng khi từ chối. Cần chạy lại sau
khi sửa fixture/helper. Không có test gọi dịch vụ trả phí; không có tích hợp
Gemini/Tavily/Qdrant/Neo4j thật.


## Việc làm tiếp theo

1. Hoàn tất helper `read_document_url()` trong `read_url.py`: một lần fetch an
   toàn, dispatch HTML/PDF theo `Content-Type`, xử lý URL PDF không có đuôi
   `.pdf`; nối `reader.py`, thêm regression.
2. Sửa TypeScript null check và chạy frontend build/lint/node tests. Kiểm tra
   retry upload, chọn nguồn, hiển thị lỗi một phần và snapshot sau reload.
3. Đồng bộ test cũ với checkpoint chọn nguồn; sửa manager/API/pipeline tests và
   thêm workflow Phase 4 nối các node thật bằng provider fixtures. Đảm bảo bài
   báo, URL, PDF, mixed/provided và nguồn bỏ chọn có hành vi được kiểm tra.
4. Sửa lỗi Ruff, sau đó chạy full backend suite, frontend build/node tests,
   diff check. Chỉ nghiệm thu sau khi các gate code/test đạt và review xong.
5. Live provider/database acceptance vẫn là việc riêng, hoãn theo yêu cầu cũ.

## Giới hạn đã biết

Session và LangGraph checkpoint còn lưu trong RAM; restart backend làm mất
session. Link PDF trong Markdown xuất ra là đường dẫn nội bộ tương đối, cần
backend và file nguồn còn tồn tại. Các URL ngoài phải được fetch qua SSRF/DNS
guards; hành vi live chưa được xác nhận. Không có browser host để xem trực tiếp
UI trong checkpoint này.

Draft PR: https://github.com/hoangthcslt/PROJECT3_Deep_Research_Agent/pull/1
Branch: feature/multi-source-research-phase4; code commit: 6ed3b12.
