import { useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import { Icon } from "./Icon";
import { SyntheticBanner } from "./Banner";
import { useTheme } from "../theme";

const NAV = [
  { to: "/", label: "Customer app", icon: "phone" as const, end: true },
  { to: "/analyst", label: "Analyst queue", icon: "inbox" as const },
  { to: "/scams", label: "Emerging scams", icon: "radar" as const },
  { to: "/budget", label: "Budget Lab", icon: "sliders" as const },
  { to: "/metrics", label: "Metrics", icon: "chart" as const },
  { to: "/simulator", label: "Simulator", icon: "play" as const },
];

export function Layout() {
  const { theme, toggle } = useTheme();
  const [open, setOpen] = useState(false);
  const location = useLocation();

  return (
    <div className="flex h-screen flex-col overflow-hidden">
      <SyntheticBanner />
      <div className="flex min-h-0 flex-1">
        {/* Sidebar */}
        <aside
          className={`fixed bottom-0 left-0 top-[27px] z-40 w-60 shrink-0 transform border-r border-border bg-surface transition-transform duration-200 lg:static lg:z-auto lg:top-auto lg:translate-x-0 ${open ? "translate-x-0" : "-translate-x-full"}`}
          aria-label="Primary navigation"
        >
          <div className="flex h-full flex-col">
            <div className="flex items-center gap-2.5 border-b border-border px-4 py-3.5">
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-brand text-brandink shadow-card">
                <Icon name="logo" className="h-5 w-5" strokeWidth={1.9} />
              </span>
              <div className="min-w-0">
                <p className="text-[15px] font-extrabold leading-tight tracking-tight text-ink">SCAM<span className="text-brand">-</span>REPORT</p>
                <p className="text-[10px] font-medium uppercase tracking-widest text-muted">Post-payment layer</p>
              </div>
            </div>
            <nav className="flex-1 overflow-y-auto p-2.5">
              {NAV.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    `mb-1 flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                      isActive ? "bg-brandsoft text-brand" : "text-muted hover:bg-surface2 hover:text-ink"
                    }`
                  }
                >
                  <Icon name={item.icon} className="h-[18px] w-[18px]" />
                  {item.label}
                </NavLink>
              ))}
            </nav>
            <div className="border-t border-border p-3 text-[10px] leading-snug text-muted">
              Bank-agnostic demo. No real bank, customer or platform data. Submission is simulated.
            </div>
          </div>
        </aside>
        {open && <button aria-label="Close menu" className="fixed inset-0 z-30 bg-black/40 lg:hidden" onClick={() => setOpen(false)} />}

        {/* Main column */}
        <div className="flex min-w-0 flex-1 flex-col">
          <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface px-3 sm:px-5">
            <button className="rounded-lg p-2 text-muted hover:bg-surface2 lg:hidden" onClick={() => setOpen(o => !o)} aria-label="Toggle menu">
              <Icon name="menu" className="h-5 w-5" />
            </button>
            <p className="hidden text-xs font-semibold uppercase tracking-widest text-muted sm:block">
              {NAV.find(n => n.to === location.pathname)?.label ?? "Case view"}
            </p>
            <div className="ml-auto flex items-center gap-2">
              <span className="hidden rounded-full border border-warn/40 bg-warnsoft px-2.5 py-1 text-[10px] font-bold uppercase tracking-widest text-warn md:inline-flex">
                Synthetic demo
              </span>
              <button onClick={toggle} aria-label="Toggle dark mode"
                      className="rounded-lg p-2 text-muted transition-colors hover:bg-surface2 hover:text-ink">
                <Icon name={theme === "light" ? "moon" : "sun"} className="h-5 w-5" />
              </button>
            </div>
          </header>
          <main className="min-h-0 flex-1 overflow-y-auto">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
