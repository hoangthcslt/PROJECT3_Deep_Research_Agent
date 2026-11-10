# 07 · Rà soát sáu yêu cầu và truy vết nghiệm thu

## Kết luận rà soát sau ba phase

Code/test đã có, nhưng hồ sơ ban đầu chưa đủ để bảo vệ bài toán: persona quá rộng; thiếu khảo sát có nguồn; thiếu liên kết use case–code–test; bảng evaluation có số trông như kết quả nhưng chưa đo. Chưa thể nói đã chứng minh hiệu quả nghiên cứu hoặc ưu thế sản phẩm.

Trong lần rà soát này đã chạy lại 60 test backend, production build frontend,
lint (exit 0, còn cảnh báo React) và snapshot test. Xem
[log và fingerprint source](evidence/README.md). Các lần kiểm tra này không gọi
provider/database thật và không thay thế đánh giá chất lượng/người dùng.

| Yêu cầu của cô | Trước hồ sơ này | Đã bổ sung | Phần vẫn cần xác nhận |
|---|---|---|---|
| 1. Bài toán cụ thể, chức năng A/B/C để nghiệm thu | Ý tưởng trợ lý nghiên cứu đa đối tượng, phạm vi quá lớn | Persona đã chốt với người dùng, bài toán khảo sát công nghệ cho đề cương, A/B/C và scenario | Cô duyệt phạm vi và rubric; chưa có xác nhận từ cô |
| 2. Khảo sát và lý do nên dùng | Chưa có đối chiếu sản phẩm đủ nguồn | Khảo sát official docs, so sánh use case, chỉ rõ khác biệt chưa chứng minh | Chưa thử sản phẩm trực tiếp hoặc đo lợi ích sinh viên |
| 3. Người dùng, chức năng, tác nhân | Có persona brainstorm, chưa thống nhất boundary | Actor/stakeholder, use case core và mục tiêu, UML use case | Chưa phỏng vấn người dùng |
| 4. Phân tích thiết kế trước làm | Có sketch nhưng đã code ba phase trước baseline đặc tả này | UML hiện trạng bám code; mở rộng vẽ riêng; quy trình design gate trước thay đổi | Không thể hồi tố thành “đã thiết kế trước”; cần áp dụng từ phase tiếp theo |
| 5. Plan tổng và lý do công nghệ | Có build plan; stack phần lớn được kế thừa | Master plan nghiệp vụ/kiểm chứng, decision record, phương án đơn giản hơn | Chưa chứng minh utility của Qdrant/reflection/Neo4j |
| 6. Chứng minh và benchmark | Có ý tưởng metric, mục tiêu và bảng số chưa có dữ liệu | H1–H6, baseline/ablation, protocol, dataset/mẫu ghi và gate đo | Tất cả kết quả benchmark thực tế vẫn CHƯA ĐO |

## Yêu cầu và bằng chứng core

| ID | Yêu cầu | UC / chức năng | Code / test đối chiếu | Trạng thái |
|---|---|---|---|---|
| FR-01 | Tạo khảo sát từ câu hỏi hợp lệ, không tự chạy khi chỉ create | UC-01 / A | [research.py](../../backend/app/api/routes/research.py), [API tests](../../backend/tests/test_phase3_api.py) | CODE/TEST |
| FR-02 | Plan sửa/duyệt được, input và interrupt hợp lệ | UC-02 / A | [planner.py](../../backend/app/graph/nodes/planner.py), [session tests](../../backend/tests/test_phase2_session_manager.py) | CODE/TEST |
| FR-03 | Tìm/đọc/index và trích xuất một vòng có giới hạn | UC-03 / B | [reader.py](../../backend/app/graph/nodes/reader.py), [pipeline](../../backend/tests/test_phase3_pipeline.py), [workflow](../../backend/tests/test_phase3_workflow.py) | CODE/TEST; provider thật chưa chạy |
| FR-04 | Xem/reconnect trạng thái không chạy lại tác vụ | UC-03/07 / B | [websocket.py](../../backend/app/api/websocket.py), [hook test](../../frontend/src/hooks/researchSnapshot.test.mjs), [API tests](../../backend/tests/test_phase3_api.py) | CODE/TEST; browser chưa kiểm chứng |
| FR-05 | Citation thuộc nguồn đã đọc, không dùng reference-only làm bằng chứng | UC-04 / C | [citation_guard.py](../../backend/app/guardrails/citation_guard.py), [citation tests](../../backend/tests/test_phase3_citations.py) | CODE/TEST cấu trúc; support ngữ nghĩa chưa đo |
| FR-06 | Duyệt final và chỉ tải đúng Markdown đã duyệt | UC-05/06 / C | [export.py](../../backend/app/api/routes/export.py), [ReportView](../../frontend/src/pages/ReportView.tsx), [API tests](../../backend/tests/test_phase3_api.py) | CODE/TEST |
| FR-07 | Sinh viên xem được claim và đoạn evidence tương ứng | UC-04 / C mở rộng | Findings trong state; chưa có evidence package/UI đầy đủ | CHƯA ĐỦ cho nghiệm thu truy vết người dùng |
| FR-08 | PDF/URL riêng/chọn nguồn | UC-08 | Endpoint PDF 501; UI unavailable | PHASE SAU / CẦN DUYỆT |
| FR-09 | Feedback và nghiên cứu bổ sung nhiều vòng | UC-09 | Quick chỉ một vòng; report chỉ approve | PHASE SAU / CẦN DUYỆT |
| FR-10 | Graph phục vụ tác vụ truy vết của sinh viên | UC-10 | API/storage có; [KnowledgeGraph](../../frontend/src/pages/KnowledgeGraph.tsx) chưa hoàn thiện luồng sử dụng | MỘT PHẦN; utility chưa đo |
| FR-11 | Mở lại phiên sau restart | UC-11 | RAM/MemorySaver hiện tại | CHƯA CÓ |
| FR-12 | Export trace, thời gian và chi phí để đo | H1–H6 | Counters/log có trong hệ thống; harness/evidence export chưa đủ | CHƯA CÓ ĐẦY ĐỦ |

| ID | Yêu cầu phi chức năng | Bằng chứng / giới hạn |
|---|---|---|
| NFR-01 | Không chạy trùng khi lặp command | Session/API/real LangGraph tests; không suy ra exactly-once cho mọi API bên ngoài |
| NFR-02 | Budget và lỗi phải rõ | [budget tests](../../backend/tests/test_phase3_budget.py); cap mặc định 4 search, 8 tài liệu; Quick 1 vòng; byte estimate, không phải tiền thật |
| NFR-03 | URL không truy cập mạng nội bộ; vector lỗi không thành công giả | [IO tests](../../backend/tests/test_phase3_io.py); dữ liệu/provider giả lập, không chứng minh mọi môi trường mạng |
| NFR-04 | Cách ly dữ liệu hai session | [Qdrant tests](../../backend/tests/test_phase3_qdrant.py), Neo4j query-contract tests; chưa phải auth đa người dùng |
| NFR-05 | Build và kiểm tra được | Phase 3 ghi 60 test backend, build frontend đạt; lint còn warning; benchmark quality chưa chạy |

## Kịch bản cô có thể nghiệm thu core

1. **A:** nhập câu hỏi Qdrant/pgvector cho đồ án nhỏ; thấy plan. Thay một tiêu chí. Chứng minh plan đã sửa được sử dụng, không chỉ thay text trên UI.
2. **B:** phê duyệt plan; theo dõi tìm/đọc/extract. Hiển thị log bằng chứng và giới hạn. Gửi lệnh lặp/stale trong test để thấy 409; reload không chạy lại.
3. **C:** xem draft có citation; mở nguồn kiểm tra. Trước approve, export bị chặn; sau approve, tải đúng Markdown của phiên đó.
4. **Âm tính:** không có nguồn dùng được hoặc LLM/embedding/lưu trữ lỗi → trạng thái error, không hiện báo cáo hoàn tất giả. Một truy vấn/trang lỗi có thể bị bỏ qua nếu còn nguồn. Citation không hợp lệ không vào draft được duyệt.
5. **Cách ly:** chạy hai phiên với mã nguồn cục bộ giống nhau; truy hồi của phiên A không lẫn B.

Scenario provider/database thật hiện **chưa nghiệm thu**, theo lựa chọn trước của người dùng. Khi demo với fixture, phải gọi là demo/test điều phối, không gọi là nghiên cứu web thật.

## Điều kiện để tuyên bố hữu ích cho sinh viên

Cô duyệt G0 và rubric; hoàn thiện phần thiếu FR-07/FR-12 nếu dùng chúng làm luận điểm; chạy G2; đo theo G3/G4; có data và reviewer labels. Nếu chỉ hoàn tất code/test, kết luận được phép là **đã xây prototype và kiểm tra chức năng**, chưa phải “giúp sinh viên nhanh hơn/đúng hơn”.

## Checklist trước khi viết tiếp

- [ ] Cô đồng ý persona và A/B/C.
- [ ] Chốt FR-07 có bắt buộc cho bản nộp cuối không.
- [ ] Chốt có cần PDF/academic search, graph và restart recovery không.
- [ ] Duyệt 20 ca và metric; xóa/đánh dấu mọi số chưa đo khỏi slide kết quả.
- [ ] Có thiết kế target cập nhật trước implementation.
- [ ] Khi làm tiếp, cập nhật code/test/evidence và UML cùng một thay đổi.
