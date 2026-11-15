/** SVG progress ring for report completeness (0–100). */
export function CompletenessRing({ value, size = 84 }: { value: number; size?: number }) {
  const stroke = 8;
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  const offset = c * (1 - pct / 100);
  const tone = pct >= 85 ? "#16a34a" : pct >= 60 ? "#d97706" : "#ef4444";
  return (
    <div className="flex flex-col items-center gap-1.5" role="img" aria-label={`Report completeness ${pct}%`}>
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} stroke="rgb(var(--c-surface2))" strokeWidth={stroke} fill="none" />
          <circle cx={size / 2} cy={size / 2} r={r} stroke={tone} strokeWidth={stroke} fill="none"
                  strokeLinecap="round" strokeDasharray={c} strokeDashoffset={offset}
                  style={{ transition: "stroke-dashoffset 600ms ease" }} />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <p className="text-base font-extrabold tabular-nums leading-none text-ink">{pct.toFixed(0)}<span className="text-[10px]">%</span></p>
        </div>
      </div>
      <p className="text-[10px] font-semibold uppercase tracking-wider text-muted">Completeness</p>
    </div>
  );
}
