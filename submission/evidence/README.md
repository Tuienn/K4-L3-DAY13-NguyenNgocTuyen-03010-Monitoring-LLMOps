# Evidence cá nhân

Đặt ảnh hoặc output text dùng để chấm vào thư mục này. Danh sách đầy đủ xem tại [docs/SUBMISSION.md](../../docs/SUBMISSION.md).

Tên file gợi ý:

```text
01-pytest.png
02-log-validator.png
03-dashboard-validator.png
04-structured-log.png
05-pii-redaction.png
06-trace-list.png
07-trace-waterfall.png
08-trace-metadata.png
09-prompt-versions.png
10-prompt-rollback.png
11-dashboard-overview.png
12-incident-metric.png
13-incident-log.png
14-incident-trace.png
```

Có thể dùng `.txt` cho output của tests/validators. Có thể tách dashboard thành nhiều ảnh nếu một ảnh không đọc rõ.

Ảnh `04`, `05`, `13` lấy từ terminal hoặc `data/logs.jsonl`. Ảnh `06`–`10`, `14` lấy từ project Langfuse cá nhân `day13-k4-l3b-<MSSV>` và nên nhìn thấy tên project. Không mở/chụp trang API Keys.

Từ `submission/REPORT.md`, dẫn ảnh bằng đường dẫn tương đối:

```markdown
![Trace waterfall](evidence/07-trace-waterfall.png)
```

Không commit secret, API key, PII thô hoặc evidence của học viên/lớp khác.

## Evidence CP0–CP2 hiện có

- `cp0-*`, `cp1-*`: output baseline và sau sửa; không làm giả kết quả baseline chưa đạt.
- `01-pytest.txt`, `02-log-validator.txt`, `03-dashboard-validator.txt`: kết quả kiểm tra cuối.
- `cp1-structured-log.jsonl`, `cp2-structured-log.jsonl`, `05-pii-redaction.txt`: log runtime đã scrub.
- `cp2-traces.json`: 22 traces được truy vấn từ project cá nhân, có URL, parent IDs, metadata và usage/cost. Đây là API export, không phải ảnh UI.
- `cp2-prompt-versions.json`, `cp2-prompt-rollback.json`: trạng thái prompt và lịch sử label từ API thật.
- `11-dashboard-overview.png/.svg/.html`, `cp2-dashboard-data.json`: dashboard export dựa trên log runtime thật; PNG chuyển từ SVG qua ImageMagick.

### Cách chụp ảnh Langfuse

1. Vào project `day13-k4-l3b-03010`, time range hôm nay, chụp danh sách ít nhất 10 traces: `06-trace-list.png`.
2. Mở URL trace baseline trong report, chụp waterfall thấy lab-agent-run/retrieval/generation: `07-trace-waterfall.png`.
3. Chụp metadata root (correlation ID, prompt name/label/version) và generation (model, input/output tokens, cost): `08-trace-metadata.png`; có thể tách ảnh nếu cần.
4. Vào prompt `day13-chat`, chụp v1/v2 và labels baseline/candidate/production: `09-prompt-versions.png`.
5. Chụp production hiện ở v1; đối chiếu trace production v2 và trace sau rollback v1 trong report: `10-prompt-rollback.png`. Không đổi label chỉ để tái tạo ảnh trước; API history đã ghi thao tác thật.

Không mở API Keys. Một số SDK metadata có `scope.attributes.public_key`; nếu UI hiển thị trường này, tránh đưa nó vào khung hình. Không chỉnh ảnh làm sai kết quả.
