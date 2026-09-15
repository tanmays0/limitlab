# Feature Specification: Rate Limiter Platform

**Feature Branch**: `001-rate-limiter-platform`

**Created**: 2026-09-15

**Status**: Clarified

**Input**: User description: "LimitLab — high-performance rate-limiting service (~10k RPS) with token bucket + sliding window, Redis-backed counters, standard rate-limit headers, load-test proof, and a deployed demo dashboard for policies, bursts, remaining quota, and latency."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Enforce a Limit on Consume (Priority: P1)

An API consumer asks LimitLab whether a request for a given key (API key, IP, or user id) may proceed, and LimitLab either allows the request (consuming quota) or denies it with clear remaining/reset signals.

**Why this priority**: Without correct allow/deny on consume, there is no product. This is the hire-proof core and interview demo centerpiece.

**Independent Test**: Configure a policy of N requests per window for a key, fire N+1 consumes, verify the first N succeed and the last is denied with remaining never negative.

**Acceptance Scenarios**:

1. **Given** a policy of 10 requests per 10 seconds for key `user:42`, **When** 10 consume requests arrive within the window, **Then** all 10 are allowed and remaining decreases to 0.
2. **Given** remaining is 0 for that key, **When** another consume arrives before reset, **Then** the request is denied, the client receives a retry-after signal, and remaining stays 0 (never negative).
3. **Given** a consume of N tokens (N > 1), **When** remaining is less than N, **Then** the request is denied without partial consumption.

---

### User Story 2 - Check Without Consuming (Priority: P1)

An API consumer peeks whether a request would be allowed for a key without spending quota—useful for dry-runs and UI previews.

**Why this priority**: Check is paired with consume in the core contract and enables safe demo/preview behavior.

**Independent Test**: With remaining = 1, call check then check again; both report allowed and remaining unchanged; then consume once and verify remaining becomes 0.

**Acceptance Scenarios**:

1. **Given** remaining quota is 5, **When** a check is performed, **Then** the response indicates allow and remaining stays 5.
2. **Given** remaining quota is 0, **When** a check is performed, **Then** the response indicates deny without changing stored state.

---

### User Story 3 - Configure Policies (Priority: P2)

An operator (or demo visitor) creates or updates a named policy: limit, window, and algorithm (token bucket or sliding window), then fetches it back.

**Why this priority**: Policies make algorithms selectable and enable the live demo to switch behaviors without redeploying.

**Independent Test**: Upsert policy `demo` as token bucket 10/10s, fetch it, change to sliding window, fetch again and confirm fields.

**Acceptance Scenarios**:

1. **Given** no policy `demo` exists, **When** it is upserted with limit 10, window 10s, algorithm token bucket, **Then** a subsequent fetch returns those exact settings.
2. **Given** policy `demo` exists as token bucket, **When** it is updated to sliding window, **Then** new consumes for keys under that policy use sliding-window semantics.
3. **Given** an invalid policy (limit ≤ 0 or unknown algorithm), **When** upsert is attempted, **Then** the system rejects the change with a clear error and leaves prior config unchanged.

---

### User Story 4 - Reset a Key’s Quota (Priority: P2)

An operator resets the remaining quota for a specific key under a policy so demos and tests can restart cleanly.

**Why this priority**: Reset is required for repeatable demos and load-test setup; secondary to consume/check.

**Independent Test**: Exhaust a key, reset it, consume once and verify allow with full remaining restored per policy.

**Acceptance Scenarios**:

1. **Given** a key is exhausted (remaining 0), **When** reset is invoked for that key and policy, **Then** the next consume is allowed as if the key were fresh.
2. **Given** a key has never been seen, **When** reset is invoked, **Then** the operation succeeds idempotently (no error required for empty state).

---

### User Story 5 - Live Demo Dashboard (Priority: P2)

A recruiter or interviewer opens a public web dashboard, configures a policy, fires a burst of requests, and watches allow/deny, remaining quota, and latency update live.

**Why this priority**: Portfolio rule: no public demo UI means the project is not done, even if the API is solid.

**Independent Test**: On the deployed URL alone (no local setup), create a tight policy, send 50–100 requests, observe allows then denies, remaining, and a latency chart.

**Acceptance Scenarios**:

1. **Given** the public demo URL, **When** a visitor sets a policy (e.g. 10 req / 10s) and clicks send burst, **Then** they see a stream of allow/deny outcomes and remaining quota updating.
2. **Given** the dashboard, **When** the visitor switches algorithm between token bucket and sliding window and re-runs a burst, **Then** behavior differences are visible without leaving the page.
3. **Given** the dashboard during a burst, **When** responses return, **Then** a small latency chart updates with recent timings.

---

### User Story 6 - Prove Throughput & Health (Priority: P3)

An engineer (or interviewer) reviews committed load-test evidence showing ~10k decisions/sec (or an honest maximum with bottlenecks), and can hit health/metrics endpoints on a running instance.

**Why this priority**: Proof and ops close the hire narrative; they depend on a working limiter first.

**Independent Test**: Open the committed load-test report in-repo; hit health on a running instance and confirm liveness; inspect metrics for request/latency counters after traffic.

**Acceptance Scenarios**:

1. **Given** the repository, **When** someone opens the published load-test report, **Then** they see method, hardware notes, achieved RPS, and any bottlenecks.
2. **Given** a running service, **When** health is requested, **Then** liveness is reported successfully if the process is up.
3. **Given** recent traffic, **When** metrics are requested, **Then** counters or latency summaries reflecting that traffic are available.

---

### Edge Cases

- Burst exactly at the limit boundary (Nth allowed, N+1th denied).
- Concurrent consumes for the same key must not over-admit beyond the limit.
- Multi-token consume larger than remaining → deny, no partial debit.
- Window/reset boundary: first request after reset time is allowed with refreshed remaining.
- Unknown policy id on consume/check → clear client error (not a silent default that masks misconfiguration).
- Store unavailable → behavior follows the documented failure mode (see clarification).
- Remaining reported to clients never negative; deny responses still include limit/remaining/reset signals.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept consume requests that debit 1 or N tokens for a key under a named policy and return allow or deny.
- **FR-002**: System MUST accept check requests that report allow or deny for a key under a policy without changing stored quota.
- **FR-003**: System MUST support resetting quota state for a key under a policy.
- **FR-004**: System MUST allow creating and updating policies with at least: identifier, limit, window duration, and algorithm (`token_bucket` or `sliding_window`).
- **FR-005**: System MUST fetch a policy by identifier and return its current configuration.
- **FR-006**: Both token bucket and sliding window MUST be available and selectable per policy in v1.
- **FR-007**: On deny of a consume, the system MUST signal that the client should wait (retry-after) and MUST expose limit, remaining, and reset information comparable to common rate-limit response conventions.
- **FR-008**: On allow of a consume (and on check), the system MUST expose limit, remaining, and reset information to the client.
- **FR-009**: Remaining quota MUST never be reported or stored as a negative value.
- **FR-010**: Concurrent decisions for the same key MUST not admit more traffic than the policy limit allows.
- **FR-011**: When the backing counter store is unavailable, the system MUST apply an explicit failure mode selected by configuration. The v1 default MUST be **fail-closed** (deny / refuse new admits when the store is down). Fail-open MUST remain available as an opt-in for operators who accept over-admit risk during outages. The active mode and rationale MUST be documented for demos and interviews.
- **FR-012**: System MUST expose a liveness/health check suitable for deploy platforms.
- **FR-013**: System MUST expose basic operational metrics (request volume and latency summaries at minimum).
- **FR-014**: A public web demo MUST let visitors configure a policy, send a burst of requests, and see allow/deny stream, remaining quota, and latency visualization.
- **FR-015**: Repository MUST include reproducible load-test scripts and a committed report documenting achieved throughput (~10k decisions/sec target) including method and hardware notes; if below target, report MUST state honest max and bottlenecks.
- **FR-016**: Demo and API MUST be reachable via public URLs; secrets MUST NOT be stored in the repository.
- **FR-017**: Local development MUST be runnable with a single compose-style bring-up of the service plus its counter store.
- **FR-018**: The public demo MUST allow anonymous visitors to upsert demo policies and fire bursts without signing in or pasting a credential (zero-friction recruiter path). Abuse hardening beyond basic rate limits on the demo itself is out of scope for v1; the README MAY note that shared demo state can be overwritten by other visitors.

### Key Entities

- **Policy**: Named rate-limit configuration (limit count, window duration, algorithm).
- **Subject Key**: The identity being limited (e.g. API key, IP, user id string).
- **Quota State**: Current remaining capacity and reset timing for a subject under a policy.
- **Decision**: Allow or deny outcome for a check or consume, including signaled headers/fields.
- **Load Test Report**: Published evidence of sustained decision throughput and test conditions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Under a policy of N requests per window, the first N consumes for a fresh key succeed and the (N+1)th is denied with remaining at 0.
- **SC-002**: Check never reduces remaining; after a successful peek with remaining ≥ 1, a following consume still succeeds when no other traffic intervenes.
- **SC-003**: Switching a policy between token bucket and sliding window changes observable burst behavior in the demo within one page session.
- **SC-004**: Documented load test shows approximately 10,000 rate-limit decisions per second, or an honest lower maximum with named bottlenecks and hardware notes.
- **SC-005**: A first-time visitor completes “set policy → send burst → see allow then deny” on the public demo in under 2 minutes without reading source code.
- **SC-006**: Concurrent burst tests for one key never show more allows than the configured limit.
- **SC-007**: Health check on the deployed API succeeds while the service is running; metrics reflect traffic after a demo burst.
- **SC-008**: After ship, a security/dependency scan is run and critical secret or dependency findings are addressed or explicitly accepted.

## Assumptions

- Primary actors are API integrators (programmatic clients) and portfolio visitors (demo dashboard); no multi-tenant SaaS billing or account system in v1.
- Subject keys are opaque strings supplied by the client (API key / IP / user id); LimitLab does not invent identity.
- Window durations are on the order of seconds to minutes (not months); demo defaults around 10 requests / 10 seconds.
- Multi-region edge mesh, paid billing, full API gateway, Kubernetes autoscaling deep-dives, and mobile apps are out of scope for v1.
- A centralized counter store (project standard: Redis) is available in local compose and in deployment.
- Portfolio audience values a clickable demo URL and a published throughput report over enterprise auth complexity.
- Stack preference from project governance: Python service API + separate web dashboard, unless later amended.
- Build and local verification are intended to be $0 (Docker Compose + free tooling). Paid cloud spend is deferred until after the product works locally; free-tier hosts are preferred at deploy time.
- Default store failure mode is fail-closed; fail-open is documented and configurable for interview tradeoff discussion.
- Public demo is intentionally open (no login) to maximize recruiter conversion on a resume link.
