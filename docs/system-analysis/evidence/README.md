# Bằng chứng kiểm tra hồ sơ và phần mềm

- [software-checks.txt](software-checks.txt): log chạy lại tests/build/lint/snapshot test khi rà soát, kèm exit code. 60 test backend đạt; production build frontend đạt; lint exit 0 còn cảnh báo React; snapshot test đạt.
- [source-manifest.csv](source-manifest.csv): hash 65 file code/test/manifest phụ thuộc tại thời điểm kiểm tra. Không bao gồm .env hoặc giá trị credential. Git HEAD không đại diện đầy đủ vì working tree chưa commit; log có aggregate manifest hash.
- [artifact-checks.txt](artifact-checks.txt): kết quả kiểm tra file/link, CSV và SVG/PNG của hồ sơ.

Các log này là bằng chứng phần mềm và artifact. Không phải phép đo chất lượng research, chạy provider/database thật, usability test hoặc xác nhận cô đã duyệt. Hình được render cục bộ và xem lại bố cục; chưa kiểm tra tương tác gallery trong browser tự động.
