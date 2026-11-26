# Deployment Information

**Student:** Phạm Minh Đức — 2A202603758  
**Platform:** Render (Free Tier)  
**Agent:** `06-lab-complete/`

---

## Public URL

```
https://k5-l3b-day14-phamminhduc-2a202603758.onrender.com
```

---

## Test Commands & Results

```bash
BASE=https://k5-l3b-day14-phamminhduc-2a202603758.onrender.com
AGENT_API_KEY=k5-day14-721af16b

# Health check → 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"      # ✅ 200

# Readiness check → 503 (no Redis on free tier)
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"        # ✅ 503

# No API key → 401
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST "$BASE/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'                                     # ✅ 401

# Valid API key → 200
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST "$BASE/ask" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'                                     # ✅ 200
```

---

## Environment Variables (set on Render dashboard)

| Variable | Giá trị | Ghi chú |
|---|---|---|
| `PORT` | (Render tự cấp) | CMD Dockerfile dùng `${PORT}` |
| `REDIS_URL` | `redis://localhost:6379` | Free tier không có Redis; app tự skip rate-limit/cost-guard |
| `AGENT_API_KEY` | _(secret — không ghi vào đây)_ | Set qua Render Environment |
| `RATE_LIMIT_PER_MINUTE` | `10` | |
| `DAILY_BUDGET_USD` | `1.0` | |
| `ENVIRONMENT` | `production` | |

---

## Screenshots

- [Deployment dashboard](screenshots/deployment-dashboard.png)
- [Service running — /health 200](screenshots/health-check.png)

---

## Deploy Steps (Render)

1. Render Dashboard → **New +** → **Web Service**
2. Connect GitHub repo `ducpham13/K5-L3B-DAY14-PhamMinhDuc-2A202603758-...`
3. Runtime: **Docker**
4. Dockerfile Path: `06-lab-complete/Dockerfile`
5. Docker Build Context: `06-lab-complete`
6. Instance Type: **Free**
7. Add Environment Variables (bảng ở trên)
8. Click **Create Web Service**
9. Chờ deploy → Live (~1 phút)
