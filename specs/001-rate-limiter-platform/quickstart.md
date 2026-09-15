# Quickstart (local validation)

Validate LimitLab without cloud spend.

## Prerequisites

- Docker + Docker Compose
- Python 3.12+ (for unit tests outside Compose, optional)
- Node 20+ (for web, optional until UI week)
- k6 (for load tests; install when needed)

## Bring-up

```bash
cp .env.example .env
docker compose up --build
```

Expected:

- API: `http://localhost:8080/health` → `{"status":"ok"}`
- Redis: healthy in Compose
- Web (when enabled): `http://localhost:3000`

## Smoke script

```bash
# Upsert policy
curl -s -X PUT http://localhost:8080/v1/policies/demo \
  -H 'content-type: application/json' \
  -d '{"limit":10,"window_seconds":10,"algorithm":"token_bucket"}'

# Check (no debit)
curl -s -X POST http://localhost:8080/v1/check \
  -H 'content-type: application/json' \
  -d '{"policy_id":"demo","key":"user:1"}'

# Consume until 429
for i in $(seq 1 12); do
  curl -s -o /tmp/ll.json -w "%{http_code}\n" -X POST http://localhost:8080/v1/consume \
    -H 'content-type: application/json' \
    -d '{"policy_id":"demo","key":"user:1"}'
done
```

Expect ~10× `200` then `429` with `Retry-After` and `X-RateLimit-Remaining: 0`.

## Tests

```bash
# from repo root once packages exist
pytest packages/limiter apps/api
```

## Load test (later)

```bash
k6 run loadtests/consume.js
# commit HTML/JSON under loadtests/reports/ with hardware notes
```

## Demo UI check

1. Open web URL
2. Set policy 10 / 10s
3. Send 50 requests — see allows then denies + latency chart
4. Switch algorithm → repeat

## Deploy

Deferred until local Definition of Done. Prefer free tiers; no paid plan required
for resume URLs if free quotas hold.
