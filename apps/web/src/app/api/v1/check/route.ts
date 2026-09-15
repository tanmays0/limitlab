import { NextResponse } from "next/server";
import { applyHeaders, evaluate, getPolicy } from "@/lib/memory-limiter";

export const runtime = "nodejs";

type Body = {
  policy_id?: string;
  key?: string;
  cost?: number;
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
  const cost = body.cost ?? 1;
  if (!policyId || !key || cost < 1) {
    return NextResponse.json(
      { detail: "policy_id, key, and cost>=1 required" },
      { status: 422 },
    );
  }
  const policy = getPolicy(policyId);
  if (!policy) {
    return NextResponse.json(
      { detail: `policy not found: ${policyId}` },
      { status: 404 },
    );
  }
  const decision = evaluate(policy, key, cost, false);
  const headers = new Headers();
  applyHeaders(headers, decision);
  return NextResponse.json(decision, { status: 200, headers });
}
