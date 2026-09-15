# Load tests

k6 against `POST /v1/consume`.

## Hardware (committed report)

| Item | Value |
|------|--------|
| Machine | Apple Mac (arm64) |
| CPU | Apple M5 (10 cores) |
| RAM | 16 GB |
| OS | macOS 27.0 (Darwin) |
| Redis | `redis:7-alpine` Docker, localhost:6379 |
| API | uvicorn, 4 workers, `127.0.0.1:8080` |
| k6 | 2.2.0 |
| Date | 2026-09-15 |

## Result

From `loadtests/reports/k6-summary.json`:

| Metric | Value |
|--------|--------|
| RPS | ≈ 7,955 (`http_reqs.rate`) |
| p95 | ≈ 39.6 ms |
| Scenario | 200 VUs, 30s, unique keys, high policy limit |

HTML: `loadtests/reports/k6-report.html`

Observed limits on this machine: Python/uvicorn overhead, Redis RTT per Lua evaluate, shared CPU with k6.

## Reproduce

```bash
docker run -d --rm --name limitlab-redis -p 6379:6379 redis:7-alpine

cd apps/api
REDIS_URL=redis://localhost:6379/0 PYTHONPATH=. \
  uvicorn app.main:app --host 127.0.0.1 --port 8080 --workers 4

cd ../..
K6_WEB_DASHBOARD=true \
K6_WEB_DASHBOARD_EXPORT=loadtests/reports/k6-report.html \
  k6 run -e VUS=200 -e DURATION=30s loadtests/consume.js
```

Env: `BASE_URL`, `VUS`, `DURATION`, `POLICY_ID`, `KEY_PREFIX`.

## Methodology

Setup upserts a high-limit token-bucket policy. Each iteration uses a unique subject key (`bench-{vu}-{iter}`). Concurrency correctness: `packages/limiter/tests/test_concurrency_token_bucket.py`.
