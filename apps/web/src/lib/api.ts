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

export type RequestResult = {
  index: number;
  allowed: boolean;
  remaining: number;
  status: number;
  latencyMs: number;
  error?: string;
};

const raw = process.env.NEXT_PUBLIC_API_URL?.trim();
const API_URL = raw ? raw.replace(/\/$/, "") : "/api";

export function usesEmbeddedApi(): boolean {
  return API_URL === "/api" || API_URL.endsWith("/api");
}

async function parseJson<T>(res: Response): Promise<T> {
  const text = await res.text();
  try {
    return JSON.parse(text) as T;
  } catch {
    throw new Error(text || `HTTP ${res.status}`);
  }
}

export async function upsertPolicy(
  id: string,
  body: {
    limit: number;
    window_seconds: number;
    algorithm: Algorithm;
    burst?: number | null;
  },
): Promise<Policy> {
  const res = await fetch(`${API_URL}/v1/policies/${encodeURIComponent(id)}`, {
    method: "PUT",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const err = await parseJson<{ detail?: string }>(res).catch(
      (): { detail?: string } => ({}),
    );
    throw new Error(err.detail || `Policy save failed (${res.status})`);
  }
  return parseJson<Policy>(res);
}

export async function getPolicy(id: string): Promise<Policy> {
  const res = await fetch(`${API_URL}/v1/policies/${encodeURIComponent(id)}`);
  if (!res.ok) {
    throw new Error(`Policy not found (${res.status})`);
  }
  return parseJson<Policy>(res);
}

export async function resetKey(policyId: string, key: string): Promise<void> {
  const res = await fetch(`${API_URL}/v1/reset`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ policy_id: policyId, key }),
  });
  if (!res.ok) {
    throw new Error(`Reset failed (${res.status})`);
  }
}

export async function consumeOnce(
  policyId: string,
  key: string,
  index: number,
): Promise<RequestResult> {
  const started = performance.now();
  try {
    const res = await fetch(`${API_URL}/v1/consume`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ policy_id: policyId, key, cost: 1 }),
    });
    const latencyMs = Math.round(performance.now() - started);
    const body = await parseJson<Decision & { detail?: string }>(res);
    if (body.detail && body.allowed === undefined) {
      return {
        index,
        allowed: false,
        remaining: 0,
        status: res.status,
        latencyMs,
        error: body.detail,
      };
    }
    return {
      index,
      allowed: Boolean(body.allowed),
      remaining: body.remaining ?? 0,
      status: res.status,
      latencyMs,
    };
  } catch (e) {
    return {
      index,
      allowed: false,
      remaining: 0,
      status: 0,
      latencyMs: Math.round(performance.now() - started),
      error: e instanceof Error ? e.message : "request failed",
    };
  }
}

export function apiBaseUrl(): string {
  return API_URL;
}

export async function consumeBurst(
  policyId: string,
  key: string,
  count: number,
  policy: {
    limit: number;
    window_seconds: number;
    algorithm: Algorithm;
    burst?: number | null;
  },
  reset = true,
): Promise<RequestResult[]> {
  const res = await fetch(`${API_URL}/v1/burst`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({
      policy_id: policyId,
      key,
      count,
      reset,
      policy,
    }),
  });
  if (!res.ok) {
    const err = await parseJson<{ detail?: string }>(res).catch(
      (): { detail?: string } => ({}),
    );
    throw new Error(err.detail || `Burst failed (${res.status})`);
  }
  const body = await parseJson<{ results: RequestResult[] }>(res);
  return body.results;
}
