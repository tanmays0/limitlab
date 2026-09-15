import { NextResponse } from "next/server";
import {
  getPolicy,
  upsertPolicy,
  type Algorithm,
  type Policy,
} from "@/lib/memory-limiter";

export const runtime = "nodejs";

type Body = {
  limit?: number;
  window_seconds?: number;
  algorithm?: Algorithm;
  burst?: number | null;
};

export async function GET(
  _req: Request,
  ctx: { params: Promise<{ policy_id: string }> },
) {
  const { policy_id } = await ctx.params;
  const policy = getPolicy(policy_id);
  if (!policy) {
    return NextResponse.json(
      { detail: `policy not found: ${policy_id}` },
      { status: 404 },
    );
  }
  return NextResponse.json(policy);
}

export async function PUT(
  req: Request,
  ctx: { params: Promise<{ policy_id: string }> },
) {
  const { policy_id } = await ctx.params;
  let body: Body;
  try {
    body = (await req.json()) as Body;
  } catch {
    return NextResponse.json({ detail: "invalid JSON" }, { status: 400 });
  }
  if (
    !body.limit ||
    body.limit < 1 ||
    !body.window_seconds ||
    body.window_seconds < 1 ||
    (body.algorithm !== "token_bucket" &&
      body.algorithm !== "sliding_window")
  ) {
    return NextResponse.json(
      { detail: "limit, window_seconds, and algorithm required" },
      { status: 422 },
    );
  }
  if (body.algorithm === "token_bucket" && body.burst != null && body.burst < 1) {
    return NextResponse.json({ detail: "burst must be >= 1" }, { status: 422 });
  }
  const policy: Policy = {
    id: policy_id,
    limit: body.limit,
    window_seconds: body.window_seconds,
    algorithm: body.algorithm,
    burst: body.burst ?? null,
  };
  return NextResponse.json(upsertPolicy(policy));
}
