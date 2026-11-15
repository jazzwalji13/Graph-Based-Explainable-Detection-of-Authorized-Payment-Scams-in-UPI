import type { ReactNode } from "react";

type Tone = "ok" | "warn" | "danger" | "muted" | "brand" | "accent";

const TONES: Record<Tone, string> = {
  ok: "bg-oksoft text-ok border-ok/30",
  warn: "bg-warnsoft text-warn border-warn/30",
  danger: "bg-dangersoft text-danger border-danger/30",
  muted: "bg-surface2 text-muted border-border",
  brand: "bg-brandsoft text-brand border-brand/30",
  accent: "bg-warnsoft text-accent border-accent/30",
};

export function Badge({ tone = "muted", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${TONES[tone]}`}>
      {children}
    </span>
  );
}

export function ScoreChip({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const tone: Tone = score >= 0.85 ? "danger" : score >= 0.7 ? "warn" : "accent";
  return <Badge tone={tone}>{pct}% risk</Badge>;
}

export function StatCard({ label, value, sub, icon }: { label: string; value: ReactNode; sub?: string; icon?: ReactNode }) {
  return (
    <div className="rounded-card border border-border bg-surface p-4 shadow-card">
      <div className="flex items-center justify-between gap-2">
        <p className="text-xs font-semibold uppercase tracking-wider text-muted">{label}</p>
        {icon && <div className="text-brand">{icon}</div>}
      </div>
      <p className="mt-2 text-2xl font-bold tabular-nums tracking-tight text-ink">{value}</p>
      {sub && <p className="mt-1 text-xs text-muted">{sub}</p>}
    </div>
  );
}
