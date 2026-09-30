# Báo cáo cá nhân — CP0 đến CP2

- Họ tên: Nguyễn Ngọc Tuyền
- MSSV: 03010; lớp: K4-L3B.
- Repository: https://github.com/Tuienn/K4-L3-DAY13-NguyenNgocTuyen-03010-Monitoring-LLMOps
- Phạm vi: dừng ở CP2; chưa thực hiện challenge CP3 và nộp bài CP4.
- Commit: xem `git log --oneline`; mỗi checkpoint một commit.

## CP0 — Baseline

Đã dùng môi trường `.venv` có sẵn và cấu hình `.env` của học viên. Workload 10 request đều HTTP 200, correlation ID còn `MISSING`. Log validator 30/100, dashboard contract 6/6, public tests 22 passed. Prompt `day13-chat` label `production` chưa tồn tại trên Langfuse nên ứng dụng dùng local-fallback; đây là blocker sẽ xử lý ở CP2.

Evidence thực tế: [workload](evidence/cp0-workload.txt), [logs](evidence/cp0-log-validator.txt), [dashboard](evidence/cp0-dashboard-validator.txt), [tests](evidence/cp0-pytest.txt).
