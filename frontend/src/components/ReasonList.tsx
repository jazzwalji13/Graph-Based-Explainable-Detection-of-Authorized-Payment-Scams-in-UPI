import { Icon } from "./Icon";

export function ReasonList({ reasons, compact = false }: { reasons: string[]; compact?: boolean }) {
  if (!reasons.length) return <p className="text-sm text-muted">No standout reason codes — inspect the graph.</p>;
  return (
    <ul className={compact ? "space-y-1.5" : "space-y-2"}>
      {reasons.map((r, i) => (
        <li key={i} className="flex items-start gap-2 text-sm text-ink">
          <span className="mt-0.5 flex h-4.5 w-4.5 shrink-0 items-center justify-center rounded-full bg-brandsoft">
            <Icon name="check" className="h-3 w-3 text-brand" strokeWidth={2.5} />
          </span>
          <span>{r}</span>
        </li>
      ))}
    </ul>
  );
}
