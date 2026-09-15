# Tasks: Rate Limiter Platform

**Input**: Design documents from `/specs/001-rate-limiter-platform/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — constitution requires algorithm edge-case tests and burst correctness.

**Organization**: Grouped by user story for incremental MVP delivery. Local $0 first; deploy last.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1–US6 map to spec user stories
- Paths follow plan.md (`apps/api`, `apps/web`, `packages/limiter`, `loadtests/`)

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Monorepo skeleton, tooling, Compose — no cloud cost

- [x] T001 Create directory layout `apps/api`, `apps/web`, `packages/limiter`, `loadtests/reports` per plan.md
- [x] T002 Initialize Python package `packages/limiter` with `packages/limiter/pyproject.toml` (name `limitlab-limiter`)
- [x] T003 Initialize FastAPI app package `apps/api/pyproject.toml` depending on `limitlab-limiter`
- [x] T004 [P] Add root `.gitignore`, `.env.example`, and `README.md` stub (local-only, no secrets)
- [x] T005 [P] Add `docker-compose.yml` with `redis` and `api` services
- [x] T006 [P] Add `apps/api/Dockerfile` (Python 3.12 slim + uvicorn)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Config, Redis client, types, failure mode, health — blocks all stories

**⚠️ CRITICAL**: No user story work until this phase completes

- [x] T007 Define shared types/enums in `packages/limiter/src/limitlab_limiter/types.py` (Algorithm, Decision, Policy)
- [x] T008 Implement pydantic Settings in `apps/api/app/config.py` (`REDIS_URL`, `REDIS_FAILURE_MODE` default `fail_closed`)
- [x] T009 Implement async Redis client factory in `apps/api/app/redis_client.py`
- [x] T010 Implement failure-mode helper in `apps/api/app/failure_mode.py` (fail_closed vs fail_open)
- [x] T011 Create FastAPI app entry in `apps/api/app/main.py` with CORS for demo origin
- [x] T012 Implement `GET /health` in `apps/api/app/routes/health.py`
- [x] T013 Wire Compose env so `docker compose up` serves `/health` → ok

**Checkpoint**: Foundation ready — stories can proceed

---

## Phase 3: User Story 1 — Enforce Limit on Consume (Priority: P1) 🎯 MVP

**Goal**: Token-bucket consume with headers, 429 + Retry-After, atomic Redis updates

**Independent Test**: Policy 10/10s; 10 allows then 429; remaining never negative

### Tests (write first — must fail before impl)

- [x] T014 [P] [US1] Unit tests for token bucket edge cases in `packages/limiter/tests/test_token_bucket.py`
- [x] T015 [P] [US1] Concurrent-admit safety test sketch in `packages/limiter/tests/test_concurrency_token_bucket.py`

### Implementation

- [x] T016 [US1] Implement token bucket Lua + Python wrapper in `packages/limiter/src/limitlab_limiter/algorithms/token_bucket.py` and `packages/limiter/src/limitlab_limiter/lua/`
- [x] T017 [US1] Implement policy get/upsert primitives needed for consume in `packages/limiter/src/limitlab_limiter/policies.py`
- [x] T018 [US1] Add rate-limit header helper in `apps/api/app/headers.py`
- [x] T019 [US1] Implement `POST /v1/consume` in `apps/api/app/routes/v1.py`
- [x] T020 [US1] Seed default policy path for local smoke (upsert via API or startup demo policy) documented in `README.md`
- [x] T021 [US1] API integration test for consume allow→deny in `apps/api/tests/test_consume.py`

**Checkpoint**: MVP consume works via curl / Compose

---

## Phase 4: User Story 2 — Check Without Consuming (Priority: P1)

**Goal**: `POST /v1/check` peeks without debit

**Independent Test**: remaining unchanged across two checks; consume still works after

### Tests

- [x] T022 [P] [US2] Unit/integration tests for check non-debit in `apps/api/tests/test_check.py`

### Implementation

- [x] T023 [US2] Implement check path in limiter package (`packages/limiter/src/limitlab_limiter/algorithms/token_bucket.py` check mode or shared engine)
- [x] T024 [US2] Implement `POST /v1/check` in `apps/api/app/routes/v1.py`

**Checkpoint**: check + consume both correct

---

## Phase 5: User Story 3 — Configure Policies (Priority: P2)

**Goal**: PUT/GET policies; switch algorithm field (sliding window impl in US3b below)

**Independent Test**: Upsert `demo`, GET returns same; invalid limit rejected

### Tests

- [x] T025 [P] [US3] Policy validation tests in `packages/limiter/tests/test_policies.py`
- [x] T026 [P] [US3] API tests for PUT/GET policies in `apps/api/tests/test_policies.py`

### Implementation

- [x] T027 [US3] Complete policy Redis storage CRUD in `packages/limiter/src/limitlab_limiter/policies.py`
- [x] T028 [US3] Implement `PUT /v1/policies/{id}` and `GET /v1/policies/{id}` in `apps/api/app/routes/v1.py`
- [x] T029 [US3] Implement sliding window algorithm + Lua in `packages/limiter/src/limitlab_limiter/algorithms/sliding_window.py`
- [x] T030 [US3] Route consume/check to algorithm from policy; unit tests in `packages/limiter/tests/test_sliding_window.py`

**Checkpoint**: Both algorithms selectable per policy

---

## Phase 6: User Story 4 — Reset Key Quota (Priority: P2)

**Goal**: `POST /v1/reset` clears subject state

**Independent Test**: Exhaust key → reset → next consume allows

### Tests

- [x] T031 [P] [US4] Reset tests in `apps/api/tests/test_reset.py`

### Implementation

- [x] T032 [US4] Implement reset in limiter package `packages/limiter/src/limitlab_limiter/reset.py`
- [x] T033 [US4] Implement `POST /v1/reset` in `apps/api/app/routes/v1.py`

**Checkpoint**: Demo loops are repeatable

---

## Phase 7: User Story 5 — Live Demo Dashboard (Priority: P2)

**Goal**: Public Next.js demo — policy form, burst, stream, remaining, latency chart

**Independent Test**: Browser-only: set policy → send 50 → see allows then denies + chart

### Implementation

- [x] T034 [US5] Scaffold Next.js app in `apps/web` (TypeScript App Router)
- [x] T035 [US5] API client in `apps/web/lib/api.ts` (policies, consume, reset, check)
- [x] T036 [US5] Policy form + algorithm select in `apps/web/components/PolicyForm.tsx`
- [x] T037 [US5] Burst runner + allow/deny stream in `apps/web/components/BurstPanel.tsx`
- [x] T038 [US5] Remaining readout + latency chart in `apps/web/components/LatencyChart.tsx`
- [x] T039 [US5] Wire page in `apps/web/app/page.tsx`; env `NEXT_PUBLIC_API_URL`
- [x] T040 [US5] Optional Compose `web` service; document `npm run dev` in `README.md`

**Checkpoint**: Local demo matches interview script (minus public URL)

---

## Phase 8: User Story 6 — Throughput Proof & Metrics (Priority: P3)

**Goal**: `/metrics`, k6 script + committed report with hardware notes

**Independent Test**: Open report in repo; hit `/metrics` after traffic; health still ok

### Implementation

- [x] T041 [US6] Implement metrics counters + `GET /metrics` in `apps/api/app/routes/metrics.py` and `apps/api/app/metrics_store.py`
- [x] T042 [US6] Write k6 script `loadtests/consume.js` targeting consume
- [x] T043 [US6] Run k6 locally; save HTML/JSON under `loadtests/reports/`; note hardware in `loadtests/README.md`
- [x] T044 [US6] Tune Redis/pipeline/uvicorn workers if needed to approach ~10k RPS; document honest max if below

**Checkpoint**: Resume bullet has evidence folder

---

## Phase 9: Polish & Ship Prep (still $0 until you choose deploy)

**Purpose**: Docs, security scan, deploy-when-ready

- [x] T045 [P] Expand root `README.md` — architecture, quickstart, interview demo script, cost notes
- [x] T046 [P] Document `REDIS_FAILURE_MODE` tradeoff in `README.md`
- [ ] T047 Validate full flow against `specs/001-rate-limiter-platform/quickstart.md`
- [ ] T048 Run Strix (or dep/secret scan) per user rules; remediate criticals — **no production scan without approval**
- [ ] T049 **Deploy (optional / after local Done)**: API to Fly/Render free, Redis Upstash free, UI to Vercel free — confirm $0 quotas before enabling always-on
- [ ] T050 Add live demo + health URLs to `README.md` once deployed

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 → Phase 2 → US1 (MVP) → US2 → US3 → US4 → US5 → US6 → Polish
- US2 depends on US1 consume engine
- US3 sliding window can start after policy storage; must land before US5 algorithm switch demo
- US5 needs US1–US4 API surface
- US6 can start metrics after US1; k6 report after API is stable
- T049–T050 only after local Done (user: defer deploy cost)

### User Story Independence

| Story | Independent test |
|-------|------------------|
| US1 | curl consume allow→429 |
| US2 | check does not debit |
| US3 | PUT/GET + algorithm switch |
| US4 | reset restores allows |
| US5 | browser burst demo |
| US6 | report + /metrics |

### Parallel Opportunities

- T004–T006 in parallel during Setup
- T014–T015 tests in parallel before T016
- T025–T026 in parallel
- T045–T046 docs in parallel

---

## Parallel Example: User Story 1

```bash
# Tests first:
Task: T014 unit token bucket
Task: T015 concurrency sketch

# Then impl:
Task: T016 token bucket Lua
Task: T017 policies primitives
Task: T018 headers helper
```

---

## Implementation Strategy

### MVP First (US1 only)

1. Phase 1 + 2
2. US1 consume + token bucket
3. Stop — validate with quickstart smoke curl loop
4. Resume bullet not complete yet (need UI + k6) but API core is demoable

### Hire-ready increment

1. US1–US4 API complete
2. US5 local UI
3. US6 k6 report
4. T048 Strix
5. T049–T050 deploy on free tiers when ready

### Suggested commit cadence

Commit after each phase checkpoint (not every task) unless asked.

---

## Notes

- Default failure mode: fail-closed; open demo: no auth
- Keep everything local/$0 until T049
- Do not commit `.env` or Redis passwords
