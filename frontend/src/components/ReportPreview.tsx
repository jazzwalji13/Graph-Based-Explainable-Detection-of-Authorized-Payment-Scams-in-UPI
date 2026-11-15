import type { ReactNode } from "react";
import type { ReportEnvelope } from "../api/types";
import { CompletenessRing } from "./CompletenessRing";
import { StageStepper } from "./StageStepper";
import { formatDateTime, formatINR } from "../format";
import { Icon } from "./Icon";

const STAGE_LABEL: Record<string, string> = {
  contact: "Contact", authority_claim: "Claimed authority", urgency: "Urgency",
  payment_request: "Payment request", payment: "Payment", follow_up: "Follow-up",
};

/** Structured report preview — everything the customer approves before submission. */
export function ReportPreview({ report, actions }: { report: ReportEnvelope; actions?: ReactNode }) {
  const p = report.payload;
  return (
    <div className="overflow-hidden rounded-card border border-border bg-surface shadow-card">
      <div className="flex flex-wrap items-center gap-3 border-b border-border bg-surface2/60 px-4 py-2.5">
        <Icon name="file" className="h-5 w-5 text-brand" />
        <div className="min-w-0">
          <p className="text-sm font-bold text-ink">Report {report.report_id}</p>
          <p className="text-[10px] uppercase tracking-widest text-muted">Structured scam-incident report · mock NCRB format</p>
        </div>
        <div className="ml-auto flex items-center gap-3">
          <CompletenessRing value={report.completeness} size={64} />
        </div>
      </div>

      <div className="grid gap-4 p-4 md:grid-cols-2">
        <section>
          <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted">Payment</h4>
          <dl className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
            <dt className="text-muted">Amount</dt><dd className="font-semibold tabular-nums text-ink">{formatINR(p.amount)}</dd>
            <dt className="text-muted">UTR</dt><dd className="font-mono text-ink">{p.payment_refs.utr}</dd>
            <dt className="text-muted">UPI ref</dt><dd className="font-mono text-ink">{p.payment_refs.upi_ref}</dd>
            <dt className="text-muted">Paid at</dt><dd className="text-ink">{p.timestamps.payment ? formatDateTime(p.timestamps.payment) : "—"}</dd>
          </dl>
        </section>
        <section>
          <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted">Payee</h4>
          <dl className="mt-1.5 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-xs">
            <dt className="text-muted">Handle</dt><dd className="break-all font-mono text-ink">{p.payee.handle}</dd>
            <dt className="text-muted">Name</dt><dd className="text-ink">{p.payee.name}</dd>
            <dt className="text-muted">Prior reports</dt><dd className="tabular-nums text-ink">{p.payee.prior_reports}</dd>
            <dt className="text-muted">Identifier</dt><dd className="font-mono text-ink">{p.payee.identifier}</dd>
          </dl>
        </section>
        <section>
          <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted">Scam classification</h4>
          <div className="mt-1.5 space-y-1 text-xs">
            <p className="font-semibold text-ink">{p.scam_type_label}</p>
            <p className="text-muted">First contact: <span className="text-ink">{p.first_contact_channel.replace(/_/g, " ")}</span></p>
            <p className="text-muted">Claimed identity: <span className="text-ink">{p.claimed_identity}</span></p>
            <p className="text-muted">Urgency cues: <span className="text-ink">{p.urgency_cues.join(", ")}</span></p>
            <p className="text-muted">Comms: <span className="font-mono text-ink">{p.communication_identifiers.caller_number_masked}</span> · {p.communication_identifiers.languages.join("/")}</p>
          </div>
        </section>
        <section>
          <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted">Customer confirmation</h4>
          <p className="mt-1.5 text-xs text-ink">
            Status: <span className="font-semibold">{p.customer_confirmation.status.replace(/_/g, " ")}</span>
          </p>
          <p className="mt-1 text-[11px] leading-snug text-muted">{p.customer_confirmation.answer_note}</p>
          <h4 className="mt-3 text-[10px] font-bold uppercase tracking-widest text-muted">Model (explainable)</h4>
          <p className="mt-1 text-xs text-ink">Confidence <span className="font-mono">{(p.model.confidence * 100).toFixed(1)}%</span> · tier {p.model.risk_tier}</p>
          <div className="mt-1.5 flex flex-wrap gap-1">
            {p.model.reason_codes.map((r, i) => (
              <span key={i} className="rounded-md bg-brandsoft px-1.5 py-0.5 text-[10px] font-medium text-brand">{r}</span>
            ))}
          </div>
        </section>
      </div>

      <div className="border-t border-border px-4 py-3">
        <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted">Stage timeline</h4>
        <div className="mt-1.5"><StageStepper stages={p.stage_timeline.map(s => s.stage)} /></div>
        <ol className="mt-2 max-h-36 space-y-1 overflow-y-auto">
          {p.stage_timeline.map((s, i) => (
            <li key={i} className="flex gap-2 text-[11px] leading-snug">
              <span className="w-24 shrink-0 font-mono tabular-nums text-muted">{formatDateTime(s.ts)}</span>
              <span className="w-28 shrink-0 font-semibold text-ink">{STAGE_LABEL[s.stage] ?? s.stage}</span>
              <span className="text-muted">{s.detail}</span>
            </li>
          ))}
        </ol>
      </div>

      <div className="grid gap-3 border-t border-border px-4 py-3 md:grid-cols-2">
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted">Evidence (mock attachments)</h4>
          <ul className="mt-1.5 space-y-1">
            {p.evidence.map((e) => (
              <li key={e.name} className="flex items-center gap-1.5 text-[11px] text-ink">
                <Icon name="file" className="h-3.5 w-3.5 text-muted" /> {e.name}
                <span className="text-[9px] uppercase tracking-wide text-muted">({e.kind}, mock)</span>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="text-[10px] font-bold uppercase tracking-widest text-muted">Narrative {p.llm_used ? "(LLM-phrased)" : "(template)"}</h4>
          <p className="mt-1.5 text-[11px] leading-snug text-ink">{p.narrative}</p>
          <h4 className="mt-2 text-[10px] font-bold uppercase tracking-widest text-muted">Consent flags</h4>
          <ul className="mt-1 text-[11px] text-ink">
            {Object.entries(p.consent).map(([k, v]) => (
              <li key={k} className="flex items-center gap-1.5">
                <Icon name={v ? "check" : "x"} className={`h-3.5 w-3.5 ${v ? "text-ok" : "text-danger"}`} />
                {k.replace(/_/g, " ")}
              </li>
            ))}
          </ul>
        </div>
      </div>

      {actions && <div className="border-t border-border bg-surface2/40 px-4 py-3">{actions}</div>}
      <p className="border-t border-border px-4 py-1.5 text-center text-[9px] font-semibold uppercase tracking-widest text-warn">
        {p.synthetic_data_notice}
      </p>
    </div>
  );
}
