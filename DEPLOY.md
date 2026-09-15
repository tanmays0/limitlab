# Deploy

| | URL |
|--|-----|
| Demo | https://limitlab.vercel.app |
| Repository | https://github.com/tanmays0/limitlab |

Public demo: Next.js `/api/v1/*` (in-memory) on Vercel. SSO disabled.

## Redis-backed FastAPI

Config: [fly.toml](./fly.toml), [render.yaml](./render.yaml), [apps/api/Dockerfile](./apps/api/Dockerfile).

```bash
fly apps create limitlab-api
fly secrets set \
  REDIS_URL='rediss://…' \
  REDIS_FAILURE_MODE=fail_closed \
  CORS_ORIGINS='https://limitlab.vercel.app'
fly deploy
```

Render: Blueprint from this repo; set `REDIS_URL` and `CORS_ORIGINS`.

Point the UI at FastAPI with Vercel env `NEXT_PUBLIC_API_URL` (no trailing slash). Leave unset for the embedded `/api` demo.
