# Deploy

| | URL |
|--|-----|
| Demo | https://limitlab.vercel.app |
| Repository | https://github.com/tanmays0/limitlab |

## Path A — public demo (done)

Next.js `/api/v1/*` in-memory limiter on Vercel. SSO disabled.  
Live: https://limitlab.vercel.app

Leave `NEXT_PUBLIC_API_URL` unset so the UI uses same-origin `/api`.

## Path B — Redis FastAPI (optional, not required)

For multi-instance Redis / production-style hosting. Config:
[fly.toml](./fly.toml), [render.yaml](./render.yaml), [apps/api/Dockerfile](./apps/api/Dockerfile).

```bash
fly apps create limitlab-api
fly secrets set \
  REDIS_URL='rediss://…' \
  REDIS_FAILURE_MODE=fail_closed \
  CORS_ORIGINS='https://limitlab.vercel.app'
fly deploy
```

Render: Blueprint from this repo; set `REDIS_URL` and `CORS_ORIGINS`.

Optional UI wire-up: Vercel env `NEXT_PUBLIC_API_URL=https://YOUR-APP.fly.dev` (no trailing slash), then redeploy.
