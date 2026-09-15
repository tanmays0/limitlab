"use client";

import { useCallback, useMemo, useState, useTransition } from "react";
import {
  apiBaseUrl,
  consumeBurst,
  consumeOnce,
  resetKey,
  upsertPolicy,
  usesEmbeddedApi,
  type Algorithm,
  type Policy,
  type RequestResult,
} from "@/lib/api";
import { LatencyChart } from "./LatencyChart";

type BurstMode = "sequential" | "parallel";

const DEFAULT_POLICY = {
  id: "demo",
  limit: 10,
  window_seconds: 10,
  algorithm: "token_bucket" as Algorithm,
  burst: 10,
};

async function runBurst(
  count: number,
  mode: BurstMode,
  concurrency: number,
  policyId: string,
  key: string,
  policy: {
    limit: number;
    window_seconds: number;
    algorithm: Algorithm;
    burst?: number | null;
  },
  onEach: (r: RequestResult) => void,
): Promise<void> {
  if (usesEmbeddedApi()) {
    const results = await consumeBurst(policyId, key, count, policy, true);
    for (const r of results) onEach(r);
    return;
  }

  if (mode === "sequential") {
    for (let i = 0; i < count; i++) {
      const r = await consumeOnce(policyId, key, i + 1);
      onEach(r);
    }
    return;
  }

  let next = 0;
  const workers = Array.from(
    { length: Math.min(concurrency, count) },
    async () => {
      while (true) {
        const i = next++;
        if (i >= count) return;
        const r = await consumeOnce(policyId, key, i + 1);
        onEach(r);
      }
    },
  );
  await Promise.all(workers);
}

export function Dashboard() {
  const [policyId, setPolicyId] = useState(DEFAULT_POLICY.id);
  const [limit, setLimit] = useState(DEFAULT_POLICY.limit);
  const [windowSeconds, setWindowSeconds] = useState(
    DEFAULT_POLICY.window_seconds,
  );
  const [algorithm, setAlgorithm] = useState<Algorithm>(
    DEFAULT_POLICY.algorithm,
  );
  const [burst, setBurst] = useState(DEFAULT_POLICY.burst);
  const [subjectKey, setSubjectKey] = useState("demo-user");
  const [requestCount, setRequestCount] = useState(50);
  const [mode, setMode] = useState<BurstMode>("sequential");
  const [concurrency, setConcurrency] = useState(5);
  const [activePolicy, setActivePolicy] = useState<Policy | null>(null);
  const [remaining, setRemaining] = useState<number | null>(null);
  const [results, setResults] = useState<RequestResult[]>([]);
  const [status, setStatus] = useState<string>("Save a policy, then fire a burst.");
  const [error, setError] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [, startTransition] = useTransition();

  const allowedCount = useMemo(
    () => results.filter((r) => r.allowed).length,
    [results],
  );
  const deniedCount = useMemo(
    () => results.filter((r) => !r.allowed).length,
    [results],
  );
  const avgLatency = useMemo(() => {
    if (results.length === 0) return null;
    const sum = results.reduce((a, r) => a + r.latencyMs, 0);
    return Math.round(sum / results.length);
  }, [results]);

  const onSavePolicy = useCallback(async () => {
    setError(null);
    try {
      const saved = await upsertPolicy(policyId, {
        limit,
        window_seconds: windowSeconds,
        algorithm,
        burst: algorithm === "token_bucket" ? burst : null,
      });
      setActivePolicy(saved);
      setRemaining(saved.limit);
      setStatus(
        `Policy “${saved.id}” saved · ${saved.limit} / ${saved.window_seconds}
s · ${saved.algorithm}`,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save policy");
    }
  }, [algorithm, burst, limit, policyId, windowSeconds]);

  const onReset = useCallback(async () => {
    setError(null);
    try {
      await resetKey(policyId, subjectKey);
      setRemaining(limit);
      setResults([]);
      setStatus(`Reset key “${subjectKey}” under policy “${policyId}”.`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Reset failed");
    }
  }, [limit, policyId, subjectKey]);

  const onBurst = useCallback(async () => {
    setError(null);
    setRunning(true);
    setResults([]);
    setStatus(
      mode === "sequential"
        ? `Sending ${requestCount} requests sequentially…`
        : `Sending ${requestCount} requests (concurrency ${concurrency})…`,
    );
    const policyBody = {
      limit,
      window_seconds: windowSeconds,
      algorithm,
      burst: algorithm === "token_bucket" ? burst : null,
    };
    try {
      if (!usesEmbeddedApi()) {
        const p = await upsertPolicy(policyId, policyBody);
        setActivePolicy(p);
      } else {
        setActivePolicy({ id: policyId, ...policyBody });
      }

      await runBurst(
        requestCount,
        mode,
        concurrency,
        policyId,
        subjectKey,
        policyBody,
        (r) => {
          startTransition(() => {
            setResults((prev) => [...prev, r].sort((a, b) => a.index - b.index));
            setRemaining(r.remaining);
          });
        },
      );
      setStatus("Burst complete.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Burst failed");
    } finally {
      setRunning(false);
    }
  }, [
    algorithm,
    burst,
    concurrency,
    limit,
    mode,
    policyId,
    requestCount,
    subjectKey,
    windowSeconds,
  ]);

  const displayAlgo = activePolicy?.algorithm ?? algorithm;
  const displayLimit = activePolicy?.limit ?? limit;

  return (
    <div className="shell">
      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Live demo · rate-limit API</p>
          <h1 className="brand">LimitLab</h1>
          <p className="tagline">
            Watch token bucket and sliding window rate limits admit, deny, and
            recover — with live remaining quota and latency.
          </p>
          <p className="api-chip">
            API <code>{apiBaseUrl()}</code>
          </p>
        </div>
        <aside className="policy-spotlight" aria-live="polite">
          <span className="spotlight-label">Active policy</span>
          <strong className="spotlight-id">{policyId}</strong>
          <div className="spotlight-meta">
            <span>{displayAlgo.replace("_", " ")}</span>
            <span>
              {displayLimit} / {windowSeconds}
s
            </span>
          </div>
          <div className="quota">
            <span className="quota-label">Remaining</span>
            <span className="quota-value">
              {remaining === null ? "—" : remaining}
              <small>/{displayLimit}</small>
            </span>
          </div>
        </aside>
      </header>

      <main className="grid">
        <section className="panel">
          <h2>1 · Policy</h2>
          <div className="form-grid">
            <label>
              Policy ID
              <input
                value={policyId}
                onChange={(e) => setPolicyId(e.target.value)}
                disabled={running}
              />
            </label>
            <label>
              Subject key
              <input
                value={subjectKey}
                onChange={(e) => setSubjectKey(e.target.value)}
                disabled={running}
              />
            </label>
            <label>
              Limit
              <input
                type="number"
                min={1}
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                disabled={running}
              />
            </label>
            <label>
              Window (seconds)
              <input
                type="number"
                min={1}
                value={windowSeconds}
                onChange={(e) => setWindowSeconds(Number(e.target.value))}
                disabled={running}
              />
            </label>
            <label>
              Algorithm
              <select
                value={algorithm}
                onChange={(e) => setAlgorithm(e.target.value as Algorithm)}
                disabled={running}
              >
                <option value="token_bucket">token bucket</option>
                <option value="sliding_window">sliding window</option>
              </select>
            </label>
            {algorithm === "token_bucket" ? (
              <label>
                Burst capacity
                <input
                  type="number"
                  min={1}
                  value={burst}
                  onChange={(e) => setBurst(Number(e.target.value))}
                  disabled={running}
                />
              </label>
            ) : (
              <div className="hint">Sliding window has no separate burst.</div>
            )}
          </div>
          <div className="actions">
            <button type="button" className="btn primary" onClick={onSavePolicy} disabled={running}>
              Save policy
            </button>
            <button type="button" className="btn ghost" onClick={onReset} disabled={running}>
              Reset key
            </button>
          </div>
        </section>

        <section className="panel">
          <h2>2 · Fire requests</h2>
          <div className="mode-row" role="group" aria-label="Burst mode">
            <button
              type="button"
              className={`mode ${mode === "sequential" ? "active" : ""}`}
              onClick={() => setMode("sequential")}
              disabled={running}
            >
              Sequential
              <small>default · clear allow → deny</small>
            </button>
            <button
              type="button"
              className={`mode ${mode === "parallel" ? "active" : ""}`}
              onClick={() => setMode("parallel")}
              disabled={running}
            >
              Limited parallel
              <small>concurrency stress</small>
            </button>
          </div>
          <div className="form-grid compact">
            <label>
              Request count
              <input
                type="number"
                min={1}
                max={500}
                value={requestCount}
                onChange={(e) => setRequestCount(Number(e.target.value))}
                disabled={running}
              />
            </label>
            {mode === "parallel" ? (
              <label>
                Concurrency
                <input
                  type="number"
                  min={2}
                  max={50}
                  value={concurrency}
                  onChange={(e) => setConcurrency(Number(e.target.value))}
                  disabled={running}
                />
              </label>
            ) : null}
          </div>
          <button
            type="button"
            className="btn primary wide"
            onClick={onBurst}
            disabled={running}
          >
            {running ? "Sending…" : `Send ${requestCount} requests`}
          </button>
          <p className="status" role="status">
            {status}
          </p>
          {error ? <p className="error">{error}</p> : null}
        </section>

        <section className="panel span-2">
          <div className="stats">
            <div>
              <span>Allowed</span>
              <strong className="ok">{allowedCount}</strong>
            </div>
            <div>
              <span>Denied</span>
              <strong className="bad">{deniedCount}</strong>
            </div>
            <div>
              <span>Avg latency</span>
              <strong>{avgLatency === null ? "—" : `${avgLatency} ms`}</strong>
            </div>
          </div>
          <h2>Latency</h2>
          <LatencyChart
            points={results.map((r) => ({
              index: r.index,
              latencyMs: r.latencyMs,
              allowed: r.allowed,
            }))}
          />
          <h2>Allow / deny stream</h2>
          <ul className="stream" aria-live="polite">
            {results.length === 0 ? (
              <li className="muted">No requests yet.</li>
            ) : (
              results.map((r) => (
                <li key={r.index} className={r.allowed ? "allow" : "deny"}>
                  <span className="idx">#{r.index}</span>
                  <span className="verdict">
                    {r.error ? "error" : r.allowed ? "allow" : "deny"}
                  </span>
                  <span className="rem">rem {r.remaining}</span>
                  <span className="lat">{r.latencyMs} ms</span>
                  <span className="code">{r.status || "—"}</span>
                </li>
              ))
            )}
          </ul>
        </section>
      </main>
    </div>
  );
}
