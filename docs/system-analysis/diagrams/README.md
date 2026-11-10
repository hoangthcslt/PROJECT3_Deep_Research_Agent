# Sơ đồ đã vẽ

Các hình được render cục bộ từ PlantUML, không gửi mô tả dự án tới dịch vụ vẽ bên ngoài. Mở [gallery](../index.html) hoặc chọn SVG/PNG bên dưới. Nguồn dùng chung style trong src/_style.iuml.

| Hình | Phạm vi | SVG / PNG / nguồn |
|---|---|---|
| 01 · Context và actor ngoài hệ thống | HIỆN TRẠNG | [SVG](svg/01-context-as-is.svg) · [PNG](png/01-context-as-is.png) · [PlantUML](src/01-context-as-is.puml) |
| 02 · UML use case A/B/C | HIỆN TRẠNG | [SVG](svg/02-use-cases-as-is.svg) · [PNG](png/02-use-cases-as-is.png) · [PlantUML](src/02-use-cases-as-is.puml) |
| 03 · Activity có swimlane | HIỆN TRẠNG | [SVG](svg/03-activity-as-is.svg) · [PNG](png/03-activity-as-is.png) · [PlantUML](src/03-activity-as-is.puml) |
| 04 · Sequence tạo/duyệt plan | HIỆN TRẠNG | [SVG](svg/04-sequence-plan.svg) · [PNG](png/04-sequence-plan.png) · [PlantUML](src/04-sequence-plan.puml) |
| 05 · Sequence nghiên cứu và dữ liệu | HIỆN TRẠNG | [SVG](svg/05-sequence-research.svg) · [PNG](png/05-sequence-research.png) · [PlantUML](src/05-sequence-research.puml) |
| 06 · Sequence duyệt/export | HIỆN TRẠNG | [SVG](svg/06-sequence-report.svg) · [PNG](png/06-sequence-report.png) · [PlantUML](src/06-sequence-report.puml) |
| 07 · UML session state machine | HIỆN TRẠNG | [SVG](svg/07-session-state.svg) · [PNG](png/07-session-state.png) · [PlantUML](src/07-session-state.puml) |
| 08 · UML lớp/miền logic | HIỆN TRẠNG | [SVG](svg/08-domain-class.svg) · [PNG](png/08-domain-class.png) · [PlantUML](src/08-domain-class.puml) |
| 09 · Component/deployment | HIỆN TRẠNG | [SVG](svg/09-components-deployment.svg) · [PNG](png/09-components-deployment.png) · [PlantUML](src/09-components-deployment.puml) |
| 10 · Master plan qua gate | ĐỀ XUẤT | [SVG](svg/10-master-plan-target.svg) · [PNG](png/10-master-plan-target.png) · [PlantUML](src/10-master-plan-target.puml) |
| 11 · UML use case mở rộng | ĐỀ XUẤT | [SVG](svg/11-use-cases-target.svg) · [PNG](png/11-use-cases-target.png) · [PlantUML](src/11-use-cases-target.puml) |
| 12 · Sequence nguồn Phase 4 | THIẾT KẾ PHASE 4 | [SVG](svg/12-phase4-source-selection.svg) · [PNG](png/12-phase4-source-selection.png) · [PlantUML](src/12-phase4-source-selection.puml) |

Hình lớp là mô hình logic theo code, không khẳng định đã có schema SQL. Component/deployment mô tả cấu hình và đường gọi trong code, không chứng minh dịch vụ thật đã chạy. Giảng viên là stakeholder nhận bản xuất ngoài ứng dụng, không phải account đã có.

## Render lại

Đã dùng PlantUML **1.2026.9**, Java sẵn có và layout Smetana. JAR tải từ [release chính thức](https://github.com/plantuml/plantuml/releases/tag/v1.2026.9), SHA-256:

`AA4A1D06F8911C4B842BEFF4828DD955BE431692B631A312D04C0E9FAB9581DE`

Không đưa JAR vào repository. SVG/PNG đã có nên chỉ cần Java/PlantUML khi muốn render lại. Tại repository root, đặt đường dẫn JAR rồi chạy:

```powershell
$diagramJarPath = 'C:/path/to/plantuml.jar'
java -jar $diagramJarPath -charset UTF-8 -tsvg -o '../svg' 'docs/system-analysis/diagrams/src/*.puml'
java -jar $diagramJarPath -charset UTF-8 -tpng -o '../png' 'docs/system-analysis/diagrams/src/*.puml'
```

Output path tương đối được tính từ thư mục source của từng hình. Nguồn cú pháp: [PlantUML CLI](https://plantuml.com/command-line), [layout Smetana](https://plantuml.com/graphviz-dot).
