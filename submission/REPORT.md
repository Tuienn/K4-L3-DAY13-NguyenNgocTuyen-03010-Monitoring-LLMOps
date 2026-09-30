# Báo cáo cá nhân — CP0 đến CP2

- Họ tên: Nguyen Ngoc Tuyen
- MSSV: 03010; lớp: K4-L3B.
- Repository: https://github.com/Tuienn/K4-L3-DAY13-NguyenNgocTuyen-03010-Monitoring-LLMOps
- Phạm vi: dừng ở CP2; chưa thực hiện challenge CP3 và nộp bài CP4.
- Commit: xem `git log --oneline`; mỗi checkpoint một commit.

## CP0 — Baseline

Đã dùng môi trường `.venv` có sẵn và cấu hình `.env` của học viên. Workload 10 request đều HTTP 200, correlation ID còn `MISSING`. Log validator 30/100, dashboard contract 6/6, public tests 22 passed. Prompt `day13-chat` label `production` chưa tồn tại trên Langfuse nên ứng dụng dùng local-fallback; đây là blocker sẽ xử lý ở CP2.

Evidence thực tế: [workload](evidence/cp0-workload.txt), [logs](evidence/cp0-log-validator.txt), [dashboard](evidence/cp0-dashboard-validator.txt), [tests](evidence/cp0-pytest.txt).

## CP1 — Logging và PII

Log validator đạt **100/100** trên workload 10 request; không thiếu metadata, 10 correlation ID, không phát hiện PII. Tests: **25 passed**. Middleware giữ header `req-<8-hex>` hợp lệ, sinh ID khi thiếu/sai, xóa context trước và sau request, trả `x-request-id` và `x-response-time-ms`. `/chat` bind user hash, session, feature, model, env trước log đầu tiên. Scrubber xử lý đệ quy cả payload và metadata sau exception formatting, trước file writer/JSON renderer; che email, điện thoại VN, CCCD và thẻ. Test concurrency đối chiếu log/response của từng request để phát hiện rò context.

Evidence: [validator](evidence/cp1-log-validator.txt), [tests](evidence/cp1-pytest.txt), [workload](evidence/cp1-workload.txt), [structured logs đã scrub](evidence/cp1-structured-log.jsonl). Log baseline được giữ riêng tại `/tmp` để không trộn vào phép đo mới.
