export function scoreColor(s) {
  if (s >= 68) return "#00FF87";
  if (s >= 38) return "#FFB830";
  return "#FF3B5C";
}
export function scoreLabel(s) {
  if (s >= 68) return "CONFIÁVEL";
  if (s >= 38) return "SUSPEITO";
  return "FALSO";
}

export default function GaugeChart({ score, size = 220 }) {
  const r    = (size / 2) * 0.73;
  const cx   = size / 2;
  const cy   = size / 2;
  const circ = 2 * Math.PI * r;
  const offset = circ - (score / 100) * circ;
  const col  = scoreColor(score);
  const ticks = 40;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <defs>
        <filter id="gw2">
          <feGaussianBlur stdDeviation="4" result="b" />
          <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
        </filter>
      </defs>

      {/* tick marks */}
      {Array.from({ length: ticks }).map((_, i) => {
        const angle = ((i / ticks) * 360 - 90) * (Math.PI / 180);
        const r1 = r + 10, r2 = r + (i % 5 === 0 ? 16 : 13);
        return (
          <line key={i}
            x1={cx + r1 * Math.cos(angle)} y1={cy + r1 * Math.sin(angle)}
            x2={cx + r2 * Math.cos(angle)} y2={cy + r2 * Math.sin(angle)}
            stroke={i / ticks <= score / 100 ? col : "#1A3A50"}
            strokeWidth={i % 5 === 0 ? 2.5 : 1}
            opacity={i / ticks <= score / 100 ? 0.65 : 0.3}
          />
        );
      })}

      {/* track */}
      <circle cx={cx} cy={cy} r={r} fill="none" stroke="#1A3A50" strokeWidth="9" />

      {/* progress */}
      <circle cx={cx} cy={cy} r={r}
        fill="none" stroke={col} strokeWidth="9" strokeLinecap="round"
        strokeDasharray={circ}
        style={{ "--full": circ, "--offset": offset, strokeDashoffset: circ }}
        transform={`rotate(-90 ${cx} ${cy})`}
        className="anim-dash"
      />

      {/* glow */}
      <circle cx={cx} cy={cy} r={r}
        fill="none" stroke={col} strokeWidth="5" strokeLinecap="round"
        strokeDasharray={circ} strokeDashoffset={offset}
        transform={`rotate(-90 ${cx} ${cy})`}
        filter="url(#gw2)" opacity="0.4"
      />

      {/* score */}
      <text x={cx} y={cy - 8} textAnchor="middle"
        fill={col} fontSize={size * 0.19} fontWeight="800"
        fontFamily="Syne, sans-serif">{score}</text>
      <text x={cx} y={cy + 14} textAnchor="middle"
        fill={col} fontSize={size * 0.046} fontFamily="JetBrains Mono, monospace"
        letterSpacing="4">{scoreLabel(score)}</text>
      <text x={cx} y={cy + 30} textAnchor="middle"
        fill="#3A6070" fontSize={size * 0.038} fontFamily="JetBrains Mono, monospace"
        letterSpacing="2">SCORE / 100</text>
    </svg>
  );
}
