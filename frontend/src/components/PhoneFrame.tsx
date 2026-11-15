import type { ReactNode } from "react";
import { Icon } from "./Icon";

/** Smartphone shell used by the customer app. */
export function PhoneFrame({ children, bankName = "Suraksha Bank" }: { children: ReactNode; bankName?: string }) {
  return (
    <div className="mx-auto w-full max-w-[380px]">
      <div className="rounded-[2.4rem] border border-border bg-neutral-900 p-2 shadow-pop">
        <div className="phone-notch relative overflow-hidden rounded-[1.9rem] bg-surface">
          {/* status bar */}
          <div className="flex items-center justify-between px-5 pt-3 text-[10px] font-semibold text-ink/80">
            <span>10:24</span>
            <span className="flex items-center gap-1.5">
              <Icon name="signal" className="h-3 w-3" /><Icon name="wifi" className="h-3.5 w-3.5" /><Icon name="battery" className="h-4 w-4" />
            </span>
          </div>
          {/* app header */}
          <div className="flex items-center gap-2 border-b border-border px-4 py-2">
            <span className="flex h-7 w-7 items-center justify-center rounded-lg bg-brand text-[11px] font-black text-brandink">SB</span>
            <div className="leading-tight">
              <p className="text-[11px] font-extrabold text-ink">{bankName}</p>
              <p className="text-[8px] uppercase tracking-widest text-muted">UPI payments</p>
            </div>
            <span className="ml-auto rounded-full bg-oksoft px-2 py-0.5 text-[8px] font-bold uppercase tracking-wider text-ok">Secured</span>
          </div>
          {/* screen */}
          <div className="h-[560px] overflow-y-auto bg-bg">{children}</div>
        </div>
      </div>
    </div>
  );
}
