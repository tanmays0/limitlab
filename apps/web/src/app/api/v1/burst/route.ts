import { NextResponse } from "next/server";
import {
  evaluate,
  resetSubject,
  upsertPolicy,
  type Algorithm,
  type Policy,
} from "@/lib/memory-limiter";

export const runtime = "nodejs";

type Body = {
  policy_id?: string;
  key?: string;
  count?: number;
  reset?: boolean;
  policy?: {
    limit?: number;
    window_seconds?: number;
    algorithm?: Algorithm;
    burst?: number | null;
  };
};

export async function POST(req: Request) {
  let body: Body;
  try {
    body = (await req.json()) as Body;
  } catch {
    return NextResponse.json({ detail: "invalid JSON" }, { status: 400 });
  }
  const policyId = body.policy_id?.trim();
  const key = body.key?.trim();
  const count = Math.min(Math.max(body.count ?? 1, 1), 200);
  if (!policyId || !key) {
    return NextResponse.json(
      { detail: "policy_id and key required" },
      { status: 422 },
    );
  }
  const p = body.policy;
  if (
    !p?.limit ||
    p.limit < 1 ||
    !p.window_seconds ||
    p.window_seconds < 1 ||
    (p.algorithm !== "token_bucket" && p.algorithm !== "sliding_window")
  ) {
    return NextResponse.json(
      { detail: "policy {limit,window_seconds,algorithm} required" },
      { status: 422 },
    );
  }
  const policy: Policy = upsertPolicy({
    id: policyId,
    limit: p.limit,
    window_seconds: p.window_seconds,
    algorithm: p.algorithm,
    burst: p.burst ?? null,
  });
  if (body.reset) {
    resetSubject(policyId, key);
  }
  const results = [];
  for (let i = 0; i < count; i++) {
    const started = performance.now();
    const decision = evaluate(policy, key, 1, true);
    results.push({
      index: i + 1,
      allowed: decision.allowed,
      remaining: decision.remaining,
      status: decision.allowed ? 200 : 429,
      latencyMs: Math.round(performance.now() - started),
    });
  }
  return NextResponse.json({ results, store: "memory", policy });
}
