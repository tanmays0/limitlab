-- Atomic token bucket: refill, then optionally consume.
-- KEYS[1] = bucket hash key
-- ARGV[1] = capacity (burst)
-- ARGV[2] = refill_rate tokens/sec (limit / window_seconds)
-- ARGV[3] = now_ms
-- ARGV[4] = cost
-- ARGV[5] = mode: 1 = consume, 0 = check
-- Returns: {allowed (0|1), remaining, reset_unix, retry_after_sec}

local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local do_consume = tonumber(ARGV[5])

if capacity < 1 or rate <= 0 or cost < 1 then
  return {0, 0, math.floor(now_ms / 1000), 1}
end

local data = redis.call('HMGET', key, 'tokens', 'ts')
local tokens = tonumber(data[1])
local last_ms = tonumber(data[2])

if tokens == nil then
  tokens = capacity
  last_ms = now_ms
end

local elapsed = math.max(0, now_ms - last_ms) / 1000.0
tokens = math.min(capacity, tokens + elapsed * rate)
last_ms = now_ms

local allowed = 0
local retry_after = 0

if tokens >= cost then
  allowed = 1
  if do_consume == 1 then
    tokens = tokens - cost
  end
else
  local need = cost - tokens
  retry_after = math.max(1, math.ceil(need / rate))
end

-- remaining never negative
if tokens < 0 then
  tokens = 0
end

local full_in = 0
if tokens < capacity then
  full_in = math.ceil((capacity - tokens) / rate)
end
local reset_unix = math.floor(now_ms / 1000) + full_in

if do_consume == 1 then
  redis.call('HSET', key, 'tokens', tokens, 'ts', last_ms)
  -- TTL: enough to refill to full plus window slack
  local ttl = math.max(full_in + 1, math.ceil(capacity / rate) + 1)
  redis.call('EXPIRE', key, ttl)
end

local remaining = math.floor(tokens)
-- for check with fractional tokens, report floor; never negative
if remaining < 0 then remaining = 0 end

return {allowed, remaining, reset_unix, retry_after}
