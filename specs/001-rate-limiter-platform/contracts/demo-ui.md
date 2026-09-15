# UI Contract: Demo Dashboard

Public page (e.g. `/`) with no login.

## Required controls

1. **Policy form**: `id`, `limit`, `window_seconds`, algorithm select
   (`token_bucket` | `sliding_window`), optional burst; Save → `PUT /v1/policies/{id}`
2. **Subject key** input (default e.g. `demo-user`)
3. **Send N requests** (default 50 or 100) → sequential or limited-parallel
   `POST /v1/consume`
4. **Reset key** button → `POST /v1/reset`

## Required feedback

1. Live stream/list of allow (green) / deny (red) with latency ms
2. Current **remaining** / **limit** readout
3. Small **latency chart** (last N samples)
4. Display active algorithm

## Non-goals

- Auth, billing, multi-user accounts
- Editing Redis directly
- Mobile-native app
