-- Sliding window via sorted set of admit timestamps (ms).
-- KEYS[1] = window zset key
-- ARGV[1] = limit
-- ARGV[2] = window_seconds
-- ARGV[3] = now_ms
-- ARGV[4] = cost
-- ARGV[5] = mode: 1 = consume, 0 = check
-- Returns: {allowed (0|1), remaining, reset_unix, retry_after_sec}

local key = KEYS[1]
local limit = tonumber(ARGV[1])
local window_sec = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])
local cost = tonumber(ARGV[4])
local do_consume = tonumber(ARGV[5])

if limit < 1 or window_sec < 1 or cost < 1 then
  return {0, 0, math.floor(now_ms / 1000), 1}
end

local window_ms = window_sec * 1000
local cutoff = now_ms - window_ms

redis.call('ZREMRANGEBYSCORE', key, 0, cutoff)
local count = redis.call('ZCARD', key)
local remaining_before = limit - count
if remaining_before < 0 then remaining_before = 0 end

local allowed = 0
local retry_after = 0
local remaining = remaining_before

if count + cost <= limit then
  allowed = 1
  if do_consume == 1 then
    for i = 1, cost do
      -- unique member: now_ms + i + random-ish counter via i
      redis.call('ZADD', key, now_ms, tostring(now_ms) .. ':' .. tostring(i) .. ':' .. tostring(math.random(1, 1000000)))
    end
    remaining = limit - (count + cost)
  else
    remaining = remaining_before
  end
else
  -- time until oldest event exits the window enough to free `cost` slots
  local need = (count + cost) - limit
  local oldest = redis.call('ZRANGE', key, 0, need - 1, 'WITHSCORES')
  if oldest ~= nil and #oldest >= 2 then
    local idx = (#oldest >= need * 2) and (need * 2) or 2
    local score = tonumber(oldest[idx])
    retry_after = math.max(1, math.ceil((score + window_ms - now_ms) / 1000.0))
  else
    retry_after = window_sec
  end
  remaining = remaining_before
end

if remaining < 0 then remaining = 0 end

local reset_unix = math.floor(now_ms / 1000) + window_sec
if do_consume == 1 then
  redis.call('EXPIRE', key, window_sec + 1)
end

return {allowed, remaining, reset_unix, retry_after}
