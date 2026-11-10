# Nguồn khảo sát và phương pháp

Đã mở/đối chiếu ngày **09/11/2026**. Nguồn bên ngoài hỗ trợ mô tả năng lực hoặc phương pháp, không chứng minh dự án tốt hơn. Các file source và test trong repository hỗ trợ mô tả hiện trạng; phần chưa triển khai được ghi riêng trong tài liệu 07.

| ID | Nguồn chính thức / nghiên cứu gốc | Dùng cho |
|---|---|---|
| S01 | [ChatGPT Learn · Web search / Deep research](https://learn.chatgpt.com/docs/web-search) | Công cụ nghiên cứu nhiều nguồn, báo cáo và xem lại nguồn; phụ thuộc tài khoản/workspace |
| S02 | [Google Help · Use Deep Research](https://support.google.com/gemini/answer/15719111?hl=en) | Có kế hoạch và sửa plan trước khi chạy; không coi HITL là điểm mới độc quyền |
| S03 | [Perplexity Help · Research mode](https://www.perplexity.ai/help-center/en/articles/10738684-what-is-research-mode) | Luồng search/read/report/export; không dùng số quảng bá như kết quả đo của đề tài |
| S04 | [Elicit Help · Workflows](https://support.elicit.com/en/articles/14757543-getting-started-with-elicit-which-workflow-should-i-use) | Phân biệt công cụ paper/systematic review với core web của dự án |
| S05 | [LangGraph · Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | Chờ/phục hồi state bằng interrupt; cần checkpoint và kiểm thử caller đúng |
| S06 | [Qdrant · Filtering](https://qdrant.tech/documentation/search/filtering/) | Filter metadata cho retrieval; không thay thế auth |
| S07 | [ALCE · Gao và cộng sự, 2023](https://arxiv.org/abs/2305.14627) | Phân biệt chất lượng câu trả lời và chất lượng citation |
| S08 | [Ragas · Es và cộng sự](https://arxiv.org/abs/2309.15217) | Tách đánh giá retrieval/generation/faithfulness; protocol đề tài không tự nhận là score chuẩn |
| S09 | [PlantUML CLI](https://plantuml.com/command-line) và [Smetana/Graphviz](https://plantuml.com/graphviz-dot) | Render hình cục bộ từ source, SVG/PNG |

Không sử dụng bài tổng hợp/diễn đàn làm nguồn xác nhận tính năng. Không khảo sát giá/giới hạn tài khoản để khẳng định “rẻ hơn” hoặc “miễn phí”. Khi đo, phải ghi cấu hình/gói/ngày và mức usage thực tế. Nhận định về usefulness và trade-off trong hồ sơ là suy luận thiết kế hoặc giả thuyết có nhãn, không phải kết quả của các nguồn trên.
