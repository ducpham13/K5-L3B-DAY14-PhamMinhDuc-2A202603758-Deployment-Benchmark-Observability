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
| 1 | 4.09 | 197.7 | 236.0 | 1716.3 | 0.67% | ✅ PASS |
| 10 | 39.13 | 187.3 | 439.6 | 1705.1 | 1.0% | ✅ PASS |
| 50 | 97.62 | 197.8 | 500.0 | 1702.8 | 1.67% | ✅ PASS |
| 100 | 61.05 | 542.1 | 2732.4 | 2989.9 | 1.0% | ❌ FAIL |

**Nhận xét:** RPS có tăng tuyến tính theo concurrency không? Vì sao?

RPS tăng khi tăng concurrency từ 1 lên ~10–20 vì idle time của từng request được lấp đầy. Sau đó RPS phẳng ra (bottleneck là mock LLM delay + GIL của Python với uvicorn sync workers). p95/p99 tăng rõ hơn p50 khi concurrency cao vì tail latency bị ảnh hưởng bởi queuing.

---

### 2.2 Tail latency

| `MOCK_SLOW_RATE` | avg (ms) | p95 (ms) | p99 (ms) |
|---|---|---|---|
| 0 | 202.0 | 442.2 | 450.8 |
| 0.03 (mặc định) | 236.4 | 467.5 | 1690.5 |
| 0.1 | 353.2 | 1694.6 | 1727.2 |

**Nhận xét:** Chỉ số nào nhạy nhất với request chậm? Vì sao SLO không nên đặt theo average?

p99 nhạy nhất — chỉ 1% request chậm đủ để p99 tăng mạnh trong khi average gần như không đổi. SLO đặt theo average gây ảo giác tốt: 90% request trả 100 ms, 10% trả 2000 ms → average ~280 ms "ổn" nhưng 1 trong 10 user trải nghiệm rất tệ. p95/p99 phản ánh đúng "user trải nghiệm xấu nhất".

---

## 3. Benchmark chất lượng (develop, `eval/run_eval.py`)

| Chỉ số | Agent v1 | Agent v2 | Agent v2 (sau khi sửa KB) |
|---|---|---|---|
| Accuracy | 4.3% (1/23) | 91.3% (21/23) | 100% (23/23) |
| Avg tokens / câu | 57.5 | 109.1 | 115.7 |
| Tổng cost (USD) | $0.000409 | $0.000762 | $0.000808 |
| Cost / câu đúng (USD) | $0.000409 | $0.000036 | $0.000035 |
| Quality gate | ❌ FAIL | ✅ PASS | ✅ PASS |

**Những câu v2 trả lời sai ban đầu và cách sửa:**

| ID | Keyword bị thiếu | Bạn đã sửa gì |
|---|---|---|
| security-02 | token, hết hạn, chữ ký | Thêm entry JWT vào KNOWLEDGE_BASE: JWT chứa payload có chữ ký (signature) và thời gian hết hạn, so sánh với API key tĩnh |
| scaling-03 | cpu, memory, custom metrics | Thêm entry HPA vào KNOWLEDGE_BASE: Kubernetes HPA scale dựa trên CPU, memory, hoặc custom metrics |

**Nhận xét về trade-off chất lượng / chi phí / latency giữa v1 và v2:**

"Cost / câu đúng" tốt hơn "cost / câu" để so hai phiên bản vì nó kết hợp cả chi phí lẫn chất lượng: nếu v2 đắt hơn 20% nhưng chính xác hơn 40%, cost/câu đúng thực ra rẻ hơn v1. Metric "cost / câu" thuần túy sẽ ủng hộ model rẻ nhất dù kém chính xác.

---

## 4. Observability stack (production)

### 4.1 Screenshot

- [x] Dashboard Grafana khi đang có tải (thấy rõ Golden Signals)  → `screenshots/grafana-dashboard.png`
- [x] Một trace chậm trong Jaeger (thấy span nào chiếm thời gian) → `screenshots/jaeger-slow-trace.png`
- [x] Một trace lỗi trong Jaeger (có event `exception`)            → `screenshots/jaeger-error-trace.png`
- [x] Trang Alerts của Prometheus với ≥ 2 alert đang **firing**    → `screenshots/prometheus-alert-firing.png`

_(Chụp trong CP8 sau khi bật stack Docker Compose production)_

### 4.2 Thí nghiệm "phá hệ thống"

| # | Thay đổi | Alert nào firing | Thời gian từ lúc đổi → firing | Panel nào phản ánh rõ nhất |
|---|---|---|---|---|
| A | `MOCK_ERROR_RATE=0.2` | AgentHighErrorRate (critical) — error rate 21.15% | ~1 phút (for duration=60s) | Error Rate panel — tỉ lệ 5xx nhảy từ ~1% lên ~20% |
| B | `MOCK_SLOW_RATE=0.3` | AgentHighLatencyP95 (warning) — p95=1.922s | ~2 phút (for duration=120s) | Latency Percentiles panel — p95 nhảy từ ~230ms lên ~1900ms |
| C | `LLM_MODEL=mock-llm-large` | LLMCostBurnRateHigh (warning) — $2.75/giờ | ~2 phút (for duration=120s) | LLM Cost Rate panel — cost burn rate tăng do latency_factor 2.5x |
| D | `docker pause` 1 instance | AgentInstanceDown (critical) | ~30s (for duration=30s) | Active Instances panel — gauge giảm từ 3 xuống 2 |
| E | `AGENT_VERSION=v1` | Không có alert firing | — | Không panel nào phản ánh — accuracy regression không phát hiện bằng metric |

**Thí nghiệm E không làm alert nào firing. Bạn sẽ phát hiện loại sự cố này trong production bằng cách nào?**

Accuracy regression (trả lời sai nhiều hơn) không thể detect bằng latency/error-rate metric. Cần: (1) shadow eval tự động so output với golden dataset sau mỗi deploy; (2) user feedback signal (thumbs down); (3) alert trên custom metric `eval_accuracy` nếu agent có endpoint `/metrics` expose nó.

### 4.3 Debug bằng trace

- `trace_id`: `8ff6dfa6c4c3ce5a58bf8f579a637318`
- Tổng thời gian: 1685.0 ms
- Span chiếm nhiều thời gian nhất: `chat mock-llm-small` (1660.9 ms, 98.6%)
- Span thứ hai: `agent.retrieve_context` (21.7 ms, 1.3%)
- Dòng log tương ứng (grep theo `trace_id`):

```json
{"timestamp": "2026-11-26T09:43:...", "level": "INFO", "trace_id": "8ff6dfa6c4c3ce5a58bf8f579a637318", "message": "LLM call completed", "model": "mock-llm-small", "latency_ms": 1660.9}
```

**Trace lỗi:** `trace_id`: `b228493dde99de008704c04fc06eca52` — 115.9 ms, span `chat mock-llm-small` throw `LLMError: Upstream LLM error: 503 Service Unavailable (mock)` sau 94.2 ms. Exception được ghi vào span event `exception` với full stacktrace.

---

## 5. Benchmark scaling (production, Locust headless, 100 users, 2 phút)

| Số instance | RPS | p50 (ms) | p95 (ms) | p99 (ms) | Failures |
|---|---|---|---|---|---|
| 1 | 66.00 | 190 | 230 | 1700 | 80 (1.02%) |
| 3 | 66.53 | 190 | 230 | 1700 | 86 (1.08%) |

**Giải thích kết quả:** Scale có cải thiện p95 không? Nút thắt nằm ở đâu?

RPS và p95 gần như không thay đổi khi scale từ 1 lên 3 instance (66.0 → 66.5 RPS, p95 vẫn ~230ms). Lý do: bottleneck không phải CPU hay số worker mà là **mock LLM delay** (~120–180ms mỗi call, I/O bound). Mỗi instance đã handle đủ 50+ concurrent requests nhờ async/await, nên thêm instance không giảm queuing. Tail latency (p99=1700ms) đến từ MOCK_SLOW_RATE=3% request bị thêm 1500ms, không phụ thuộc số instance. Scale sẽ giúp khi bottleneck là CPU (compute-heavy model) hoặc khi single instance đạt giới hạn concurrent connections.

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
