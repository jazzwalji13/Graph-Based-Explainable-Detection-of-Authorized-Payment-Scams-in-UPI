import { Icon } from "./Icon";

export function Spinner({ label = "Loading…" }: { label?: string }) {
  return (
    <div role="status" aria-live="polite" className="flex items-center justify-center gap-3 py-16 text-muted">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-border border-t-brand" />
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ title = "Something went wrong", detail, onRetry }: { title?: string; detail?: string; onRetry?: () => void }) {
  return (
    <div role="alert" className="mx-auto max-w-md rounded-card border border-danger/30 bg-dangersoft p-6 text-center">
      <Icon name="alert" className="mx-auto mb-2 w-6 h-6 text-danger" />
      <p className="font-semibold text-ink">{title}</p>
      {detail && <p className="mt-1 text-sm text-muted break-words">{detail}</p>}
      {onRetry && (
        <button onClick={onRetry}
                className="mt-4 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-brandink hover:opacity-90">
          Try again
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, detail, action }: { title: string; detail?: string; action?: React.ReactNode }) {
  return (
    <div className="mx-auto max-w-md rounded-card border border-dashed border-border bg-surface p-8 text-center">
      <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-surface2">
        <Icon name="inbox" className="w-6 h-6 text-muted" />
      </div>
      <p className="font-semibold text-ink">{title}</p>
      {detail && <p className="mt-1 text-sm text-muted">{detail}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
