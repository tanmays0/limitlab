# Data Model: Rate Limiter Platform

## Entities

### Policy

| Field | Type | Rules |
|-------|------|-------|
| `id` | string | 1–64 chars; `[a-zA-Z0-9:_-]+` |
| `limit` | int | ≥ 1 |
| `window_seconds` | int | ≥ 1 |
| `algorithm` | enum | `token_bucket` \| `sliding_window` |
| `burst` | int \| null | Optional; token bucket only; default = `limit` |
| `updated_at` | datetime | Set on upsert |

**Storage key**: `policy:{id}` (Redis hash or JSON string).

**Validation**: Reject unknown algorithm; reject `limit`/`window_seconds` ≤ 0;
ignore `burst` for sliding window (or require null).

### Subject Key

Opaque string supplied by client (`key` field), e.g. `user:42`, `ip:1.2.3.4`,
`apk_xxx`. Not an entity table — part of quota addressing.

### Quota State (derived / stored)

Addressed by `(policy_id, key)`.

| Algorithm | Stored shape (conceptual) |
|-----------|---------------------------|
| Token bucket | tokens remaining, last refill timestamp |
| Sliding window | timestamps (or weighted counts) of admits in window |

**Invariants**:
- Remaining reported to clients ≥ 0
- Concurrent updates atomic (Lua)
- Reset deletes or zeroes state for `(policy_id, key)`

### Decision

Not persisted; response DTO:

| Field | Meaning |
|-------|---------|
| `allowed` | bool |
| `limit` | policy limit |
| `remaining` | after this decision (check: unchanged) |
| `reset` | unix seconds when window fully refreshes / next token |
| `retry_after` | seconds (deny only; else omitted) |
| `algorithm` | echo of policy algorithm |

### Metrics Snapshot

In-process counters (optionally scraped):

- `requests_total{route,outcome}`
- `request_latency_seconds` histogram or summary
- `redis_errors_total`

## State transitions

```text
[unknown key] --consume(allow)--> [partial/full quota]
[quota > 0]   --consume(allow)--> [quota decreased]
[quota = 0]   --consume----------> [deny, unchanged]
[any]         --check------------> [unchanged]
[any]         --reset------------> [fresh / empty state]
[store down]  --* (fail_closed)--> [deny / 503 per route policy]
[store down]  --* (fail_open)---> [allow without debit]
```

## Relationships

```text
Policy 1 --- * Quota State (via subject keys)
Decision * --- 1 Policy (evaluated against)
```
