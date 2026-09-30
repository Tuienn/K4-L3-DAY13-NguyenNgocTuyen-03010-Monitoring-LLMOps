# Alert runbooks — NguyenNgocTuyen-03010

Ba rule trong [alert_rules.yaml](../config/alert_rules.yaml) là định nghĩa alert, chưa nối Slack webhook hoặc triển khai scheduler. Kênh dự kiến: `#k4-l3b-alerts`; owner: NguyenNgocTuyen-03010. Không gửi thông báo thực tế trong lab.

Tính trên cửa sổ trượt 5 phút, đánh giá mỗi 30 giây và chỉ fire sau 5 phút liên tục vi phạm; reset duration khi điều kiện hết đúng. Error/retrieval chỉ đánh giá khi có ít nhất 20 request/attempt, mẫu số 0 là không có dữ liệu. Retrieval tính một kết quả terminal cho mỗi correlation ID từ `response_sent` hoặc `request_failed`, không cộng trùng observation.

## Alert 1

**HighLatencyP95** · warning · P95 > 3000ms trong 5 phút. SLO liên quan: request thành công trong 3000ms. User bị chậm phản hồi.

1. Mở `/dashboard`, xác định thời gian P95/P99 tăng và so với TTFT; kiểm tra traffic cùng thời gian.
2. Lọc `response_sent.latency_ms > 3000` trong `data/logs.jsonl`, lấy `correlation_id` và `trace_id`.
3. Mở trace cùng ID trên Langfuse, so sánh retrieval/generation; kiểm tra prompt version và token/cost.
4. Nếu prompt mới gây regression: chuyển production về baseline và xóa cache/restart app. Nếu retrieval chậm: giảm timeout, dùng fallback hoặc khôi phục backend. Chỉ disable practice incident đã bật, không sửa challenge riêng.
5. Chạy lại cùng workload, xác nhận P95 ≤ 3000ms và chất lượng không giảm. Đóng alert sau 5 phút metric ổn định, ghi trace/correlation ID và hành động.

## Alert 2

**HighErrorRate** · critical · request_failed / request_received > 2% trong 5 phút, tối thiểu 20 request. User nhận HTTP 500; tiêu hao error budget.

1. Xác định thời gian lỗi trên errors panel, xem breakdown `error_type`, traffic và retrieval success.
2. Chọn log `request_failed` trong thời gian đó, lấy correlation ID và mở trace tương ứng.
3. Kiểm tra span ERROR, upstream timeout và prompt metadata; xác nhận scope ảnh hưởng trước khi kết luận.
4. Khôi phục dependency, dùng fallback/retry có giới hạn nếu phù hợp, hoặc rollback phiên bản vừa triển khai. Tránh retry vô hạn làm tăng traffic/cost.
5. Chạy cùng input để xác nhận HTTP 200; kiểm tra error rate ≤ 2%, latency và quality. Đóng alert khi ổn định 5 phút, lưu nguyên log lỗi phục vụ điều tra.

## Alert 3

**LowRetrievalSuccess** · warning · retrieval success < 90% trong 5 phút, tối thiểu 20 attempts. User không lấy được context hoặc request lỗi.

1. Đọc retrieval success trên errors panel; đối chiếu error rate và latency cùng thời gian.
2. Lọc `tool_name=retrieval`, `tool_success=false`, lấy correlation ID rồi tìm trace.
3. Kiểm tra retrieval span lỗi/timeout, trạng thái vector store, doc_count và fallback; doc_count > 0 chưa chứng minh relevance.
4. Khôi phục vector store hoặc dùng context fallback an toàn; theo dõi quality để tránh trả lời sai. Ghi rõ mitigation đang dùng.
5. Chạy cùng workload, xác nhận retrieval success ≥ 90%, error rate ≤ 2% và quality ≥ 0.75 trước khi đóng alert sau 5 phút ổn định.
