# Implementation Plan: Rate Limiter Platform

**Branch**: `001-rate-limiter-platform` | **Date**: 2026-09-15 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-rate-limiter-platform/spec.md`

## Summary

Build **LimitLab**: a Redis-backed rate-limiting HTTP API with token bucket and
sliding window (per-policy), standard rate-limit headers, health/metrics, and a
public demo dashboard (policy form, burst fire, remaining + latency). Prove
~10k RPS with committed k6 reports. Local-first $0 development via Docker
Compose; public deploy deferred until the product works locally (free tiers
preferred).

## Technical Context

**Language/Version**: Python 3.12+ (API + limiter package); TypeScript (Next.js demo UI)

**Primary Dependencies**: FastAPI, uvicorn, redis (async), pydantic-settings;
Next.js (App Router) + lightweight chart lib for demo

**Storage**: Redis (counters/buckets; Lua for atomicity); policies in Redis
(JSON hashes) for v1 simplicity (no Postgres)

**Testing**: pytest (+ pytest-asyncio); k6 for load; optional Playwright later

**Target Platform**: Linux containers locally; later Fly/Render (API) + Vercel (UI)

**Project Type**: Monorepo web service + demo web app

**Performance Goals**: ~10k RPS consume/check on documented hardware (or honest max)

**Constraints**: Atomic updates; remaining ≥ 0; fail-closed default; no secrets in git;
$0 local build; open public demo (no auth)

**Scale/Scope**: Single-region v1; demo + API + loadtests; no multi-tenant SaaS

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status |
|------|--------|
| I. Correctness before throughput | PASS — Lua/atomic Redis; remaining never negative |
| II. Dual algorithms, policy-selectable | PASS — token_bucket + sliding_window |
| III. Redis SoT; failure mode explicit | PASS — default fail-closed; env toggle |
| IV. Measurable performance proof | PASS — loadtests/ + committed report |
| V. Observability & operability | PASS — /health, /metrics, Compose |
| VI. Demo UI is part of done | PASS — apps/web public dashboard |

Post-design: unchanged PASS.

## Project Structure

### Documentation (this feature)

```text
specs/001-rate-limiter-platform/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
└── tasks.md
```

### Source Code (repository root)

```text
apps/
├── api/                      # FastAPI service
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── routes/
│   │   │   ├── v1.py         # check, consume, reset, policies
│   │   │   ├── health.py
│   │   │   └── metrics.py
│   │   ├── redis_client.py
│   │   └── metrics_store.py
│   ├── tests/
│   ├── Dockerfile
│   └── pyproject.toml
└── web/                      # Next.js demo dashboard
    ├── app/
    ├── components/
    ├── lib/api.ts
    ├── package.json
    └── Dockerfile            # optional local compose

packages/
└── limiter/                  # Pure algorithms + Redis Lua wrappers
    ├── src/limitlab_limiter/
    │   ├── algorithms/
    │   │   ├── token_bucket.py
    │   │   └── sliding_window.py
    │   ├── lua/
    │   ├── policies.py
    │   └── types.py
    ├── tests/
    └── pyproject.toml

loadtests/
├── consume.js                # k6 script
├── reports/                  # committed HTML/JSON
└── README.md                 # hardware + how to reproduce

docker-compose.yml            # api + redis (+ web optional)
.env.example
README.md
```

**Structure Decision**: Constitution layout (`apps/api`, `apps/web`,
`packages/limiter`, `loadtests/`). Python monorepo with a shared limiter
package keeps algorithms unit-testable without HTTP. Next.js demo is separate
for free Vercel deploy later.

## Phase 0 / Phase 1

See [research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/), [quickstart.md](./quickstart.md).

## Cost posture (portfolio / student)

| Phase | Expected cost |
|-------|----------------|
| Local build + Compose + pytest + k6 | **$0** |
| GitHub repo | **$0** |
| Deploy (after local Done) | Prefer **free tiers**: Vercel (UI), Fly.io or Render (API), Upstash Redis free — watch idle sleep / request caps |
| Custom domain | Optional; `*.vercel.app` / `*.fly.dev` suffice for resume |

No paid services required to implement or prove the project locally.

## Complexity Tracking

No unjustified complexity. Policies stored in Redis (not Postgres) to keep
v1 free and operationally simple for a single-region demo.
