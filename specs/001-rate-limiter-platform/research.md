# Research: Rate Limiter Platform

## 1. API runtime

- **Decision**: FastAPI + uvicorn (Python 3.12+)
- **Rationale**: Matches ops-mcp Python depth on the resume; async Redis clients;
  clear OpenAPI for recruiters; constitution preference.
- **Alternatives considered**: Node/Express (one-language monorepo) — rejected to
  diversify stack next to JS UI; Go — higher RPS ceiling but slower student
  iteration and weaker portfolio pairing with ops-mcp.

## 2. Counter store & atomicity

- **Decision**: Redis with Lua scripts (or MULTI/EXEC) for consume/check/reset
- **Rationale**: Industry-standard for rate limits; atomicity under concurrency
  is interview-critical; Docker image is free locally.
- **Alternatives considered**: In-memory only — fails multi-worker and demo
  realism; Postgres counters — heavier and slower for 10k RPS path.

## 3. Algorithms

- **Decision**: Token bucket + sliding window log (or sorted-set window), selectable per policy
- **Rationale**: Spec requires both; token bucket shows burst tradeoffs; sliding
  window shows smoother fairness — perfect interview contrast.
- **Alternatives considered**: Fixed window only — too weak for hire bar;
  leaky bucket as third — deferred to v2 (YAGNI).

## 4. Policy storage

- **Decision**: Redis hashes/JSON keys (`policy:{id}`) for v1
- **Rationale**: $0 extra DB; same Compose stack; enough for demo + load tests.
- **Alternatives considered**: Postgres/SQLite — adds deploy cost/complexity
  without hire upside for v1.

## 5. Failure mode

- **Decision**: Env `REDIS_FAILURE_MODE=fail_closed|fail_open`, default `fail_closed`
- **Rationale**: Portfolio + interview: default safe; toggle proves you thought
  about availability vs correctness.
- **Alternatives considered**: Hard-coded fail-open — bad for rate limiter story.

## 6. Demo UI

- **Decision**: Next.js App Router (TypeScript), anonymous open demo
- **Rationale**: Free Vercel deploy later; resume-friendly; matches “deployed UI
  required” rule; zero login friction for recruiters.
- **Alternatives considered**: Vite SPA — also fine, slightly less “default hire
  stack”; auth-walled demo — hurts click-through from resume.

## 7. Load proof

- **Decision**: k6 scripts + committed HTML/JSON under `loadtests/reports/`
- **Rationale**: Free OSS; HTML report is screenshot-friendly for interviews.
- **Alternatives considered**: Locust — also free; k6 preferred for smaller
  scripts and static HTML reports.

## 8. Deploy targets (deferred)

- **Decision**: Defer paid/cloud until local Definition of Done; then free tiers
  (Vercel UI + Fly/Render API + Upstash Redis free)
- **Rationale**: User constraint — build free first; avoid surprise bills.
- **Alternatives considered**: Always-on paid Redis/VM — unnecessary for v1 hire
  demo if free tiers hold.

## 9. Metrics format

- **Decision**: Prometheus text on `/metrics` plus simple JSON summary for demo UI
- **Rationale**: Familiar to backend interviewers; JSON keeps dashboard simple.
- **Alternatives considered**: JSON-only — fine but weaker “ops” signal.

## 10. Headers

- **Decision**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
  (unix seconds); `Retry-After` on 429
- **Rationale**: Spec + IETF-ish conventions recruiters/interviewers recognize.
- **Alternatives considered**: Draft IETF `RateLimit-*` only — less common in
  tutorials; can add later as aliases.
