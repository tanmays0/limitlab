

export type Algorithm = "token_bucket" | "sliding_window";

export type Policy = {
  id: string;
  limit: number;
  window_seconds: number;
  algorithm: Algorithm;
  burst?: number | null;
  updated_at?: string | null;
};

export type Decision = {
  allowed: boolean;
  limit: number;
  remaining: number;
  reset: number;
  algorithm: Algorithm;
  retry_after?: number | null;
};

type Bucket = { tokens: number; lastMs: number };

const g = globalThis as typeof globalThis & {
  __limitlabPolicies?: Map<string, Policy>;
  __limitlabBuckets?: Map<string, Bucket>;
  __limitlabWindows?: Map<string, number[]>;
};

function policies(): Map<string, Policy> {
  if (!g.__limitlabPolicies) g.__limitlabPolicies = new Map();
  return g.__limitlabPolicies;
}

function buckets(): Map<string, Bucket> {
  if (!g.__limitlabBuckets) g.__limitlabBuckets = new Map();
  return g.__limitlabBuckets;
}

function windows(): Map<string, number[]> {
  if (!g.__limitlabWindows) g.__limitlabWindows = new Map();
  return g.__limitlabWindows;
}

function bk(policyId: string, subject: string): string {
  return `${policyId}:${subject}`;
}

export function getPolicy(policyId: string): Policy | null {
  return policies().get(policyId) ?? null;
}

export function upsertPolicy(policy: Policy): Policy {
  const updated: Policy = {
    ...policy,
    updated_at: new Date().toISOString(),
  };
  policies().set(updated.id, updated);
  return updated;
}

export function resetSubject(policyId: string, subject: string): void {
  const key = bk(policyId, subject);
  buckets().delete(key);
  windows().delete(key);
}

function refillTokens(
  tokens: number,
  lastMs: number,
  nowMs: number,
  capacity: number,
  rate: number,
): [number, number] {
  const elapsed = Math.max(0, nowMs - lastMs) / 1000;
  const filled = Math.min(capacity, tokens + elapsed * rate);
  return [filled, nowMs];
}

function tryConsume(
  tokens: number,
  capacity: number,
  rate: number,
  cost: number,
  debit: boolean,
): { allowed: boolean; remaining: number; retry: number | null } {
  if (tokens >= cost) {
    return {
      allowed: true,
      remaining: debit ? tokens - cost : tokens,
      retry: null,
    };
  }
  const need = cost - tokens;
  const retry = rate > 0 ? Math.ceil(need / rate) : 1;
  return { allowed: false, remaining: Math.max(0, Math.floor(tokens)), retry };
}

function evalTokenBucket(
  policy: Policy,
  subject: string,
  cost: number,
  consume: boolean,
): Decision {
  const key = bk(policy.id, subject);
  const capacity = policy.burst ?? policy.limit;
  const rate = policy.limit / policy.window_seconds;
  const nowMs = Date.now();
  const existing = buckets().get(key) ?? { tokens: capacity, lastMs: nowMs };
  const [tokens, lastMs] = refillTokens(
    existing.tokens,
    existing.lastMs,
    nowMs,
    capacity,
    rate,
  );
  const { allowed, remaining, retry } = tryConsume(
    tokens,
    capacity,
    rate,
    cost,
    consume,
  );
  if (consume) {
    buckets().set(key, { tokens: remaining, lastMs });
  }
  let fullIn = 0;
  if (remaining < capacity && rate > 0) {
    fullIn = Math.ceil((capacity - remaining) / rate);
  }
  return {
    allowed,
    limit: policy.limit,
    remaining: Math.max(0, Math.floor(remaining)),
    reset: Math.floor(nowMs / 1000) + fullIn,
    algorithm: "token_bucket",
    retry_after: allowed ? null : retry,
  };
}

function evalSlidingWindow(
  policy: Policy,
  subject: string,
  cost: number,
  consume: boolean,
): Decision {
  const key = bk(policy.id, subject);
  const nowMs = Date.now();
  const windowMs = policy.window_seconds * 1000;
  const cutoff = nowMs - windowMs;
  let q = windows().get(key) ?? [];
  q = q.filter((t) => t > cutoff);
  const count = q.length;
  const remainingBefore = Math.max(0, policy.limit - count);
  if (count + cost <= policy.limit) {
    if (consume) {
      for (let i = 0; i < cost; i++) q.push(nowMs);
      windows().set(key, q);
    } else {
      windows().set(key, q);
    }
    return {
      allowed: true,
      limit: policy.limit,
      remaining: Math.max(0, policy.limit - (consume ? q.length : count)),
      reset: Math.floor(nowMs / 1000) + policy.window_seconds,
      algorithm: "sliding_window",
      retry_after: null,
    };
  }
  windows().set(key, q);
  let retryAfter = policy.window_seconds;
  if (q.length) {
    const oldest = q[0];
    retryAfter = Math.max(1, Math.ceil((oldest + windowMs - nowMs) / 1000));
  }
  return {
    allowed: false,
    limit: policy.limit,
    remaining: remainingBefore,
    reset: Math.floor(nowMs / 1000) + policy.window_seconds,
    algorithm: "sliding_window",
    retry_after: retryAfter,
  };
}

export function evaluate(
  policy: Policy,
  subject: string,
  cost: number,
  consume: boolean,
): Decision {
  if (policy.algorithm === "token_bucket") {
    return evalTokenBucket(policy, subject, cost, consume);
  }
  return evalSlidingWindow(policy, subject, cost, consume);
}

export function applyHeaders(
  headers: Headers,
  decision: Decision,
): void {
  headers.set("X-RateLimit-Limit", String(decision.limit));
  headers.set("X-RateLimit-Remaining", String(decision.remaining));
  headers.set("X-RateLimit-Reset", String(decision.reset));
  if (decision.retry_after != null) {
    headers.set("Retry-After", String(decision.retry_after));
  }
}
