import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CaseDetail as CaseDetailType, ReportEnvelope } from "../api/types";
import { CaseGraph } from "../components/CaseGraph";
import { ReasonList } from "../components/ReasonList";
import { ReportPreview } from "../components/ReportPreview";
import { CompletenessRing } from "../components/CompletenessRing";
import { Spinner, ErrorState } from "../components/Feedback";
import { Badge, ScoreChip } from "../components/Badge";
import { Icon } from "../components/Icon";
import { StageStepper } from "../components/StageStepper";
import { formatDateTime, formatINR, prettyScamType, timeAgo } from "../format";

export default function CaseDetail() {
  const { id } = useParams<{ id: string }>();
  const caseId = Number(id);
  const [detail, setDetail] = useState<CaseDetailType | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [report, setReport] = useState<ReportEnvelope | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      const d = await api.getCase(caseId);
      setDetail(d);
      if (d.report) setReport(await api.getReport(d.report.id));
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Failed to load case.");
    }
  }, [caseId]);

  useEffect(() => { void load(); }, [load]);

  const act = async (name: string, fn: () => Promise<unknown>) => {
    setBusy(name);
    try { await fn(); await load(); } catch (e) { setError(e instanceof ApiError ? e.message : String(e)); } finally { setBusy(null); }
  };

  if (error) return <div className="p-6"><ErrorState title="Could not open case" detail={error} onRetry={() => void load()} /></div>;
  if (!detail) return <Spinner label="Loading case graph…" />;

  const f = detail.features;
  const open = detail.status === "open";
  const confirmed = detail.status === "confirmed";

  return (
    <div className="mx-auto max-w-7xl p-4 sm:p-6">
      {/* header */}
      <Link to="/analyst" className="inline-flex items-center gap-1 text-xs font-bold text-muted hover:text-ink">
        <Icon name="chevron-left" className="h-4 w-4" /> Back to queue
      </Link>
      <div className="mt-2 flex flex-wrap items-start justify-between gap-3">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-extrabold tracking-tight text-ink">Case #{detail.id}</h1>
            <ScoreChip score={detail.score} />
            <Badge tone={confirmed ? "ok" : open ? "warn" : "muted"}>{detail.status}</Badge>
            {detail.graph.top_features.length > 0 && <Badge tone="brand">{prettyScamType(detail.scam_type)}</Badge>}
          </div>
          <p className="mt-1 text-sm text-muted">
            <span className="font-semibold text-ink">{detail.user_name}</span> ({detail.city}, {detail.segment.replace("_", " ")}) · paid {timeAgo(detail.payment_ts)} · {formatDateTime(detail.payment_ts)}
          </p>
        </div>
        <div className="text-right">
          <p className="text-3xl font-black tabular-nums tracking-tight text-ink">{formatINR(detail.amount)}</p>
          <p className="font-mono text-[10px] text-muted">{detail.graph.payment_ref}</p>
        </div>
      </div>

      {/* facts strip */}
      <div className="mt-3 grid grid-cols-2 gap-2 md:grid-cols-4">
        {[
          { label: "Payee", value: detail.payee_name, sub: detail.payee_handle },
          { label: "New payee?", value: f.new_payee >= 1 ? "Yes" : "No", sub: `prior reports: ${detail.payee_prior_reports} · fan-in: ${detail.payee_fan_in}` },
          { label: "Amount z-score", value: `${f.amount_z.toFixed(2)}σ`, sub: "vs customer's own baseline" },
          { label: "Mobilization", value: f.fd_break >= 1 ? "FD broken" : f.loan_taken >= 1 ? "Loan taken" : "None", sub: "pre-payment stress signal" },
        ].map((s, i) => (
          <div key={i} className="rounded-card border border-border bg-surface p-3 shadow-card">
            <p className="text-[9px] font-bold uppercase tracking-widest text-muted">{s.label}</p>
            <p className="mt-0.5 truncate text-sm font-bold text-ink" title={String(s.value)}>{s.value}</p>
            <p className="truncate text-[10px] text-muted" title={s.sub}>{s.sub}</p>
          </div>
        ))}
      </div>

      {/* actions */}
      <div className="mt-3 flex flex-wrap items-center gap-2">
        {open && (
          <button onClick={() => act("confirm", () => api.answerCheckin(caseId, "confirm"))} disabled={busy !== null}
                  className="rounded-lg bg-ok px-3 py-2 text-xs font-bold text-white hover:opacity-90 disabled:opacity-50">
            {busy === "confirm" ? "…" : "Mark customer-confirmed"}
          </button>
        )}
        <button onClick={() => act("callback", () => api.requestCallback(caseId))} disabled={busy !== null}
                className="rounded-lg border border-border bg-surface px-3 py-2 text-xs font-bold text-ink hover:bg-surface2 disabled:opacity-50">
          {busy === "callback" ? "…" : "Request human callback"}
        </button>
        <button onClick={() => act("dismiss", () => api.dismissCase(caseId))} disabled={busy !== null}
                className="rounded-lg border border-danger/30 bg-dangersoft px-3 py-2 text-xs font-bold text-danger hover:opacity-90 disabled:opacity-50">
          {busy === "dismiss" ? "…" : "Dismiss (legit)"}
        </button>
        {confirmed && !report && (
          <button onClick={() => act("report", () => api.createReport(caseId))} disabled={busy !== null}
                  className="rounded-lg bg-brand px-3 py-2 text-xs font-bold text-brandink hover:opacity-90 disabled:opacity-50">
            {busy === "report" ? "Building…" : "Build report"}
          </button>
        )}
        {detail.report && (
          <a href="#report-preview" className="inline-flex items-center gap-1 rounded-lg border border-brand/40 bg-brandsoft px-3 py-2 text-xs font-bold text-brand">
            {detail.report.status === "submitted" ? `Submitted · ${detail.report.reference_id}` : "Report draft below"} <Icon name="chevron-right" className="h-3.5 w-3.5" />
          </a>
        )}
      </div>

      {/* main grid: graph + reasons/timeline */}
      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <div className="rounded-card border border-border bg-surface p-4 shadow-card lg:col-span-2">
          <h2 className="text-sm font-extrabold uppercase tracking-widest text-muted">Explainable case graph</h2>
          <div className="mt-2"><CaseGraph graph={detail.graph} /></div>
        </div>

        <div className="flex flex-col gap-4">
          <div className="rounded-card border border-border bg-surface p-4 shadow-card">
            <h2 className="text-sm font-extrabold uppercase tracking-widest text-muted">Why this was flagged</h2>
            <div className="mt-2"><ReasonList reasons={detail.graph.reasons} /></div>
            <div className="mt-3 border-t border-border pt-3">
              <p className="text-[10px] font-bold uppercase tracking-widest text-muted">Top model contributors</p>
              <ul className="mt-1.5 space-y-1">
                {detail.graph.top_features.slice(0, 5).map(tf => (
                  <li key={tf.feature} className="flex items-center gap-2 text-[11px]">
                    <span className="w-36 truncate font-mono text-muted" title={tf.feature}>{tf.feature}</span>
                    <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface2">
                      <div className="h-full rounded-full bg-brand/70" style={{ width: `${Math.min(100, tf.share * 100)}%` }} />
                    </div>
                    <span className="w-12 text-right font-mono tabular-nums text-ink">{(tf.share * 100).toFixed(0)}%</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="rounded-card border border-border bg-surface p-4 shadow-card">
            <h2 className="text-sm font-extrabold uppercase tracking-widest text-muted">Stage timeline</h2>
            {detail.timeline.length > 0
              ? <div className="mt-2"><StageStepper stages={detail.timeline.map(t => t.stage)} /></div>
              : <p className="mt-2 text-xs text-muted">No script on record (text signal unavailable) — flags came from behavioural features.</p>}
            <ol className="mt-2 max-h-48 space-y-1.5 overflow-y-auto">
              {detail.timeline.map((e, i) => (
                <li key={i} className="text-[11px] leading-snug">
                  <span className="font-mono tabular-nums text-muted">{formatDateTime(e.ts)}</span>{" "}
                  <span className="font-semibold text-ink">{e.stage.replace(/_/g, " ")}</span>
                  <p className="text-muted">{e.text}</p>
                </li>
              ))}
              {detail.behaviors.map((b, i) => (
                <li key={`b${i}`} className="text-[11px] leading-snug">
                  <span className="font-mono tabular-nums text-muted">{formatDateTime(b.ts)}</span>{" "}
                  <span className="font-semibold text-danger">{b.kind.replace(/_/g, " ")}</span>
                  <p className="text-muted">{b.detail}</p>
                </li>
              ))}
            </ol>
          </div>
        </div>
      </div>

      {/* report preview */}
      {report && (
        <div id="report-preview" className="mt-4 scroll-mt-6">
          <div className="mb-2 flex items-center justify-between">
            <h2 className="text-sm font-extrabold uppercase tracking-widest text-muted">Structured report</h2>
            <CompletenessRing value={report.completeness} size={56} />
          </div>
          <ReportPreview report={report} />
        </div>
      )}
    </div>
  );
}
