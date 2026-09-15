"use client";

type Point = { index: number; latencyMs: number; allowed: boolean };

type Props = {
  points: Point[];
};

export function LatencyChart({ points }: Props) {
  const width = 480;
  const height = 140;
  const pad = 12;
  const data = points.slice(-60);
  const maxLat = Math.max(1, ...data.map((p) => p.latencyMs));

  if (data.length === 0) {
    return (
      <div className="chart-empty" aria-hidden>
        Latency chart appears after you fire requests
      </div>
    );
  }

  const coords = data.map((p, i) => {
    const x =
      pad + (i / Math.max(1, data.length - 1)) * (width - pad * 2);
    const y = height - pad - (p.latencyMs / maxLat) * (height - pad * 2);
    return { x, y, ...p };
  });

  const path = coords
    .map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`)
    .join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="latency-chart"
      role="img"
      aria-label="Request latency chart"
    >
      <path d={path} className="latency-line" fill="none" />
      {coords.map((c) => (
        <circle
          key={c.index}
          cx={c.x}
          cy={c.y}
          r={3}
          className={c.allowed ? "dot-allow" : "dot-deny"}
        />
      ))}
    </svg>
  );
}
