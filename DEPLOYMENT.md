# Deployment Information

**Student:** Phạm Minh Đức — 2A202603758  
**Platform:** Railway  
**Agent:** `06-lab-complete/`

---

## Public URL

```
https://production-ai-agent.up.railway.app
```

_(Điền URL thật sau khi deploy xong)_

---

## Test Commands

```bash
BASE=https://production-ai-agent.up.railway.app
AGENT_API_KEY=<your-key-from-railway-dashboard>

# Health check → 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/health"

# Readiness check → 200
curl -sS -o /dev/null -w '%{http_code}\n' "$BASE/ready"

# No API key → 401
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST "$BASE/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'

# Valid API key → 200
curl -sS -o /dev/null -w '%{http_code}\n' \
  -X POST "$BASE/ask" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $AGENT_API_KEY" \
  -d '{"question":"Hello"}'
```

---

## Environment Variables (set on Railway dashboard)

| Variable | Giá trị | Ghi chú |
|---|---|---|
| `PORT` | (Railway tự cấp) | CMD Dockerfile dùng `${PORT}` |
| `REDIS_URL` | `redis://...railway.internal:6379` | Redis add-on Railway |
| `AGENT_API_KEY` | _(secret — không ghi vào đây)_ | Set qua Railway Variables |
| `RATE_LIMIT_PER_MINUTE` | `10` | |
| `DAILY_BUDGET_USD` | `1.0` | |
| `ENVIRONMENT` | `production` | |

---

## Screenshots

- [Deployment dashboard](screenshots/deployment-dashboard.png)
- [Service running — /health 200](screenshots/health-check.png)
- [Redis add-on connected — /ready 200](screenshots/ready-check.png)
- [API key test — /ask 200](screenshots/ask-200.png)

---

## Deploy Steps (Railway)

```bash
cd 06-lab-complete
npm i -g @railway/cli
railway login
railway init
railway add --plugin redis          # Redis add-on (auto-sets REDIS_URL)
railway variables set AGENT_API_KEY=<generated-secret>
railway up
railway domain                      # → public URL
```

Sau khi deploy, kiểm tra:
```bash
python check_production_ready.py --public-url https://production-ai-agent.up.railway.app
```
