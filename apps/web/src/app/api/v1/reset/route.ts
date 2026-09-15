import { NextResponse } from "next/server";
import { getPolicy, resetSubject } from "@/lib/memory-limiter";

export const runtime = "nodejs";

type Body = {
  policy_id?: string;
  key?: string;
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
  if (!policyId || !key) {
    return NextResponse.json(
      { detail: "policy_id and key required" },
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
  resetSubject(policyId, key);
  return NextResponse.json({ ok: true });
}
