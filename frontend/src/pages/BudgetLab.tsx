import { useEffect, useMemo, useState } from "react";
import {
  ComposedChart, Line, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { api, ApiError } from "../api/client";
import type { BudgetResult } from "../api/types";
import { Spinner, ErrorState } from "../components/Feedback";
import { Icon } from "../components/Icon";

function Slider({ label, value, min, max, step, format, onChange }: {
  label: string; value: number; min: number; max: number; step: number;
  format: (v: number) => string; onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-xs font-bold text-ink">{label}</span>
        <span className="font-mono text-xs tabular-nums text-brand">{format(value)}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
             onChange={e => onChange(Number(e.target.value))}
             className="mt-1 w-full accent-[#0d6e69]" aria-label={label} />
    </label>
  );
}

export default function BudgetLab() {
  const [c0, setC0] = useState(0.3);
  const [alpha, setAlpha] = useState(0.6);
  const [windowHrs, setWindowHrs] = useState(24);
  const [decay, setDecay] = useState(0.05);
  const [cooldown, setCooldown] = useState(180);
  const [result, setResult] = useState<BudgetResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = window.setTimeout(async () => {
      setLoading(true);
      setError(null);
      try {
        setResult(await api.budgetSimulate({ c0, alpha, window_minutes: Math.round(windowHrs * 60), decay, cooldown_minutes: cooldown }));
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Budget simulation failed.");
      } finally {
        setLoading(false);
      }
    }, 280);
    return () => window.clearTimeout(t);
  }, [c0, alpha, windowHrs, decay, cooldown]);

  const op = result?.operating_point;
  const tierMax = op ? Math.max(1, ...Object.values(op.tier_counts)) : 1;

  const curveData = useMemo(() => result?.curve ?? [], [result]);
  const baselineData = useMemo(() => result?.baseline_curve ?? [], [result]);

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <h1 className="text-2xl font-extrabold tracking-tight text-ink">Budget Lab</h1>
      <p className="mt-1 max-w-2xl text-sm text-muted">
        A check-in interrupts real people, so every alert must earn its cost. Tune the budget rule and watch the
        recall-versus-noise trade-off on the held-out future window — live.
      </p>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        {/* controls */}
        <div className="rounded-card border border-border bg-surface p-4 shadow-card">
          <h2 className="text-xs font-extrabold uppercase tracking-widest text-muted">Budget parameters</h2>
          <div className="mt-3 space-y-4">
            <Slider label="c0 — base cost of one check-in" value={c0} min={0.05} max={1.0} step={0.01} format={v => v.toFixed(2)} onChange={setC0} />
            <Slider label="α — fatigue multiplier per recent check-in" value={alpha} min={0} max={2} step={0.05} format={v => v.toFixed(2)} onChange={setAlpha} />
            <Slider label="Window — recent-count horizon" value={windowHrs} min={2} max={72} step={1} format={v => `${v}h`} onChange={setWindowHrs} />
            <Slider label="λ — value decay of acting fast" value={decay} min={0.01} max={0.15} step={0.005} format={v => `${v.toFixed(3)} /min`} onChange={setDecay} />
            <Slider label="Cooldown after a check-in" value={cooldown} min={0} max={720} step={15} format={v => `${v} min`} onChange={setCooldown} />
          </div>

          <div className="mt-4 rounded-xl border border-border bg-surface2/60 p-3">
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted">The rule</p>
            <p className="mt-1 font-mono text-[12px] leading-relaxed text-ink">
              check-in if&nbsp; P(scam) · V(delay) ≥ c₀ · (1 + α·n_recent)
            </p>
            <p className="mt-1 font-mono text-[11px] text-muted">V(delay) = e<sup>−λ·minutes_since_payment</sup> = {result?.operating_point.value_of_delay.toFixed(3) ?? "…"}</p>
            <p className="mt-1 text-[10px] leading-snug text-muted">n_recent = check-ins already sent to this customer inside the window. Cooldown and one-per-campaign deduplication apply on top.</p>
          </div>

          <div className="mt-3 rounded-xl border border-border bg-surface2/60 p-3 text-[10px] leading-snug text-muted">
            <p className="font-bold uppercase tracking-widest">Response tiers</p>
            <ul className="mt-1 space-y-0.5">
              <li><span className="font-semibold text-ink">silent_log</span> — below budget; monitor only</li>
              <li><span className="font-semibold text-ink">soft_checkin</span> — gentle in-app question (Yes / No / Not sure)</li>
              <li><span className="font-semibold text-ink">direct_checkin</span> — push + in-app question, higher priority</li>
              <li><span className="font-semibold text-ink">human_callback</span> — ≥ 3.0× budget; a human calls the customer</li>
            </ul>
          </div>
        </div>

        {/* chart */}
        <div className="rounded-card border border-border bg-surface p-4 shadow-card lg:col-span-2">
          <h2 className="text-xs font-extrabold uppercase tracking-widest text-muted">Recall vs check-ins per 1,000 payments</h2>
          {error && <ErrorState title="Simulation failed" detail={error} />}
          {loading && !result && <Spinner label="Replaying test window…" />}
          {result && (
            <>
              <div className="mt-2 h-72 w-full">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart margin={{ top: 12, right: 12, left: -4, bottom: 4 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--c-border))" />
                    <XAxis type="number" dataKey="checkins_per_1000" name="Check-ins / 1,000"
                            tick={{ fontSize: 10 }} label={{ value: "check-ins per 1,000 payments", position: "insideBottom", offset: -2, fontSize: 10 }}
                            domain={[0, 'dataMax + 10']} />
                    <YAxis type="number" dataKey="recall" domain={[0, 1]} tick={{ fontSize: 10 }}
                           label={{ value: "scam recall", angle: -90, position: "insideLeft", fontSize: 10, offset: 12 }} />
                    <Tooltip contentStyle={{ fontSize: 11, background: "rgb(var(--c-surface))", border: "1px solid rgb(var(--c-border))", borderRadius: 8 }}
                             formatter={(v: number, name: string) => [name === "recall" ? v.toFixed(3) : v.toFixed(2), name]} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    <Line data={curveData} type="monotone" dataKey="recall" name="Budget-aware (this rule)"
                          stroke="#0d9488" strokeWidth={2.5} dot={false} isAnimationActive={false} />
                    <Line data={baselineData} type="monotone" dataKey="recall" name="Fixed score threshold"
                          stroke="#94a3b8" strokeWidth={2} strokeDasharray="6 4" dot={false} isAnimationActive={false} />
                    {op && (
                      <Scatter data={[{ checkins_per_1000: op.checkins_per_1000, recall: op.recall }]}
                               dataKey="recall" name="This setting" fill="#d97706" stroke="#d97706" />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>
              <div className="mt-2 grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  { label: "Recall (test window)", value: op ? `${(op.recall * 100).toFixed(1)}%` : "—" },
                  { label: "Check-ins sent", value: op?.checkins_sent ?? "—" },
                  { label: "Per 1,000 payments", value: op?.checkins_per_1000.toFixed(1) ?? "—" },
                  { label: "Test scams", value: result.test_window.scams },
                ].map(s => (
                  <div key={s.label} className="rounded-xl border border-border bg-surface2/50 p-2 text-center">
                    <p className="text-[9px] font-bold uppercase tracking-wider text-muted">{s.label}</p>
                    <p className="mt-0.5 text-lg font-extrabold tabular-nums text-ink">{s.value}</p>
                  </div>
                ))}
              </div>
              <div className="mt-2">
                <p className="text-[9px] font-bold uppercase tracking-widest text-muted">Tier distribution (this setting)</p>
                <div className="mt-1 space-y-1">
                  {Object.entries(op?.tier_counts ?? {}).map(([tier, n]) => (
                    <div key={tier} className="flex items-center gap-2 text-[10px]">
                      <span className="w-24 truncate font-mono text-muted">{tier}</span>
                      <div className="h-2.5 flex-1 overflow-hidden rounded-full bg-surface2">
                        <div className={`h-full rounded-full ${tier === "human_callback" ? "bg-danger" : tier === "direct_checkin" ? "bg-accent" : tier === "soft_checkin" ? "bg-brand" : "bg-border"}`}
                             style={{ width: `${(n / tierMax) * 100}%` }} />
                      </div>
                      <span className="w-10 text-right tabular-nums text-ink">{n}</span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      <p className="mt-3 flex items-center justify-center gap-2 text-center text-[10px] uppercase tracking-widest text-muted">
        <Icon name="info" className="h-3.5 w-3.5" /> Replay is Chronological over the held-out future window ({result?.test_window.start?.slice(0, 10)} → {result?.test_window.end?.slice(0, 10)}) · synthetic data
      </p>
    </div>
  );
}
