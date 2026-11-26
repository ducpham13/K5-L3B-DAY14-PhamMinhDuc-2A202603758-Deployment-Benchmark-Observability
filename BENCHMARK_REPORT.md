# Benchmark & Observability Report — Day 14

> Mọi con số phải lấy từ report JSON / CSV / screenshot thật, không ước lượng.

**Họ tên:** Phạm Minh Đức  
**MSSV:** 2A202603758  
**Ngày chạy:** 2026-11-26  
**Môi trường:** Windows 11 Pro, WSL2, Docker Desktop 4 CPU / 8 GB RAM  

---

## 1. SLO của agent

| SLI | SLO | Lý do chọn ngưỡng này |
|---|---|---|
| p95 latency `/ask` | < 500 ms | Mock LLM có delay ~100–150 ms; p95 < 500 ms đảm bảo người dùng không cảm thấy lag |
| Error rate `/ask` | < 1 % | Sai sót hệ thống (không phải 4xx từ client) dưới 1% là mức chấp nhận được cho dịch vụ AI |
| Accuracy trên golden dataset | ≥ 80 % | Ngưỡng tối thiểu để agent có ích; v2 phải đạt 100% sau khi sửa KB |

---

## 2. Benchmark hiệu năng (develop, `load_test.py`)

### 2.1 Concurrency vs latency (agent v2)

| Concurrency | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Error rate | SLO |
|---|---|---|---|---|---|---|
| 1 | | | | | | |
| 10 | | | | | | |
| 50 | | | | | | |
| 100 | | | | | | |

_(Điền sau khi chạy load_test.py theo CP7 — xem `develop/reports/load_v2_c*.json`)_

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

RPS tăng khi tăng concurrency từ 1 lên ~10–20 vì idle time của từng request được lấp đầy. Sau đó RPS phẳng ra (bottleneck là mock LLM delay + GIL của Python với uvicorn sync workers). p95/p99 tăng rõ hơn p50 khi concurrency cao vì tail latency bị ảnh hưởng bởi queuing.

---

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | | | |
| 0.03 (mặc định) | | | |
| 0.1 | | | |

_(Điền sau khi chạy ba lần với `--concurrency 20 --requests 300`)_

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

p99 nhạy nhất — chỉ 1% request chậm đủ để p99 tăng mạnh trong khi average gần như không đổi. SLO đặt theo average gây ảo giác tốt: 90% request trả 100 ms, 10% trả 2000 ms → average ~280 ms "ổn" nhưng 1 trong 10 user trải nghiệm rất tệ. p95/p99 phản ánh đúng "user trải nghiệm xấu nhất".

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | | | |
| Avg tokens / câu | | | |
| Tổng cost (USD) | | | |
| Cost / câu đúng (USD) | | | |
| Quality gate | PASS / FAIL | PASS / FAIL | PASS / FAIL |

_(Điền từ `reports/eval_v1.json`, `reports/eval_v2.json`, `reports/eval_v2_fixed.json`)_

**Những câu v2 trả lời sai ban đầu và cách sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| | | |

_(Điền sau khi chạy eval và xem diff của `KNOWLEDGE_BASE` trong `develop/utils/mock_llm.py`)_

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

"Cost / câu đúng" tốt hơn "cost / câu" để so hai phiên bản vì nó kết hợp cả chi phí lẫn chất lượng: nếu v2 đắt hơn 20% nhưng chính xác hơn 40%, cost/câu đúng thực ra rẻ hơn v1. Metric "cost / câu" thuần túy sẽ ủng hộ model rẻ nhất dù kém chính xác.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [ ] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)  → `screenshots/grafana-dashboard.png`
- [ ] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian) → `screenshots/jaeger-slow-trace.png`
- [ ] Một trace lỗi trong Jaeger (có event `exception`)            → `screenshots/jaeger-error-trace.png`
- [ ] Trang Alerts của Prometheus với ≥ 2 alert đang **firing**    → `screenshots/prometheus-alert-firing.png`

_(Chụp trong CP8 sau khi bật stack Docker Compose production)_

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | | | |
| B | `MOCK_SLOW_RATE=0.3` | | | |
| C | `LLM_MODEL=mock-llm-large` | | | |
| D | `docker pause` 1 instance | | | |
| E | `AGENT_VERSION=v1` | | | |

_(Điền sau khi chạy từng thí nghiệm trong CP8)_

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

Accuracy regression (trả lời sai nhiều hơn) không thể detect bằng latency/error-rate metric. Cần: (1) shadow eval tự động so output với golden dataset sau mỗi deploy; (2) user feedback signal (thumbs down); (3) alert trên custom metric `eval_accuracy` nếu agent có endpoint `/metrics` expose nó.

### 4.3 Debug bằng trace

_(Điền sau khi tìm trace chậm nhất trong Jaeger)_

- `trace_id`: ...
- Tổng thời gian: ... ms
- Span chiếm nhiều thời gian nhất: ... (... ms, ...%)
- Dòng log tương ứng (grep theo `trace_id`):

```json

```

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | | | | | |
| 3 | | | | | |

_(Điền từ `production/benchmark-results/scale_1_stats.csv` và `scale_3_stats.csv`)_

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

Với 3 instance so với 1, p95 nên giảm vì request được phân tải qua Nginx — ít bị queue hơn. Nút thắt thường là mock LLM delay (I/O bound) hoặc số uvicorn worker. Nếu p95 không cải thiện nhiều, có thể Redis là bottleneck (rate-limit counter pipeline gọi nhiều lần/giây).

---

## 6. Kết luận

- 3 điều học được về benchmark & observability:
  1. **p95/p99 quan trọng hơn average** — average che giấu tail latency; SLO cần đặt theo percentile.
  2. **Tracing kết hợp log qua trace_id** — khi có lỗi, trace cho thấy span nào chậm, log cùng trace_id cho context chi tiết.
  3. **Eval tự động như CI gate** — quality gate với `--min-accuracy` chặn merge code làm giảm chất lượng, giống unit test cho AI.

- Nếu đưa agent này lên production thật, sẽ thêm:
  - Metric `llm_cost_usd_total` (counter) để alert khi budget gần cạn theo real-time.
  - Metric `eval_accuracy_ratio` expose sau mỗi shadow eval định kỳ.
  - Alert `HighCostPerAnswer` khi cost/câu tăng bất thường (model đổi, prompt bloat).
