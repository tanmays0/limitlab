# LimitLab

Rate-limiting API with token bucket and sliding window algorithms, Redis Lua
atomicity, metrics, and a live demo dashboard.

## Links

| | |
|--|--|
| Demo | https://limitlab.vercel.app |
| Repository | https://github.com/tanmays0/limitlab |
| k6 report | [loadtests/reports/k6-report.html](./loadtests/reports/k6-report.html) |

## Architecture

```text
Demo:   Browser → Next.js /api/v1/* (in-memory) on Vercel
Bench:  Client → FastAPI → Redis Lua (packages/limiter)
```

- Algorithms: token bucket, sliding window (per policy)
- Redis path: atomic Lua; `REDIS_FAILURE_MODE=fail_closed` (default) or `fail_open`
- Demo path: in-process store + `POST /api/v1/burst`

## Quick start

### Demo UI (memory API)

```bash
cd apps/web
npm install && npm run dev
```

http://127.0.0.1:3000

### FastAPI + Redis

```bash
cp .env.example .env
docker run -d --rm --name limitlab-redis -p 6379:6379 redis:7-alpine

python3 -m venv .venv && source .venv/bin/activate
pip install -e "packages/limiter[dev]" -e "apps/api[dev]"
cd apps/api
REDIS_URL=redis://localhost:6379/0 PYTHONPATH=. \
  uvicorn app.main:app --host 127.0.0.1 --port 8080 --workers 4
```

```bash
cd apps/web
echo 'NEXT_PUBLIC_API_URL=http://127.0.0.1:8080' > .env.local
npm install && npm run dev
```

```bash
curl http://127.0.0.1:8080/health
curl 'http://127.0.0.1:8080/metrics?format=json'
```

`LIMITLAB_STORE=memory` selects the in-process store when Redis is unavailable.

## API

| Method | Path | Description |
|--------|------|-------------|
| POST | `/v1/check` | Peek allow/deny |
| POST | `/v1/consume` | Consume quota |
| POST | `/v1/burst` | Upsert policy + N consumes |
| POST | `/v1/reset` | Clear subject quota |
| GET/PUT | `/v1/policies/{id}` | Read / upsert policy |
| GET | `/health` | Liveness |
| GET | `/metrics` | Prometheus (`?format=json` for JSON; FastAPI) |

On the public demo, paths are prefixed with `/api`.

## Load test

| Metric | Result |
|--------|--------|
| RPS | ≈ 7,955 (`http_reqs.rate`) |
| p95 | ≈ 40 ms |
| Setup | Apple M5, Redis Docker, 4 uvicorn workers, 200 VUs, 30s |

Reproduce: [loadtests/README.md](./loadtests/README.md)  
Artifacts: [loadtests/reports/](./loadtests/reports/)

## Tests

```bash
source .venv/bin/activate
pytest packages/limiter apps/api -q
```

## Deploy

- UI: Vercel project `limitlab` (`apps/web`)
- Redis API: [fly.toml](./fly.toml), [render.yaml](./render.yaml)
- Notes: [DEPLOY.md](./DEPLOY.md)

## Spec

[specs/001-rate-limiter-platform/](./specs/001-rate-limiter-platform/)
