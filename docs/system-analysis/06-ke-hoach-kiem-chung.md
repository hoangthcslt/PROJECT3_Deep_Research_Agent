# 06 · Kế hoạch kiểm chứng, benchmark và bằng chứng

**Trạng thái: thiết kế thực nghiệm; CHƯA CHẠY benchmark chất lượng/người dùng.** Các ngưỡng dưới đây là mục tiêu đề xuất để cô duyệt trước đo, không phải kết quả. 60 test phần mềm không phải 60 câu hỏi benchmark.

## Những gì cần chứng minh

| ID | Giả thuyết / câu hỏi | So sánh cần làm | Nếu không được ủng hộ |
|---|---|---|---|
| H1 | Sinh viên có bản nháp đủ dùng với ít thời gian thao tác hơn | Core vs thao tác thủ công trên nhiệm vụ tương đương | Sửa UX/phạm vi; không tuyên bố tiết kiệm thời gian |
| H2 | Plan và duyệt plan giúp bám tiêu chí đề cương | Core có HITL vs tự duyệt plan, cùng model/corpus | Không coi HITL là cải thiện chất lượng đã được chứng minh |
| H3 | Retrieval bằng Qdrant đáng chi phí với corpus Quick nhỏ | Qdrant vs direct-context cùng nguồn/budget | Ưu tiên phương án đơn giản hơn nếu chất lượng tương đương, chi phí thấp hơn |
| H4 | Reflection đáng thêm một lượt LLM trong Quick | Bật vs bỏ reflection, các phần khác giữ nguyên | Bỏ/đổi bước nếu không cải thiện coverage/faithfulness |
| H5 | Graph giúp truy vết nguồn | UI graph tối thiểu vs danh sách claim–evidence, sau khi có cả hai | Không ưu tiên Neo4j/UI graph; hiện chưa thể kết luận |
| H6 | Hệ thống tuân thủ ngân sách, phiên và trạng thái lỗi | Ca lỗi cố định, hai session, command lặp | Lỗi chức năng phải sửa; không bù bằng điểm chất lượng cao |

Tách citation correctness khỏi sự tồn tại của ID, tham khảo hướng đánh giá của [ALCE](https://arxiv.org/abs/2305.14627). Có thể dùng [Ragas](https://arxiv.org/abs/2309.15217) để hỗ trợ đánh giá retrieval/generation; bộ công thức và nhãn dưới đây là protocol của đề tài, không tự nhận là điểm Ragas chuẩn.

## Baseline và công bằng thực nghiệm

- **B0 · Thủ công:** trình duyệt/tài liệu + trình soạn thảo. Tính cả đọc và kiểm tra nguồn, không chỉ thời gian gõ.
- **B1 · RAG một lượt:** cùng corpus, embed/retriever/model và giới hạn output với core, nhưng không planner/HITL/reflection. Chưa có implementation baseline này.
- **B2 · Core hiện tại:** Quick Phase 3, kèm can thiệp của người dùng được ghi lại.
- **A1 · Direct-context:** thay retrieval bằng context từ cùng tập nguồn; cùng trần input/output. Tài liệu không vừa context phải có quy tắc cắt được công bố, không cho baseline lợi thế vô hạn.
- **A2 · Không reflection:** cùng plan và evidence, bỏ một lượt reflect để kiểm tra H4.
- **Sản phẩm thương mại:** chỉ so sánh mô tả hoặc một track thử nghiệm riêng, ghi gói/tài khoản/ngày và toàn bộ thao tác. Không kiểm soát được model/search của chúng nên không dùng làm bằng chứng nhân quả “kiến trúc của ta tốt hơn”.

Hai track độc lập: **fixed corpus** để phân tích nguyên nhân; **live web** để kiểm tra khả năng dùng ngoài thực tế. Không trộn trung bình hai track. Trong track cố định phải dùng cùng tài liệu và phần văn bản có thể thấy; không so hệ thống chỉ đọc 8 KB với baseline đọc full text mà bỏ qua khác biệt.

## Bộ ca và quy mô đề xuất

[cases.csv](benchmarks/cases.csv) có 20 nhiệm vụ CNTT: so sánh công nghệ, lựa chọn kiến trúc, kiểm tra giới hạn/phiên bản và các fixture thiếu/mâu thuẫn bằng chứng. Không chứa đáp án đoán sẵn, bài toán pháp luật/y khoa hoặc khẳng định một chủ đề “không tồn tại” khi chưa khảo sát.

Chọn thêm 2 ca pilot **ngoài** 20 ca đánh giá để hiệu chỉnh protocol. Với các cấu hình tự động B1/B2/A1/A2, chạy 3 lần mỗi ca thông thường phù hợp, ghi seed nếu provider hỗ trợ; nếu không, ghi không có seed tái lập. Quy mô và chi phí phải được cô/nhóm duyệt trước gọi API. Fixture lỗi không dùng để tính thời gian/điểm nghiên cứu thông thường.

Pilot người dùng đề xuất 8–12 sinh viên tự nguyện, thiết kế within-subject với nhiệm vụ ghép cặp và thứ tự đối trọng. Không để một người làm lại đúng câu hỏi vừa đọc đáp án. Đây là nghiên cứu thăm dò nhỏ, không đủ tự kết luận đại diện mọi sinh viên. Chưa tuyển người tham gia hoặc thu dữ liệu cá nhân.

## Chỉ số và cách tính

| Chỉ số | Định nghĩa vận hành | Không được hiểu nhầm |
|---|---|---|
| Task coverage | Số tiêu chí được giao có câu trả lời kèm bằng chứng / tổng tiêu chí trong rubric đã khóa trước chạy | Không chỉ đo plan do model tự chọn |
| Supported-claim rate | Claim hoàn toàn được đoạn nguồn đã đọc hỗ trợ / tổng factual claim được chấm | ID hợp lệ không làm claim thành supported; partial ghi riêng |
| Citation completeness | Claim cần dẫn chứng có ít nhất một citation hỗ trợ / tổng claim cần dẫn chứng | Citation ở References/code không tính |
| Citation precision | Cặp claim–citation có nguồn thật sự hỗ trợ / tất cả cặp claim–citation đã chấm | Phải đọc evidence, không chỉ mở URL |
| Structural validity | Citation ID thuộc nguồn đọc/index đúng session / tổng ID citation xuất hiện | Test phần mềm; không phải faithfulness |
| Source relevance | Nguồn đọc liên quan trực tiếp tới rubric / tổng nguồn đọc | Ghi riêng domain, nguồn gốc, phiên bản; không ép diversity tùy tiện |
| Human effort | Phút thao tác/đọc/sửa/kiểm tra đến bản nộp chấp nhận được | Tách khỏi thời gian model chạy |
| Wall time | Từ run đến draft; từ run đến approved gồm thời gian người duyệt | Báo cả hai, không giấu thời gian chờ |
| Cost/calls | Chi phí theo usage provider và đơn giá tại ngày chạy; search/LLM/embed/retry, gồm cả lượt lỗi | Byte budget hiện tại không phải tiền/tokens thực trả |
| Robustness | Ca lỗi cho trạng thái/hành vi mong đợi / tổng ca fixture theo danh mục | Không đưa ca lỗi vào điểm chất lượng báo cáo |

Hai người chấm độc lập các factual claim với nhãn supported/partial/contradicted/not_found và đoạn evidence tương ứng. Một người thứ ba hoặc cô phân xử khi bất đồng; báo tỷ lệ đồng thuận và cách phân xử. Bản corpus/context phải được lưu để nguồn web thay đổi không làm mất dấu. LLM-as-judge chỉ hỗ trợ rà, không thay người chấm và không dùng chính model sinh để tự xác nhận kết quả.

Nếu mẫu số bằng 0, ghi NA và lý do, không tự ghi 100%. Report lỗi được ghi failure; không loại khỏi tỷ lệ hoàn thành chỉ để làm đẹp số liệu.

## Mục tiêu dự kiến để duyệt trước đo

| Tiêu chí | Ngưỡng đề xuất | Trạng thái |
|---|---|---|
| State/budget/session/SSRF fixtures bắt buộc | 100% ca bắt buộc đạt | Có test tương ứng; không chứng minh dịch vụ thật |
| Structural citation validity | 100% trong tập chấm | CHƯA ĐO trên report thật |
| Supported-claim rate | ≥ 0,85 và không có claim sai trọng yếu trong kết luận chọn công nghệ | Mục tiêu đề xuất, cần cô duyệt |
| Task coverage | ≥ 0,80 trên rubric cố định | Mục tiêu đề xuất |
| H1 thời gian sinh viên | Median effort thấp hơn B0; báo chênh lệch và độ phân tán | CHƯA ĐO; không đặt sẵn % cải thiện |
| H3/H4 | Quality/cost trade-off tốt hơn hoặc giải thích được; không giảm chất lượng chỉ để nhanh | CHƯA ĐO |
| Chi phí | Không vượt ngân sách thử nghiệm B đã được duyệt; báo lượt thất bại | Chưa chốt B; không tự chi API trong việc lập hồ sơ |

Khóa ngưỡng sau pilot và trước holdout. Không hạ ngưỡng sau khi nhìn kết quả. Báo median/IQR, số mẫu, fail rate và chênh lệch paired; khoảng tin cậy nếu đủ điều kiện. Không kết luận significance chỉ từ một lần chạy.

## Gói dữ liệu cần có cho mỗi lượt chạy

run_id; task/config/model/version; Git commit + hash working tree nếu chưa commit; corpus hash; prompt/plan đã duyệt; nguồn/đoạn đã index và truncated; retrieved chunks; findings; report; thời gian từng stage; call/retry/usage/cost; can thiệp người dùng; lỗi. Trace, cost export và benchmark harness đầy đủ **chưa được triển khai**.

Các mẫu [runs.csv](benchmarks/runs.csv), [claims.csv](benchmarks/claims.csv), [user-study.csv](benchmarks/user-study.csv) chỉ có header để ghi thật. [RESULTS_TEMPLATE.md](benchmarks/RESULTS_TEMPLATE.md) cố ý giữ kết quả ở CHƯA ĐO. Không chép bảng 88,5%/96,8% từ brainstorm thành kết quả thực nghiệm.

## Điều kiện bắt đầu đo thật

G0 đã duyệt; tích hợp thật hoạt động; baseline/harness có test; khóa model/prompt/corpus/quy tắc cắt; rubric và assessor sẵn sàng; ngân sách được đồng ý. Chưa đạt các điều kiện này thì chỉ báo bằng chứng code/test và kế hoạch, không có bảng thắng/thua.
