# Bộ ca và mẫu ghi kết quả

**Chưa có benchmark runner hoặc kết quả thực nghiệm.** Đây là vật liệu để khóa protocol với cô, không phải một bộ đáp án chuẩn đã gán nhãn.

- [cases.csv](cases.csv): 20 case ID duy nhất. BM01–BM16 là tác vụ khảo sát; cần chọn và freeze corpus. BM17–BM20 là fixture phải tạo, không được trộn vào điểm trung bình chất lượng thông thường. Tất cả có status=not_run.
- [runs.csv](runs.csv): một dòng mỗi lượt chạy/configuration; hiện chỉ có header. track phải phân biệt fixed_corpus/live_web/user_study. Cost/token thực tế phải ghi từ provider, không lấy byte budget làm hóa đơn.
- [claims.csv](claims.csv): một dòng mỗi người chấm/claim; label gồm supported, partial, contradicted, not_found. Dẫn evidence_span và source hash.
- [user-study.csv](user-study.csv): một dòng mỗi lượt làm nhiệm vụ, chỉ dùng mã người tham gia; hiện chưa thu dữ liệu.
- [RESULTS_TEMPLATE.md](RESULTS_TEMPLATE.md): báo cáo chỉ điền khi có artifact và data thật.

Thiết kế baseline, mẫu số metric, assessor và điều kiện bắt đầu ở [tài liệu 06](../06-ke-hoach-kiem-chung.md). Hai case pilot cần được chọn riêng ngoài bộ 20 case; chưa có corpus hoặc expected claims để tự động chấm đúng/sai.
