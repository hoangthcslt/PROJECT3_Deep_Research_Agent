# 02 · Khảo sát hệ thống và lý do xây dựng

**Ngày đối chiếu: 09/11/2026.** Khảo sát dưới đây dựa trên tài liệu chính thức, không phải thử nghiệm trực tiếp các tài khoản. Chức năng có thể phụ thuộc gói hoặc workspace; “chưa xác minh” không có nghĩa là sản phẩm không có.

## Các phương án sinh viên có thể dùng

| Phương án | Năng lực được tài liệu hỗ trợ | Khi nào phù hợp? | Đối chiếu với dự án |
|---|---|---|---|
| Trình duyệt + ghi chú thủ công | Đây là baseline thao tác do đề tài định nghĩa, không phải một sản phẩm AI | Muốn chủ động đọc từng nguồn, ít tài liệu | Phải đo tổng thời gian tìm, đọc, viết và kiểm tra; không mặc định chậm hơn |
| ChatGPT / Deep research | Tổng hợp nhiều nguồn thành báo cáo để người dùng xem lại và hỏi tiếp; tính sẵn có tùy tài khoản/workspace. [Tài liệu OpenAI](https://learn.chatgpt.com/docs/web-search) | Cần một công cụ nghiên cứu dùng ngay | Dự án chưa chứng minh chất lượng, tốc độ hay giá tốt hơn; điểm có thể nghiên cứu là kiểm soát implementation và thực nghiệm theo rubric môn học |
| Gemini Deep Research | Lập kế hoạch cho đề tài, cho phép sửa trước khi bắt đầu; có thể sử dụng nhiều nguồn. [Google Help](https://support.google.com/gemini/answer/15719111?hl=en) | Muốn có luồng plan → research → report | **Duyệt kế hoạch không phải điểm mới độc quyền của dự án** |
| Perplexity Research | Tự tìm, đọc, điều chỉnh hướng nghiên cứu và tổng hợp report; có xuất/chia sẻ. [Perplexity Help](https://www.perplexity.ai/help-center/en/articles/10738684-what-is-research-mode) | Cần báo cáo nghiên cứu nhiều nguồn | Không được suy ra dự án vượt hơn chỉ vì dùng nhiều node hoặc có citation; không dùng tuyên bố tốc độ của hãng như phép đo của đề tài |
| Elicit | Có các workflow Research Agent, Research Report và Systematic Review; thiên về nghiên cứu bằng tài liệu học thuật. [Elicit Help](https://support.elicit.com/en/articles/14757543-getting-started-with-elicit-which-workflow-should-i-use) | Tổng quan bằng chứng từ paper và quy trình học thuật | Elicit phù hợp hơn nếu bài toán thật là systematic review; core hiện tại của dự án chỉ là khảo sát công nghệ từ web |

## Vì sao sinh viên nên dùng dự án này?

**Chưa có đủ bằng chứng để khẳng định sinh viên nói chung nên bỏ các công cụ trên.** Nếu chỉ cần báo cáo ngay, lựa chọn sản phẩm có sẵn là hợp lý. Lý do làm đồ án là xây và kiểm chứng một workflow có phạm vi học tập cụ thể, có implementation để khảo sát và thay đổi.

Giá trị dự kiến cần chứng minh:

1. **Theo tiêu chí đề cương:** câu hỏi, plan và output bám đúng bối cảnh đồ án; đo bằng rubric của giảng viên và độ phủ khía cạnh.
2. **Kiểm soát quy trình:** giảng viên/nhóm phát triển có thể kiểm tra state transition, budget và cách gắn nguồn trong code. Việc có thể xem code chưa đồng nghĩa chất lượng tốt hơn.
3. **Thực nghiệm tái lập:** cố định corpus, phiên bản và cấu hình để so sánh với baseline nhỏ. Tính linh hoạt này là mục tiêu nghiên cứu phần mềm; chưa có giao diện xuất đầy đủ trace thực nghiệm.
4. **Truy vết cho người học:** hỗ trợ sinh viên tìm lại evidence nhanh và đúng. Hiện đã có footnote; màn hình claim–evidence rõ ràng vẫn là đề xuất cần làm/đo nếu được duyệt.

## Những điều không được dùng làm luận điểm khác biệt

- Có tiếng Việt, có trích dẫn hay cho duyệt plan: các sản phẩm khác cũng hỗ trợ các kiểu tương tác này; không phải chứng minh tính mới.
- “Dùng LangGraph nên thông minh hơn”, “dùng Neo4j nên faithful hơn”: cần ablation, không suy ra từ tên công nghệ.
- “Miễn phí”, “rẻ hơn”, “nhanh hơn”, “đúng 95%”: chưa đo chi phí/tốc độ/chất lượng và không có bằng chứng để khẳng định.
- “Local nên dữ liệu không ra ngoài”: sai với cấu hình hiện tại; prompt và embedding gửi tới provider bên ngoài.

## Ma trận quyết định sử dụng

| Nhu cầu chính | Lựa chọn hợp lý hiện tại |
|---|---|
| Cần sản phẩm trưởng thành, dùng ngay | Thử sản phẩm có sẵn theo quyền truy cập; không ép dùng dự án |
| Cần khảo sát systematic review/paper | Xem công cụ chuyên học thuật; core web của dự án chưa đủ |
| Cần bảo vệ đồ án về workflow, kiểm soát nguồn và đánh giá tái lập | Dự án phù hợp làm đối tượng xây dựng/thực nghiệm |
| Cần bảo mật toàn bộ nội dung tại máy | Cấu hình hiện tại chưa đáp ứng; phải thiết kế provider/local model riêng |

## Kết luận khảo sát

Khoảng trống được đề xuất là **một trợ lý khảo sát công nghệ có thể kiểm tra và đánh giá theo bài tập của sinh viên CNTT**, không phải một deep-research engine tổng quát mới. Tính hữu ích cho sinh viên và lợi ích của từng thành phần được đặt thành giả thuyết trong [kế hoạch kiểm chứng](06-ke-hoach-kiem-chung.md). Chưa có kết quả so sánh thực nghiệm với các sản phẩm thương mại.
