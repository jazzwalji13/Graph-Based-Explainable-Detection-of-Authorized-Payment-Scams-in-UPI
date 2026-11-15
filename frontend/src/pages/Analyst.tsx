import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CasesSummary, CaseListItem } from "../api/types";
import { StatCard, ScoreChip, Badge } from "../components/Badge";
import { Spinner, ErrorState, EmptyState } from "../components/Feedback";
import { Icon } from "../components/Icon";
import { formatDateTime, formatINR, prettyScamType, timeAgo } from "../format";

const SCAM_TYPES = ["", "digital_arrest", "utility_bill", "kyc_sim", "task_investment", "relative_impersonation", "e_challan_summons"];
const STATUSES = ["", "open", "confirmed", "denied", "unsure", "dismissed"];

export default function Analyst() {
  const navigate = useNavigate();
  const [summary, setSummary] = useState<CasesSummary | null>(null);
  const [items, setItems] = useState<CaseListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState("");
  const [scamType, setScamType] = useState("");
  const [minScore, setMinScore] = useState(0.62);
  const [q, setQ] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [sum, res] = await Promise.all([
        api.casesSummary(),
        api.listCases({ status: status || undefined, scam_type: scamType || undefined, min_score: minScore, q: q || undefined, limit: 80 }),
      ]);
      setSummary(sum);
      setItems(res.items);
      setTotal(res.total);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load cases.");
    } finally {
      setLoading(false);
    }
  }, [status, scamType, minScore, q]);

  useEffect(() => {
    const t = window.setTimeout(() => void load(), 220);
    return () => window.clearTimeout(t);
  }, [load]);

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      {/* summary cards */}
      <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="Open cases" value={summary?.open ?? "—"} sub="Awaiting customer check-in" icon={<Icon name="inbox" className="h-5 w-5" />} />
        <StatCard label="Confirmed scams" value={summary?.confirmed ?? "—"} sub="Customer-confirmed" icon={<Icon name="flag" className="h-5 w-5" />} />
        <StatCard label="Avg. time to report" value={summary?.avg_minutes_to_confirm != null ? `${summary.avg_minutes_to_confirm.toFixed(0)} min` : "—"} sub="From payment to confirmation" icon={<Icon name="clock" className="h-5 w-5" />} />
        <StatCard label="Total flagged" value={summary?.total_flagged ?? "—"} sub="Model-flagged queue volume" icon={<Icon name="shield" className="h-5 w-5" />} />
      </div>

      {/* filters */}
      <div className="mt-4 flex flex-wrap items-center gap-2 rounded-card border border-border bg-surface p-3 shadow-card">
        <label className="relative min-w-[180px] flex-1">
          <Icon name="search" className="pointer-events-none absolute left-2.5 top-2.5 h-4 w-4 text-muted" />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="Search customer or payee handle…"
                 className="w-full rounded-lg border border-border bg-surface py-2 pl-9 pr-3 text-sm text-ink placeholder:text-muted" />
        </label>
        <select aria-label="Scam type" value={scamType} onChange={e => setScamType(e.target.value)}
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm text-ink">
          {SCAM_TYPES.map(s => <option key={s} value={s}>{s ? prettyScamType(s) : "All scam types"}</option>)}
        </select>
        <select aria-label="Status" value={status} onChange={e => setStatus(e.target.value)}
                className="rounded-lg border border-border bg-surface px-3 py-2 text-sm capitalize text-ink">
          {STATUSES.map(s => <option key={s} value={s}>{s ? s : "All statuses"}</option>)}
        </select>
        <label className="flex items-center gap-2 text-xs font-semibold text-muted">
          Min confidence
          <input type="range" min={0.5} max={0.95} step={0.01} value={minScore} onChange={e => setMinScore(Number(e.target.value))} className="accent-[#0d6e69]" aria-label="Minimum confidence" />
          <span className="w-10 tabular-nums text-ink">{Math.round(minScore * 100)}%</span>
        </label>
        <span className="ml-auto text-xs tabular-nums text-muted">{total} case{total === 1 ? "" : "s"}</span>
      </div>

      {/* queue */}
      {loading && <Spinner label="Loading flagged cases…" />}
      {error && <div className="mt-6"><ErrorState title="Could not load the queue" detail={error} onRetry={() => void load()} /></div>}
      {!loading && !error && items.length === 0 && (
        <div className="mt-6"><EmptyState title="No cases match these filters" detail="Lower the confidence slider or clear the search." /></div>
      )}
      {!loading && !error && items.length > 0 && (
        <div className="mt-4 overflow-hidden rounded-card border border-border bg-surface shadow-card">
          <table className="w-full min-w-[760px] text-sm">
            <thead className="bg-surface2/70 text-left text-[10px] font-bold uppercase tracking-widest text-muted">
              <tr>
                <th className="px-4 py-2.5">Case</th><th className="px-3 py-2.5">Customer</th>
                <th className="px-3 py-2.5 text-right">Amount</th><th className="px-3 py-2.5">Scam type</th>
                <th className="px-3 py-2.5">Payee</th><th className="px-3 py-2.5">Risk</th>
                <th className="px-3 py-2.5">Status</th><th className="px-3 py-2.5">When</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {items.map(c => (
                <tr key={c.id} onClick={() => navigate(`/case/${c.id}`)}
                    className="cursor-pointer transition-colors hover:bg-brandsoft/40" tabIndex={0}
                    onKeyDown={e => { if (e.key === "Enter") navigate(`/case/${c.id}`); }}
                    aria-label={`Open case ${c.id}, risk ${(c.score * 100).toFixed(0)} percent`}>
                  <td className="px-4 py-2.5 font-mono text-xs font-bold text-brand">#{c.id}{c.is_demo === 1 && <span title="Demo case"> ★</span>}</td>
                  <td className="px-3 py-2.5"><p className="font-semibold text-ink">{c.user_name}</p><p className="text-[10px] text-muted">{c.city} · {c.segment.replace("_", " ")}</p></td>
                  <td className="px-3 py-2.5 text-right font-mono tabular-nums text-ink">{formatINR(c.amount)}</td>
                  <td className="px-3 py-2.5 text-xs text-ink">{prettyScamType(c.scam_type)}</td>
                  <td className="max-w-[160px] truncate px-3 py-2.5 font-mono text-[11px] text-muted" title={c.payee_handle}>{c.payee_handle}</td>
                  <td className="px-3 py-2.5"><ScoreChip score={c.score} /></td>
                  <td className="px-3 py-2.5"><Badge tone={(c.status === "confirmed" ? "ok" : c.status === "open" ? "warn" : "muted")}>{c.status}</Badge></td>
                  <td className="px-3 py-2.5 text-[11px] text-muted" title={formatDateTime(c.payment_ts)}>{timeAgo(c.payment_ts)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="mt-3 text-center text-[10px] uppercase tracking-widest text-muted">Synthetic data — queue sorted by model risk, not real fraud</p>
    </div>
  );
}
