# API Contract: LimitLab v1

Base URL (local): `http://localhost:8080`

Content-Type: `application/json`

CORS: allow demo origin(s); local `*` acceptable for v1 demo.

## Headers (on check/consume responses)

| Header | When |
|--------|------|
| `X-RateLimit-Limit` | always |
| `X-RateLimit-Remaining` | always (≥ 0) |
| `X-RateLimit-Reset` | always (unix seconds) |
| `Retry-After` | on HTTP 429 |

## Endpoints

### `POST /v1/check`

Dry-run; does not debit.

**Request**

```json
{
  "policy_id": "demo",
  "key": "user:42",
  "cost": 1
}
```

**Response 200**

```json
{
  "allowed": true,
  "limit": 10,
  "remaining": 10,
  "reset": 1726400000,
  "algorithm": "token_bucket"
}
```

### `POST /v1/consume`

Debit `cost` (default 1).

**Request**: same as check.

**Response 200**: same shape; `remaining` after debit.

**Response 429**: `allowed: false`; include `retry_after`; headers as above.

### `POST /v1/reset`

**Request**

```json
{
  "policy_id": "demo",
  "key": "user:42"
}
```

**Response 200**

```json
{ "ok": true }
```

### `GET /v1/policies/{id}`

**Response 200**: Policy object.

**Response 404**: unknown policy.

### `PUT /v1/policies/{id}`

**Request**

```json
{
  "limit": 10,
  "window_seconds": 10,
  "algorithm": "token_bucket",
  "burst": 10
}
```

**Response 200**: stored Policy.

**Response 422**: validation error.

### `GET /health`

**Response 200**

```json
{ "status": "ok" }
```

Optional: include Redis ping when fail-closed cares about readiness — keep
liveness process-up; document readiness separately if needed.

### `GET /metrics`

Prometheus text exposition (and/or `?format=json` for demo).

## Error shape

```json
{
  "detail": "human readable message"
}
```

Unknown policy on check/consume → **400** or **404** with clear detail (prefer
404 for missing policy).
