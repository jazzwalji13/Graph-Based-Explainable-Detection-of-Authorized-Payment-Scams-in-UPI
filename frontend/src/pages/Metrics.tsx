import { useEffect, useState } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { api, ApiError } from "../api/client";
import type { Metrics } from "../api/types";
import { Spinner, ErrorState } from "../components/Feedback";
import { StatCard } from "../components/Badge";
import { Icon } from "../components/Icon";
import { prettyScamType } from "../format";

export default function MetricsPage() {
  const [m, setM] = useState<Metrics | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.metrics().then(setM).catch(e => setError(e instanceof ApiError ? e.message : "Failed to load metrics — run `make seed`."));
  }, []);

  if (error) return <div className="p-6"><ErrorState title="Metrics unavailable" detail={error} /></div>;
  if (!m) return <Spinner label="Loading synthetic evaluation…" />;

  const model = m.model;
  const cmpData = [
    { name: "PR-AUC", SCAM_REPORT: model.pr_auc, "Transaction-only": m.baselines.transaction_only_model.pr_auc, "Rule-based": null as number | null },
    { name: "Recall @ 2% budget", SCAM_REPORT: model.recall_at_fixed_budget, "Transaction-only": m.baselines.transaction_only_model.recall_at_fixed_budget, "Rule-based": m.baselines.rule_based.recall },
    { name: "Recall @ flag threshold", SCAM_REPORT: model.recall_at_flag_threshold, "Transaction-only": m.baselines.transaction_only_model.recall_at_flag_threshold, "Rule-based": m.baselines.rule_based.recall },
  ];

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      <div role="note" aria-label="Synthetic data notice" className="rounded-card border border-warn/50 bg-warnsoft px-4 py-2 text-center text-[11px] font-bold uppercase tracking-widest text-warn">
        Synthetic data. Not real-world performance.
      </div>

      <div className="mt-4 flex flex-wrap items-end justify-between gap-2">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-ink">Evaluation metrics</h1>
          <p className="mt-1 text-xs text-muted">
            Held-out <span className="font-semibold text-ink">future window</span> ({m.test_window.start.slice(0, 10)} → {m.test_window.end.slice(0, 10)})
            · {m.test_window.payments.toLocaleString("en-IN")} payments · {m.test_window.scams} scams · temporal train/calibration/test split (66/12/22)
            · generated {m.generated_at.replace("T", " ")}
          </p>
        </div>
        <p className="rounded-lg border border-border bg-surface px-2 py-1 font-mono text-[10px] text-muted">flag threshold {m.flag_threshold}</p>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        <StatCard label="PR-AUC" value={model.pr_auc.toFixed(3)} sub="Avg. precision — the headline metric for rare scams" icon={<Icon name="chart" className="h-5 w-5" />} />
        <StatCard label="Recall @ 2% budget" value={`${(model.recall_at_fixed_budget * 100).toFixed(1)}%`} sub="Flag only top 2% of payments" icon={<Icon name="flag" className="h-5 w-5" />} />
        <StatCard label="False-flag on hard negatives" value={`${(model.false_flag_rate_hard_negatives * 100).toFixed(1)}%`} sub="Rent, medical, genuine bank calls, family transfers" icon={<Icon name="alert" className="h-5 w-5" />} />
        <StatCard label="Check-ins / 1,000" value={model.checkins_per_1000.toFixed(1)} sub={`Precision @ flag threshold ${(model.precision_at_flag_threshold * 100).toFixed(0)}%`} icon={<Icon name="sliders" className="h-5 w-5" />} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        <div className="rounded-card border border-border bg-surface p-4 shadow-card">
          <h2 className="text-xs font-extrabold uppercase tracking-widest text-muted">SCAM-REPORT vs baselines</h2>
          <div className="mt-2 h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={cmpData} margin={{ top: 8, right: 4, left: -8, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="rgb(var(--c-border))" />
                <XAxis dataKey="name" tick={{ fontSize: 9 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 10 }} />
                <Tooltip cursor={{ fill: "rgb(var(--c-surface2))" }} contentStyle={{ fontSize: 11, background: "rgb(var(--c-surface))", border: "1px solid rgb(var(--c-border))", borderRadius: 8 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="SCAM_REPORT" name="SCAM-REPORT (GBDT+calibration)" fill="#0d9488" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Transaction-only" name="Transaction-only GBDT" fill="#64748b" radius={[4, 4, 0, 0]} />
                <Bar dataKey="Rule-based" name="Rule-based (new+call+amount)" fill="#d97706" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-1 text-[10px] text-muted">Rule-based bar missing for PR-AUC: rule scores are binary, so AUPRC is undefined — recall is shown instead.</p>
        </div>

        <div className="rounded-card border border-border bg-surface p-4 shadow-card">
          <h2 className="text-xs font-extrabold uppercase tracking-widest text-muted">Leave-one-scam-type-out recall</h2>
          <p className="mt-0.5 text-[10px] text-muted">Recall on each scam family in the test window at the flag threshold. Low values expose generalisation gaps.</p>
          <table className="mt-2 w-full text-sm">
            <thead className="text-left text-[10px] font-bold uppercase tracking-widest text-muted">
              <tr><th className="py-1.5">Scam type</th><th className="py-1.5 text-right">Recall</th><th className="py-1.5 pl-4">Share of flags</th></tr>
            </thead>
            <tbody className="divide-y divide-border">
              {Object.entries(model.leave_one_scam_type_out_recall).map(([k, v]) => (
                <tr key={k}>
                  <td className="py-1.5 pr-2 text-xs font-semibold capitalize text-ink">{prettyScamType(k)}</td>
                  <td className="py-1.5 text-right font-mono tabular-nums text-ink">{v == null ? "—" : `${(v * 100).toFixed(0)}%`}</td>
                  <td className="py-1.5 pl-4">
                    <div className="h-2.5 w-full overflow-hidden rounded-full bg-surface2">
                      <div className="h-full rounded-full bg-brand/70" style={{ width: `${Math.min(100, (v ?? 0) * 100)}%` }} />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-3 border-t border-border pt-3 text-[11px] text-muted">
            <p className="font-bold uppercase tracking-widest text-[9px]">Baseline detail</p>
            <ul className="mt-1 space-y-0.5 font-mono text-[10px]">
              <li>rule-based: recall {(m.baselines.rule_based.recall * 100).toFixed(1)}% · false-flag {(m.baselines.rule_based.false_flag_rate_hard_negatives * 100).toFixed(1)}% · {m.baselines.rule_based.checkins_per_1000.toFixed(1)}/1k check-ins</li>
              <li>txn-only GBDT: PR-AUC {m.baselines.transaction_only_model.pr_auc.toFixed(3)} · recall@2% {(m.baselines.transaction_only_model.recall_at_fixed_budget * 100).toFixed(1)}% · {m.baselines.transaction_only_model.checkins_per_1000.toFixed(1)}/1k check-ins</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="mt-4 rounded-card border border-border bg-surface p-4 text-[11px] text-muted shadow-card">
        <p className="text-[10px] font-bold uppercase tracking-widest text-muted">How to read this</p>
        <ul className="mt-1 list-disc space-y-0.5 pl-5">
          {m.notes.map((n, i) => <li key={i}>{n}</li>)}
        </ul>
      </div>
    </div>
  );
}
