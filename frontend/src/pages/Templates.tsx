import { useCallback, useEffect, useState } from "react";
import { api, ApiError } from "../api/client";
import type { Template } from "../api/types";
import { Badge } from "../components/Badge";
import { Spinner, ErrorState, EmptyState } from "../components/Feedback";
import { Icon } from "../components/Icon";
import { StageStepper } from "../components/StageStepper";
import { prettyScamType } from "../format";

export default function Templates() {
  const [items, setItems] = useState<Template[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [filter, setFilter] = useState<"proposed" | "approved" | "all">("proposed");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.templates();
      setItems(res.items);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load templates.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const act = async (id: number, action: "approve" | "reject") => {
    setBusyId(id);
    try {
      if (action === "approve") await api.approveTemplate(id); else await api.rejectTemplate(id);
      await load();
    } finally {
      setBusyId(null);
    }
  };

  const visible = items.filter(t => (filter === "all" ? true : filter === "proposed" ? t.status === "proposed" : t.status === filter));
  const proposedCount = items.filter(t => t.status === "proposed").length;

  return (
    <div className="mx-auto max-w-6xl p-4 sm:p-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-extrabold tracking-tight text-ink">Emerging scam templates</h1>
          <p className="mt-1 max-w-xl text-sm text-muted">
            Confirmed scam dialogues are clustered (TF-IDF + KMeans). Clusters that don't match any bank-approved
            template are proposed automatically with a novelty score — recall this is how the injected
            <span className="font-semibold text-ink"> e-challan / court e-summons </span> variant surfaced late in the timeline.
          </p>
        </div>
        <div className="flex rounded-lg border border-border p-0.5 text-xs font-bold">
          {(["proposed", "approved", "all"] as const).map(f => (
            <button key={f} onClick={() => setFilter(f)}
                    className={`rounded-md px-3 py-1.5 capitalize ${filter === f ? "bg-brand text-brandink" : "text-muted"}`}>
              {f}{f === "proposed" && proposedCount > 0 ? ` (${proposedCount})` : ""}
            </button>
          ))}
        </div>
      </div>

      {loading && <Spinner label="Clustering and loading templates…" />}
      {error && <div className="mt-6"><ErrorState title="Could not load templates" detail={error} onRetry={() => void load()} /></div>}
      {!loading && !error && visible.length === 0 && (
        <div className="mt-6"><EmptyState title={filter === "proposed" ? "No novel clusters pending review" : "Nothing here yet"} detail="All clusters match approved templates — or the data was just reseeded." /></div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {visible.map(t => (
          <article key={t.id}
                   className={`flex flex-col rounded-card border bg-surface p-4 shadow-card ${t.status === "proposed" ? "border-accent/50 ring-1 ring-accent/30" : "border-border"}`}>
            <div className="flex flex-wrap items-center gap-2">
              {t.status === "proposed"
                ? <Badge tone="accent"><Icon name="spark" className="h-3 w-3" /> Proposed</Badge>
                : t.status === "approved"
                  ? <Badge tone="ok">Approved</Badge>
                  : <Badge tone="muted">Rejected</Badge>}
              <Badge tone="muted">{t.channel.replace(/_/g, " ")}</Badge>
              <span className="ml-auto text-[10px] font-semibold uppercase tracking-widest text-muted">{t.size} samples</span>
            </div>
            <h2 className="mt-2 font-bold text-ink">{t.name}</h2>
            <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-[11px]">
              <dt className="text-muted">Hook</dt><dd className="text-ink">{t.hook}</dd>
              <dt className="text-muted">Claimed identity</dt><dd className="text-ink">{t.claimed_identity}</dd>
              <dt className="text-muted">Urgency cues</dt><dd className="text-ink">{t.urgency_cue}</dd>
              <dt className="text-muted">Payment ask</dt><dd className="text-ink">{t.payment_ask}</dd>
              <dt className="text-muted">Scam family</dt><dd className="text-ink">{prettyScamType(t.scam_type)}</dd>
            </dl>
            <div className="mt-2"><StageStepper stages={t.stages} /></div>
            <div className="mt-2 flex flex-wrap gap-1">
              {t.top_terms.slice(0, 8).map(term => (
                <span key={term} className="rounded bg-surface2 px-1.5 py-0.5 font-mono text-[9px] text-muted">{term}</span>
              ))}
            </div>
            {t.script_samples.length > 0 && (
              <details className="mt-2 text-[11px] text-muted">
                <summary className="cursor-pointer font-semibold text-ink">Sample scripts ({t.script_samples.length})</summary>
                <ul className="mt-1 list-disc space-y-1 pl-4">
                  {t.script_samples.slice(0, 3).map((s, i) => <li key={i} className="leading-snug">“{s}”</li>)}
                </ul>
              </details>
            )}
            <div className="mt-3 flex items-center gap-3 border-t border-border pt-3">
              <div className="flex items-center gap-2">
                <div className="h-2 w-24 overflow-hidden rounded-full bg-surface2">
                  <div className={`h-full rounded-full ${t.novelty_score >= 0.6 ? "bg-accent" : "bg-brand/60"}`} style={{ width: `${Math.min(100, t.novelty_score * 100)}%` }} />
                </div>
                <span className="text-[10px] font-mono tabular-nums text-muted">novelty {t.novelty_score.toFixed(2)}</span>
              </div>
              {t.status === "proposed" && (
                <div className="ml-auto flex gap-1.5">
                  <button onClick={() => void act(t.id, "reject")} disabled={busyId === t.id}
                          className="rounded-lg border border-danger/30 bg-dangersoft px-2.5 py-1.5 text-[11px] font-bold text-danger hover:opacity-90 disabled:opacity-50">
                    Reject
                  </button>
                  <button onClick={() => void act(t.id, "approve")} disabled={busyId === t.id}
                          className="rounded-lg bg-brand px-2.5 py-1.5 text-[11px] font-bold text-brandink hover:opacity-90 disabled:opacity-50">
                    Approve &amp; track
                  </button>
                </div>
              )}
            </div>
          </article>
        ))}
      </div>
      <p className="mt-3 text-center text-[10px] uppercase tracking-widest text-muted">Templates power the template_match model feature and analyst playbooks</p>
    </div>
  );
}
