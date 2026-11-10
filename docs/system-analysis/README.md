# Hồ sơ phân tích–thiết kế và nghiệm thu

**Baseline: 09/11/2026 · Người dùng đã chốt: sinh viên CNTT khảo sát công nghệ cho đề cương đồ án.**

Tên đề tài đề xuất: **Hệ thống hỗ trợ sinh viên CNTT khảo sát công nghệ có kiểm soát và truy vết nguồn**. Tên repository Deep Research Agent được giữ nguyên; tên đề tài cần cô hướng dẫn duyệt.

Đây là hồ sơ được lập **sau Phase 3**, từ code và tài liệu hiện có. Không trình bày như thể đã hoàn thành phân tích trước ba phase vừa qua. Người dùng đã cho phép triển khai Phase 4; [thiết kế và phạm vi Phase 4](../PHASE4_IMPLEMENTATION.md) được bổ sung trước thay đổi. Đây chưa phải xác nhận của cô về tên đề tài/rubric. Sơ đồ 01–09 và fingerprint source giữ mốc Phase 3.

## Đọc theo thứ tự nào?

1. [Bài toán, ba chức năng và phạm vi](01-bai-toan-va-pham-vi.md): dùng để trình bày đề tài trong 3 phút.
2. [Khảo sát và lý do tự xây hệ thống](02-khao-sat-va-dinh-vi.md): đối thủ làm được gì, dự án còn phải chứng minh gì.
3. [Actors và đặc tả use case](03-actors-use-cases.md): ai sử dụng, luồng chính, lỗi và điều kiện hoàn tất.
4. [Phân tích–thiết kế và UML](04-phan-tich-thiet-ke.md): sơ đồ và đối chiếu với implementation.
5. [Master plan và quyết định công nghệ](05-master-plan-va-cong-nghe.md): gate nghiệm thu, phụ thuộc và điều kiện giữ/bỏ công nghệ.
6. [Kế hoạch kiểm chứng và benchmark](06-ke-hoach-kiem-chung.md): giả thuyết, baseline, cách đo và giới hạn kết luận.
7. [Rà soát sáu yêu cầu của cô và truy vết nghiệm thu](07-nghiem-thu-va-truy-vet.md).

**Xem hình:** mở [index.html](index.html) bằng trình duyệt, hoặc xem [danh mục sơ đồ](diagrams/README.md). Mỗi hình có SVG để phóng to, PNG để đưa vào báo cáo và nguồn PlantUML để sửa. Các hình có nhãn **HIỆN TRẠNG** hoặc **ĐỀ XUẤT**; không trộn hai loại.

## Một câu giải thích hệ thống

Sinh viên đưa ra câu hỏi so sánh công nghệ cùng bối cảnh đồ án; hệ thống đề xuất kế hoạch để sinh viên duyệt, tìm và đọc nguồn web trong ngân sách, rồi tạo bản nháp có dẫn nguồn để sinh viên kiểm tra trước khi xuất Markdown.

## Mức độ bằng chứng

| Nhãn | Ý nghĩa |
|---|---|
| CODE/TEST | Có implementation và kiểm tra phần mềm; không suy ra chất lượng nghiên cứu |
| CHƯA KIỂM CHỨNG THẬT | Chưa chạy provider/database thật hoặc chưa thử với người dùng |
| ĐỀ XUẤT | Thiết kế/tiêu chí để thảo luận; chưa phải chức năng đã có |
| CHƯA ĐO | Chưa có thực nghiệm; không điền số liệu giả |

Mốc 60 test backend và frontend build đã được ghi trong [Phase 3](../PHASE3_STATUS.md). Đây **không phải** kết quả faithfulness, tốc độ làm việc của sinh viên hoặc bằng chứng thắng sản phẩm khác. Benchmark có [bộ ca](benchmarks/cases.csv), [mẫu ghi lượt chạy](benchmarks/runs.csv) và [mẫu đánh giá claim](benchmarks/claims.csv), đều chưa có kết quả đo.

Lần rà soát này có [log kiểm tra mới và fingerprint source](evidence/README.md), cùng [danh sách nguồn khảo sát](SOURCE_REGISTER.md).

Tài liệu [brainstorm](../brainstorm/) là lịch sử ý tưởng. Các tỷ lệ kết quả trong bản evaluation cũ chưa có dữ liệu thực nghiệm và không được dùng làm số liệu bảo vệ. Hồ sơ này là đặc tả làm việc mới; code vẫn là nguồn xác nhận hành vi hiện trạng.

## Các điểm cần cô duyệt

- [ ] Tên bài toán và người dùng chính.
- [ ] Ba chức năng A/B/C và các mục ngoài phạm vi.
- [ ] Tiêu chí nghiệm thu chức năng trong tài liệu 07.
- [ ] Bộ câu hỏi, baseline và rubric trong tài liệu 06.
- [ ] Có cần graph tương tác và lưu phiên bền vững cho bản nộp cuối không?

Người dùng đã chọn hướng sinh viên CNTT; **chưa có bằng chứng cô đã duyệt**. Chưa phỏng vấn người dùng, chưa chạy benchmark sản phẩm và chưa làm tích hợp provider/database thật trong công việc lập hồ sơ này.
