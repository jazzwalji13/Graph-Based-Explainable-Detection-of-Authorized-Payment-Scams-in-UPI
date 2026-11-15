import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { DemoStory } from "../api/types";
import { Spinner, ErrorState } from "../components/Feedback";
import { Icon } from "../components/Icon";
import { formatINR } from "../format";

export default function Simulator() {
  const navigate = useNavigate();
  const [seed, setSeed] = useState(42);
  const [users, setUsers] = useState(1000);
  const [days, setDays] = useState(150);
  const [scamRate, setScamRate] = useState(0.016);
  const [busy, setBusy] = useState<"seed" | "demo" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<unknown>(null);
  const [demo, setDemo] = useState<DemoStory | null>(null);

  useEffect(() => { api.health().catch(() => undefined); }, []);

  const regenerate = async () => {
    setBusy("seed"); setError(null); setSummary(null);
    try {
      const res = await api.simulate({ seed, users, days, scam_rate: scamRate });
      setSummary(res.summary);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Re-seed failed.");
    } finally {
      setBusy(null);
    }
  };

  const playDemo = async () => {
    setBusy("demo"); setError(null);
    try {
      const res = await api.demoStory();
      setDemo(res);
      navigate(`/?demo=1`);
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Demo story unavailable — run `make seed` first.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="mx-auto max-w-5xl p-4 sm:p-6">
      <h1 className="text-2xl font-extrabold tracking-tight text-ink">Simulator</h1>
      <p className="mt-1 max-w-2xl text-sm text-muted">
        Everything here is synthetic. Re-seed to regenerate users, payments, scam funnels, drift and noise deterministically.
        The demo story replays one scripted scam end-to-end in under two minutes.
      </p>

      {/* demo CTA */}
      <div className="mt-4 flex flex-col items-start justify-between gap-4 rounded-card border border-brand/40 bg-gradient-to-br from-brandsoft to-surface p-5 shadow-card sm:flex-row sm:items-center">
        <div>
          <p className="flex items-center gap-2 text-[10px] font-bold uppercase tracking-widest text-brand"><Icon name="spark" className="h-4 w-4" /> Guided demo</p>
          <h2 className="mt-1 text-lg font-extrabold text-ink">Fake electricity-department call — ₹80,000 paid under pressure</h2>
          <p className="mt-1 max-w-md text-xs leading-snug text-muted">
            Meena Devi gets a hinglish call from "Bijli Vibhag", pays ₹80,000 to a new payee, notices something's wrong,
            and the bank's layer catches it — check-in, confirmation, report, simulated submission.
          </p>
        </div>
        <button onClick={() => void playDemo()} disabled={busy !== null}
                className="group inline-flex shrink-0 items-center gap-2 rounded-xl bg-brand px-6 py-4 text-base font-extrabold text-brandink shadow-pop transition-transform hover:scale-105 disabled:opacity-60">
          {busy === "demo" ? <Spinner label="" /> : <Icon name="play" className="h-6 w-6 transition-transform group-hover:translate-x-0.5" />}
          Play demo story
        </button>
      </div>
      {demo && <p className="mt-2 text-xs text-muted">Last demo run: case #{demo.case_id} · {formatINR(demo.amount)} to <span className="font-mono">{demo.payee_handle}</span></p>}

      {/* reseed controls */}
      <div className="mt-5 grid gap-4 md:grid-cols-5">
        <div className="rounded-card border border-border bg-surface p-4 shadow-card md:col-span-2">
          <h2 className="text-xs font-extrabold uppercase tracking-widest text-muted">Regenerate dataset</h2>
          <div className="mt-3 grid grid-cols-2 gap-3">
            <label className="text-[11px] font-semibold text-muted">Random seed
              <input type="number" value={seed} onChange={e => setSeed(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-ink" />
            </label>
            <label className="text-[11px] font-semibold text-muted">Users
              <input type="number" min={100} max={5000} step={100} value={users} onChange={e => setUsers(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-ink" />
            </label>
            <label className="text-[11px] font-semibold text-muted">Days of history
              <input type="number" min={30} max={365} step={10} value={days} onChange={e => setDays(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-ink" />
            </label>
            <label className="text-[11px] font-semibold text-muted">Scam rate
              <input type="number" min={0.005} max={0.05} step={0.002} value={scamRate} onChange={e => setScamRate(Number(e.target.value))} className="mt-1 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-sm text-ink" />
            </label>
          </div>
          <button onClick={() => void regenerate()} disabled={busy !== null}
                  className="mt-3 w-full rounded-xl border border-brand bg-surface px-4 py-2.5 text-sm font-bold text-brand hover:bg-brandsoft disabled:opacity-60">
            {busy === "seed" ? "Re-seeding (takes ~30–60s)…" : "Regenerate data & retrain model"}
          </button>
          {error && <div className="mt-2"><ErrorState title="Re-seed failed" detail={error} /></div>}
        </div>

        <div className="rounded-card border border-border bg-surface p-4 shadow-card md:col-span-3">
          <h2 className="text-xs font-extrabold uppercase tracking-widest text-muted">What gets generated</h2>
          <ul className="mt-2 list-disc space-y-1 pl-5 text-xs leading-snug text-muted">
            <li><span className="font-semibold text-ink">1,000 users</span> with baseline behaviour: payees, amounts, frequency, device habits, salary/retirement segments.</li>
            <li><span className="font-semibold text-ink">Hard negatives</span> — rent deposits, medical emergencies, genuine bank fraud calls, family transfers — with distress-like behaviour to punish naive flagging.</li>
            <li><span className="font-semibold text-ink">5 scam types</span> (digital arrest, utility bill, KYC/SIM, task/investment, impersonated relative) with stage sequences and EN/HI/Hinglish scripts.</li>
            <li><span className="font-semibold text-ink">Post-payment distress</span> — balance checks, reversal searches, support calls, failed payee contact. ~30% of victims show none (non-realization).</li>
            <li><span className="font-semibold text-ink">Drift</span> — an unseen <span className="font-semibold text-ink">e-challan / court e-summons</span> variant appears only in the last ~28 days of the timeline.</li>
            <li><span className="font-semibold text-ink">Missing signals</span> — ~15% of scams have no usable text; ~5% of feature rows are noisy.</li>
          </ul>
          {!!summary && (
            <pre className="mt-3 max-h-40 overflow-auto rounded-xl border border-border bg-surface2/60 p-3 text-[10px] leading-snug text-ink">{JSON.stringify(summary, null, 2)}</pre>
          )}
        </div>
      </div>
    </div>
  );
}
