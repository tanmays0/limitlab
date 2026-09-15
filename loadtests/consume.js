import http from "k6/http";
import { check } from "k6";

const BASE_URL = __ENV.BASE_URL || "http://127.0.0.1:8080";
const POLICY_ID = __ENV.POLICY_ID || "k6-bench";
const KEY_PREFIX = __ENV.KEY_PREFIX || "bench";

export const options = {
  scenarios: {
    consume_burst: {
      executor: "constant-vus",
      vus: Number(__ENV.VUS || 50),
      duration: __ENV.DURATION || "20s",
      gracefulStop: "5s",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<100"],
  },
};

export function setup() {
  const res = http.put(
    `${BASE_URL}/v1/policies/${POLICY_ID}`,
    JSON.stringify({
      limit: 1000000,
      window_seconds: 60,
      algorithm: "token_bucket",
      burst: 1000000,
    }),
    { headers: { "content-type": "application/json" } },
  );
  check(res, { "policy upsert 200": (r) => r.status === 200 });
  return { base: BASE_URL, policy: POLICY_ID };
}

export default function (data) {
  const key = `${KEY_PREFIX}-${__VU}-${__ITER}`;
  const res = http.post(
    `${data.base}/v1/consume`,
    JSON.stringify({
      policy_id: data.policy,
      key,
      cost: 1,
    }),
    {
      headers: { "content-type": "application/json" },
      tags: { name: "consume" },
    },
  );
  check(res, {
    "consume 200": (r) => r.status === 200,
  });
}

export function handleSummary(data) {
  const reqs = data.metrics.http_reqs;
  const dur = data.metrics.http_req_duration;
  const failed = data.metrics.http_req_failed;
  const summary = {
    generated_at: new Date().toISOString(),
    base_url: BASE_URL,
    policy_id: POLICY_ID,
    note: "Unique keys per VU/iter; high limit so RPS measures admit path.",
    metrics: {
      http_reqs: reqs ? reqs.values : null,
      http_req_duration: dur ? dur.values : null,
      http_req_failed: failed ? failed.values : null,
      iterations: data.metrics.iterations
        ? data.metrics.iterations.values
        : null,
      vus_max: data.metrics.vus_max ? data.metrics.vus_max.values : null,
    },
  };
  const rate = (reqs && reqs.values && reqs.values.rate) || 0;
  const p95 = (dur && dur.values && dur.values["p(95)"]) || 0;
  const text = [
    "",
    "=== LimitLab k6 summary ===",
    `RPS (http_reqs.rate): ${rate.toFixed(1)}`,
    `p95 latency ms: ${p95.toFixed(2)}`,
    "JSON: loadtests/reports/k6-summary.json",
    "",
  ].join("\n");
  return {
    "loadtests/reports/k6-summary.json": JSON.stringify(summary, null, 2),
    stdout: text,
  };
}
