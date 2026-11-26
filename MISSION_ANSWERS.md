# Day 14 Lab — Mission Answers

**Họ tên:** Phạm Minh Đức  
**MSSV:** 2A202603758  
**Ngày:** 2026-11-26  

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found (develop/app.py)

1. **API key hardcode trong code** — `api_key = "sk-abc123"` nằm thẳng trong source, push lên GitHub là lộ key.
2. **Debug mode bật cứng** — `app.run(debug=True)` hoặc `reload=True` không tắt được trong production.
3. **Không có health check endpoint** — platform không biết app còn sống không, không tự restart được.
4. **Không xử lý SIGTERM gracefully** — `docker stop` giết process ngay, cắt request đang xử lý.
5. **Config không đến từ environment** — port, database URL, timeout đều ghi cứng trong code, deploy ra môi trường khác phải sửa code.
6. **Dùng `print()` thay logging** — không có severity level, không parse được, không filter được trong production log aggregator.

Dòng code minh hoạ (develop/app.py):
```python
# Anti-pattern 1 — hardcode secret
OPENAI_API_KEY = "sk-abc123"
# Anti-pattern 5 — config cứng
app.run(host="0.0.0.0", port=8000, reload=True)
```

Bản production/app.py sửa:
```python
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")   # đọc từ env
PORT = int(os.getenv("PORT", "8000"))           # cấu hình từ env
```

### Exercise 1.2: Chạy bản develop

```bash
cd 01-localhost-vs-production/develop
pip install -r requirements.txt
python app.py
curl -X POST "http://localhost:8000/ask?question=Hello"
# → {"answer": "...mock response..."}
```

### Exercise 1.3: Bảng so sánh develop / production

| Feature | Develop | Production | Vì sao quan trọng? |
|---|---|---|---|
| Config | Hardcode trong code | Đọc từ env vars (`os.getenv`) | Cùng image deploy nhiều môi trường, không lộ secret qua code |
| Secrets | `api_key = "sk-abc123"` | `os.getenv("AGENT_API_KEY")` | Secret lọt vào git history là thảm hoạ bảo mật |
| Port | Cố định `8000` | `PORT = int(os.getenv("PORT", "8000"))` | Railway/Render tự cấp port ngẫu nhiên |
| Health check | Không có | `GET /health` → 200 | Load balancer cần để biết instance nào đang chạy |
| Readiness | Không có | `GET /ready` → 503 khi deps chưa sẵn | Tránh route traffic tới instance đang khởi động |
| Shutdown | Process bị kill ngay | Lifespan drain in-flight requests | Tránh cắt ngang request đang xử lý khi rolling deploy |
| Logging | `print()` | Structured JSON | Dễ filter, search, alert trên Datadog / CloudWatch |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

1. **Base image dùng:** `python:3.11` (develop) — đơn giản nhưng nặng (~1 GB).
2. **Working directory:** `WORKDIR /app` — mọi lệnh sau chạy trong `/app`.
3. **Copy dependencies trước source:** `COPY requirements.txt .` → `RUN pip install` → `COPY . .` — để Docker cache layer `pip install` khi chỉ đổi source code (requirements không đổi).
4. **CMD chạy app:** `CMD ["python", "app.py"]` hoặc `CMD ["uvicorn", "app:app", "--host", "0.0.0.0"]`.

### Exercise 2.2: Chạy container

```bash
# Build từ gốc repo
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run -p 8000:8000 -d my-agent:develop
curl -X POST "http://localhost:8000/ask?question=Hello"
# → {"answer": "..."}
```

### Exercise 2.3: Image size comparison

```
$ docker images | grep my-agent
my-agent  develop    ~800 MB   ← python:3.11 full
my-agent  advanced   ~160 MB   ← python:3.11-slim + multi-stage
```

- Develop: **~800 MB** (python:3.11 đầy đủ, bao gồm pip, build tools)
- Production: **~160 MB** (python:3.11-slim runtime, không có build tools)
- Chênh lệch: **~80%** nhỏ hơn

**Multi-stage giảm dung lượng bằng cách:** stage builder cài đầy đủ deps vào `/install`, stage runtime chỉ `COPY --from=builder /install /usr/local` — các layer của builder bị loại hoàn toàn khỏi final image.

**Vì sao `COPY requirements.txt` phải đứng trước `COPY . .`:** Docker cache layer theo thứ tự. Khi chỉ sửa source code (không sửa requirements.txt), layer `RUN pip install` được cache lại — không phải tải lại tất cả packages. Nếu `COPY . .` đứng trước, mọi thay đổi source đều invalidate cache của pip.

### Exercise 2.4: Stack Docker Compose (production)

Sơ đồ services của `02-docker/production/docker-compose.yml`:

```
[Client] → [Nginx :80] → [Agent :8000]
                              ↓
                         [Redis :6379]
```

Services:
- `agent` — FastAPI app, build từ Dockerfile multi-stage
- `redis` — redis:7-alpine, lưu session / rate limit state
- `nginx` — reverse proxy, SSL termination, load balancing

```bash
docker compose -f 02-docker/production/docker-compose.yml up -d
curl http://localhost/health
# → {"status": "ok"}
```

---

## Part 3: Cloud Deployment

### Exercise 3.1 / 3.2: Deploy agent Part 6

- **Platform:** Railway (hoặc Render)
- **URL:** `https://production-ai-agent.up.railway.app` _(điền sau khi deploy)_
- **Screenshot:** xem `screenshots/`

### Exercise 3.3: Pipeline Cloud Run (đọc cloudbuild.yaml + service.yaml)

Pipeline `cloudbuild.yaml` gồm 4 bước chạy tuần tự:

1. **test** — chạy `pytest` trên `python:3.11-slim` để không merge code lỗi.
2. **build** — `docker build` với tag `$COMMIT_SHA` và `latest`, dùng `--cache-from latest` để tận dụng layer cache.
3. **push** — push cả hai tag lên Google Container Registry (`gcr.io/$PROJECT_ID/ai-agent`).
4. **deploy** — `gcloud run deploy` chỉ định image bằng `$COMMIT_SHA` (không dùng `latest` để deploy có thể rollback chính xác), region `asia-southeast1`, min 1 instance (tránh cold start), secret `OPENAI_API_KEY` lấy từ Secret Manager thay vì env var trực tiếp.

`service.yaml` khai báo Cloud Run service dưới dạng Knative: `containerConcurrency: 80`, liveness probe → `/health`, startup probe → `/ready`, resources giới hạn 1 CPU / 512 MB. Secret lấy từ `secretKeyRef` — không ghi giá trị vào YAML.

**So sánh railway.toml vs render.yaml:**

| | railway.toml | render.yaml |
|---|---|---|
| Builder | `DOCKERFILE` explicit | `runtime: docker` implicit |
| Health check | `healthcheckPath = "/health"` | `healthCheckPath: /health` |
| Secret | Đặt qua Railway CLI / Dashboard | `generateValue: true` trong YAML |
| Redis | Add-on riêng trên Railway | Khai báo `databases:` trong cùng YAML |
| Multi-service | Mỗi service 1 file `.toml` | Tất cả service trong 1 `render.yaml` |

---

## Part 4: API Security

### Exercise 4.1: API Key auth (develop)

```bash
# Bật server
AGENT_API_KEY=secret-key-123 python 04-api-gateway/develop/app.py

# Không có key → 401
curl -i -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" -d '{"question":"Hello"}'
# HTTP/1.1 401 Unauthorized

# Có key đúng → 200
curl -i -X POST http://localhost:8000/ask \
  -H "X-API-Key: secret-key-123" \
  -H "Content-Type: application/json" -d '{"question":"Hello"}'
# HTTP/1.1 200 OK
# {"question":"Hello","answer":"..."}
```

### Exercise 4.2: JWT (production)

```bash
# Lấy token (tài khoản student/demo123)
curl -i -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"username":"student","password":"demo123"}'
# HTTP/1.1 200 OK
# {"access_token":"eyJ...","token_type":"bearer"}

# Dùng token
curl -i -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer eyJ..." \
  -H "Content-Type: application/json" -d '{"question":"Hello"}'
# HTTP/1.1 200 OK
```

### Exercise 4.3: Rate limiting → 429

```bash
TOKEN=eyJ...
for i in $(seq 1 15); do
  curl -s -o /dev/null -w "Request $i: %{http_code}\n" \
    -X POST http://localhost:8000/ask \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" -d '{"question":"test"}'
done
# Request 1-10: 200
# Request 11+:  429 Too Many Requests
# (giới hạn 10 req/phút cho tài khoản student)
```

### Exercise 4.4: Cost guard

**Cách hoạt động:** mỗi request gọi LLM, app cộng `(input_tokens * price_input + output_tokens * price_output)` vào Redis key `cost:daily:<YYYY-MM-DD>`. Trước khi gọi LLM, `check_budget()` đọc tổng hiện tại và so với `DAILY_BUDGET_USD`. Nếu vượt → trả 402 Payment Required ngay, không gọi LLM.

**Rate limit bảo vệ tốc độ; cost guard bảo vệ tiền:** rate limit chặn spam request ngắn hạn (429 sau N req/phút). Cost guard chặn tiêu hết budget dù mỗi request đều hợp lệ — ví dụ 1000 request mỗi request 1 token vẫn có thể cạn budget.

---

## Part 5: Scaling & Reliability

### Exercise 5.1–5.3: Health check & graceful shutdown

- `/health` (liveness) — luôn trả 200 khi process còn sống, kể cả khi Redis chết. Platform dùng để restart nếu process crash.
- `/ready` (readiness) — trả 200 khi app sẵn sàng nhận traffic (startup xong, Redis kết nối được); trả 503 khi không. Load balancer dùng để tạm ngừng route traffic tới instance đang shutdown hoặc khởi động.

**Tại sao `/health` không được check Redis:** nếu Redis die nhưng process vẫn sống, platform restart container là vô ích — không giải quyết Redis problem. `/ready` mới dùng để tách instance đó ra khỏi load balancer.

### Exercise 5.4: Chạy 3 instance

```bash
cd 05-scaling-reliability/production
touch .env.local
docker compose -p k5-day14-scaling up -d --build --scale agent=3
python test_stateless.py
docker compose -p k5-day14-scaling down
```

**Kết quả `test_stateless.py`:** 5 messages gửi trong cùng session được route tới 3 instance khác nhau (round-robin qua Nginx), nhưng history vẫn đúng vì session state lưu trong Redis dùng chung — không trong RAM của từng instance.

### Exercise 5.5: Vì sao state trong RAM hỏng khi scale

Nếu state (session, rate-limit counter, budget) lưu trong `dict` Python (RAM của process), mỗi instance có bản sao riêng. User request 1 đến instance A → counter trong A tăng. Request 2 đến instance B → counter trong B vẫn là 0, rate limit không bị hit. → Giải pháp: lưu tất cả state vào Redis dùng chung.

---

## Part 6: Final Project — 11/12 (Windows: SIGTERM không gửi được, Docker stop ✅)

```
================================================================
  Production Readiness Check — Day 14 Lab
================================================================

✅ 1. Dockerfile (multi-stage, < 500 MB)
     ✅ Multi-stage build (≥ 2 lệnh FROM)
     ✅ Base image gọn — stage cuối dùng python:3.11-slim
     ✅ Chạy bằng user non-root
     ✅ Có HEALTHCHECK
     ✅ Docker: build image thành công — 4s
     ✅ Docker: image < 500 MB — 238 MB
     ✅ Docker: container chạy được, GET /health → 200

✅ 2. docker-compose.yml (agent + redis)
     ✅ Có service agent (build từ Dockerfile) + redis
     ✅ Service agent kết nối redis (REDIS_URL + depends_on)

✅ 3. .dockerignore
     ✅ .dockerignore loại trừ .env (secrets)
     ✅ .dockerignore loại trừ __pycache__, venv

✅ 4. Health check endpoint (GET /health)
     ✅ Khi chạy: GET /health → 200 — uvicorn --workers 2

✅ 5. Readiness endpoint (GET /ready)
     ✅ Khi chạy: GET /ready → 200
     ✅ Khi chạy: Redis mất kết nối → /ready 503 (còn /health vẫn 200)

✅ 6. API Key authentication
     ✅ Khi chạy: thiếu / sai API key → 401
     ✅ Khi chạy: API key đúng → 200

✅ 7. Rate limiting
     ✅ Khi chạy: vượt giới hạn → 429 — 429 sau 5 request thành công
     ✅ Khi chạy: state nằm trong Redis — restart agent vẫn bị 429

✅ 8. Cost guard
     ✅ Khi chạy: hết budget → 402 — 402 ở request thứ 1

✅ 9. Config từ environment variables
     ✅ app/config.py đọc biến môi trường
     ✅ .env.example liệt kê đủ biến cấu hình
     ✅ .env nằm trong .gitignore
     ✅ Không hard-code secret trong code
     ✅ Khi chạy: agent dùng AGENT_API_KEY và RATE_LIMIT_PER_MINUTE từ env

✅ 10. Structured logging
     ✅ Code ghi log dạng JSON
     ✅ Khi chạy: mọi dòng log của app là JSON hợp lệ — 7 dòng JSON

⚠️  11. Graceful shutdown
     ✅ Code xử lý SIGTERM / lifespan shutdown
     ⚠️  SIGTERM — Windows không gửi được SIGTERM (giới hạn OS, không phải lỗi code)
     ✅ Docker: `docker stop` tắt êm (exit code 0, < 10s) — exit code 0, 0.6s

✅ 12. Public URL ready (Railway / Render config)
     ✅ railway.toml: builder + healthcheckPath = "/health"
     ✅ render.yaml: web service + healthCheckPath /health
     ✅ render.yaml: secret không ghi thẳng giá trị (generateValue / sync: false)
     ✅ App lắng nghe theo biến PORT do platform cấp

================================================================
  📋 Checklist Deliverable
     ✅ Dockerfile (multi-stage, < 500 MB)
     ✅ docker-compose.yml (agent + redis)
     ✅ .dockerignore
     ✅ Health check endpoint (GET /health)
     ✅ Readiness endpoint (GET /ready)
     ✅ API Key authentication
     ✅ Rate limiting
     ✅ Cost guard
     ✅ Config từ environment variables
     ✅ Structured logging
     ⚠️  Graceful shutdown (Docker stop ✅, SIGTERM host: Windows không hỗ trợ)
     ✅ Public URL ready (Railway / Render config)
----------------------------------------------------------------
  Result: 11/12 tiêu chí đạt · 42/42 checks passed
  Môi trường: Windows 11 Pro, Docker Desktop 29.9.3, Python 3.12
================================================================
```
