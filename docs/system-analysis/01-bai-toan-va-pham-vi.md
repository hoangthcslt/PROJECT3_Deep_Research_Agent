# 01 · Bài toán cụ thể và phạm vi

## Đề xuất để cô nghiệm thu

**Bài toán:** sinh viên CNTT cần lập một bản khảo sát công nghệ ban đầu để quyết định phương án cho đồ án. Các thông tin thường nằm rải rác trong tài liệu hãng, bài hướng dẫn và báo cáo kỹ thuật; sinh viên phải chuyển chúng thành các tiêu chí so sánh và dẫn chứng có thể kiểm tra.

**Đầu vào:** một câu hỏi bằng tiếng Việt hoặc tiếng Anh, nêu công nghệ cần so sánh, bối cảnh đồ án và các tiêu chí quan tâm. Hiện giao diện có một ô văn bản tự do; chưa có các trường bối cảnh/tiêu chí riêng.

**Đầu ra:** kế hoạch được sinh viên duyệt và một bản nháp báo cáo Markdown có nguồn web, được sinh viên xem và phê duyệt trước khi tải xuống. Báo cáo hỗ trợ ra quyết định; không tự động xác nhận kết luận đúng hoặc viết thay toàn bộ đề cương.

**Ví dụ đầu vào:** “Em làm chatbot hỏi đáp tài liệu môn học, khoảng 100 tài liệu, chạy trên máy cá nhân. Khảo sát Qdrant và pgvector theo khả năng triển khai, truy hồi, vận hành và giới hạn. Phân biệt thông tin từ tài liệu với nhận định cần đo.” Đây là nhiệm vụ demo, không phải kết quả benchmark hai công nghệ.

## Ba chức năng A/B/C

| Chức năng | Người dùng làm gì? | Hệ thống làm gì? | Sản phẩm nghiệm thu |
|---|---|---|---|
| **A. Định hướng khảo sát** | Nhập câu hỏi; duyệt hoặc sửa câu hỏi phụ | Tạo phiên, sinh kế hoạch, dừng chờ quyết định | Kế hoạch có ID; sửa được; chưa tìm kiếm trước khi duyệt |
| **B. Thu thập bằng chứng có kiểm soát** | Theo dõi tiến độ/lỗi | Tìm web, đọc URL an toàn, index, truy hồi và trích xuất findings trong giới hạn | Nguồn và findings cùng phiên; cạn ngân sách/lỗi không bị báo thành công |
| **C. Tổng hợp và kiểm tra báo cáo** | Đọc bản nháp, mở nguồn kiểm tra, duyệt và tải | Tổng hợp từ findings có nguồn, kiểm tra marker, thay reference bằng metadata thu thập | Bản nháp → bản đã duyệt; Markdown tải đúng nội dung |

Phạm vi A/B/C có implementation và test sau Phase 3. Chất lượng báo cáo với dịch vụ thật và mức hữu ích đối với sinh viên **chưa được chứng minh**.

## Người dùng và lợi ích cần kiểm chứng

Người dùng chính là sinh viên CNTT làm đề cương hoặc khảo sát phương án kỹ thuật. Giảng viên là người đánh giá bài nộp; hiện không có tài khoản hay màn hình riêng cho giảng viên. Người vận hành cấu hình dịch vụ, không phải một vai trò quản trị đã có trong giao diện.

Ba giả thuyết nghiệp vụ: sinh viên mất ít thời gian hơn để có bản nháp dùng được; bản nháp bao phủ tiêu chí được giao; sinh viên kiểm tra nguồn và sửa phạm vi dễ hơn. Chưa có phỏng vấn hay đo thời gian để xác nhận các giả thuyết này.

## Hiện trạng và đích đề xuất

| Hạng mục | Phase 3 hiện có | Bản nộp cuối đề xuất |
|---|---|---|
| Loại khảo sát | Quick, web, một vòng thu thập | Giữ Quick làm core; chỉ mở rộng khi có use case được duyệt |
| Định hướng | Câu hỏi tự do + duyệt/sửa plan | Hướng dẫn nhập bối cảnh/tiêu chí; template so sánh cần kiểm chứng thêm |
| Dẫn chứng | Marker nguồn, footnote URL; findings nằm trong state | Gói claim–evidence–source xem được để hỗ trợ kiểm tra |
| Nguồn | Web do tìm kiếm trả về | PDF/URL riêng nếu cô yêu cầu; không mặc định phải làm mọi loại nguồn |
| Phiên | RAM; reload khi backend còn sống | Lưu sau restart nếu được đưa vào tiêu chí nộp cuối |
| Graph | Có lưu Source/Finding và API; UI còn hạn chế | Chỉ hoàn thiện nếu có tác vụ truy vết cụ thể và đo được lợi ích |

## Ngoài phạm vi core

- Không phải systematic literature review, công cụ chứng nhận tính mới hoặc phát hiện research gap đã được kiểm định.
- Không tự đo throughput/latency của Qdrant, Milvus hay công nghệ được hỏi. Nếu nguồn không có số liệu, phải nói chưa biết; muốn có số liệu phải làm thực nghiệm riêng.
- Không phải multi-agent phân tán: hiện là một workflow điều phối các node chuyên trách.
- Không phải hệ thống học tích lũy tri thức xuyên người dùng/phiên: truy hồi được lọc theo session.
- Chưa có đăng nhập, phân quyền lớp học, nộp bài cho cô, cộng tác hay triển khai công khai.
- PDF, academic search, feedback sửa báo cáo, Standard/Deep và phục hồi sau restart chưa thuộc core Phase 3.

## Giới hạn phải trình bày khi demo

Một backend worker; session mất khi restart. Mỗi trang chỉ index tối đa 8.000 byte UTF-8; trang cần JavaScript hoặc không truy cập được có thể không đọc được. Input budget là ước lượng bảo thủ theo byte, không phải hóa đơn API thực tế. Citation guard kiểm tra cấu trúc nguồn và heuristic, không chứng minh claim được nguồn hỗ trợ.

## Tiêu chí chốt bài toán

Trước Phase 4, cô cần duyệt: tên đề tài; tình huống demo; ba chức năng A/B/C; những phần mở rộng bắt buộc; rubric chất lượng và tập benchmark. Bằng chứng hiện có chỉ xác nhận phần mềm chạy theo thiết kế trong test. Không đổi “chưa đo” thành “đạt” chỉ vì đã có code.
