const ORDER = ["contact", "authority_claim", "urgency", "payment_request", "payment", "follow_up"];
const LABELS: Record<string, string> = {
  contact: "Contact",
  authority_claim: "Authority claim",
  urgency: "Urgency",
  payment_request: "Payment ask",
  payment: "Payment",
  follow_up: "Follow-up",
};

/** Horizontal scam-funnel stepper used on template and case views. */
export function StageStepper({ stages, highlightUpTo }: { stages: string[]; highlightUpTo?: number }) {
  const present = ORDER.filter(s => stages.includes(s));
  const list = present.length ? present : stages;
  return (
    <ol className="flex flex-wrap items-center gap-y-2" aria-label="Scam stage sequence">
      {list.map((stage, i) => {
        const active = highlightUpTo === undefined || i <= highlightUpTo;
        return (
          <li key={stage} className="flex items-center">
            <span
              className={`rounded-md border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${
                active ? "border-brand/40 bg-brandsoft text-brand" : "border-border bg-surface2 text-muted"
              }`}
            >
              {LABELS[stage] ?? stage}
            </span>
            {i < list.length - 1 && (
              <svg viewBox="0 0 16 12" className="mx-1 h-3 w-4 text-muted" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden="true">
                <path d="M1 6h12M9 2l4 4-4 4" strokeLinecap="round" strokeLinejoin="round" />
              </svg>
            )}
          </li>
        );
      })}
    </ol>
  );
}
