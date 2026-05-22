import { scoreColor } from "./GaugeChart";

export default function MetricBar({ label, value, delay = 0 }) {
  const col = scoreColor(value);
  return (
    <div className="mb-4">
      <div className="flex justify-between mb-1.5">
        <span className="font-mono text-[10px] tracking-widest text-muted">{label}</span>
        <span className="font-mono text-[10px] font-semibold" style={{ color: col }}>{value}</span>
      </div>
      <div className="h-[3px] rounded-full overflow-hidden" style={{ background: "#1A3A50" }}>
        <div
          className="h-full rounded-full bar-reveal"
          style={{
            "--w": `${value}%`,
            "--delay": `${delay}s`,
            background: col,
            boxShadow: `0 0 8px ${col}66`,
          }}
        />
      </div>
    </div>
  );
}
