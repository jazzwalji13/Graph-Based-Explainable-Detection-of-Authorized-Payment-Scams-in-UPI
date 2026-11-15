import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import type { CaseDetail, CustomerOverview, ReportEnvelope } from "../api/types";
import { PhoneFrame } from "../components/PhoneFrame";
import { ReportPreview } from "../components/ReportPreview";
import { Spinner, ErrorState, EmptyState } from "../components/Feedback";
import { Badge } from "../components/Badge";
import { Icon } from "../components/Icon";
import { useLang } from "../i18n";
import { formatINR, timeAgo } from "../format";

type Step = "loading" | "idle" | "checkin" | "ack" | "intake" | "report" | "submitted";

export default function Customer() {
  const { t, lang, setLang } = useLang();
  const [searchParams] = useSearchParams();
  const demo = searchParams.get("demo") === "1";

  const [overview, setOverview] = useState<CustomerOverview | null>(null);
  const [caseDetail, setCaseDetail] = useState<CaseDetail | null>(null);
  const [step, setStep] = useState<Step>("loading");
  const [error, setError] = useState<string | null>(null);

  const [howContacted, setHowContacted] = useState("Phone call");
  const [claimedIdentity, setClaimedIdentity] = useState("");
  const [askedTo, setAskedTo] = useState("");
  const [contactDetail, setContactDetail] = useState("");
  const [brokeDeposit, setBrokeDeposit] = useState(false);

  const [approveChecked, setApproveChecked] = useState(false);
  const [report, setReport] = useState<ReportEnvelope | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [ackAnswer, setAckAnswer] = useState<"deny" | "unsure" | null>(null);
  const [autoPlay, setAutoPlay] = useState(demo);

  const caseId = overview?.demo_case_id ?? null;

  const load = useCallback(async () => {
    setStep("loading");
    setError(null);
    try {
      const ov = await api.customerOverview();
      setOverview(ov);
      if (ov.demo_case_id) {
        const cd = await api.getCase(ov.demo_case_id);
        setCaseDetail(cd);
        if (cd.status === "open") setStep("checkin");
        else if (cd.status === "confirmed" && cd.report?.status === "submitted") {
          const rep = await api.getReport(cd.report.id);
          setReport(rep);
          setStep("submitted");
        } else if (cd.status === "confirmed") setStep("intake");
        else setStep("idle");
        setClaimedIdentity(cd.timeline.find(e => e.stage === "authority_claim")?.text ?? "");
        setAskedTo(cd.timeline.find(e => e.stage === "payment_request")?.text ?? "");
      } else {
        setStep("idle");
      }
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not reach the API. Is the backend running on :8011?");
      setStep("idle");
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const answer = async (a: "confirm" | "deny" | "unsure") => {
    if (!caseId) return;
    await api.answerCheckin(caseId, a);
    if (a === "confirm") setStep("intake");
    else { setAckAnswer(a); setStep("ack"); }
  };

  const buildReport = async () => {
    if (!caseId) return;
    const rep = await api.createReport(caseId);
    setReport(rep);
    setStep("report");
  };

  const submit = async () => {
    if (!report) return;
    setSubmitting(true);
    try {
      const res = await api.submitReport(report.id);
      setReport({ ...report, status: "submitted", reference_id: res.reference_id, submitted_at: res.submitted_at });
      setStep("submitted");
      setAutoPlay(false);
    } finally {
      setSubmitting(false);
    }
  };

  const approveRef = useRef(false);
  const setApprove = (v: boolean) => { approveRef.current = v; setApproveChecked(v); };

  // -------- auto-play for the guided demo story --------
  useEffect(() => {
    if (!demo || !autoPlay) return;
    let timers: number[] = [];
    if (step === "checkin") timers.push(window.setTimeout(() => void answer("confirm"), 1600));
    else if (step === "intake") timers.push(window.setTimeout(() => void buildReport(), 2600));
    else if (step === "report") {
      timers.push(window.setTimeout(() => setApprove(true), 1400));
      timers.push(window.setTimeout(() => { if (approveRef.current) void submit(); }, 3000));
    }
    return () => timers.forEach(t => window.clearTimeout(t));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [demo, autoPlay, step]);

  const demoPendingCase = caseDetail ?? null;
  const pendingPayment = overview?.payments.find(p => p.is_demo === 1);

  return (
    <div className="mx-auto grid max-w-6xl gap-6 p-4 sm:p-6 lg:grid-cols-[minmax(0,420px)_1fr]">
      {/* ---- phone ---- */}
      <div>
        <PhoneFrame>
          {/* in-phone header row: language toggle + bank row handled by frame */}
          <div className="flex items-center justify-between px-4 pt-2">
            <p className="text-[10px] font-bold uppercase tracking-widest text-muted">{t("appTagline")}</p>
            <div className="flex rounded-lg border border-border p-0.5 text-[9px] font-bold">
              {(["en", "hi"] as const).map(l => (
                <button key={l} onClick={() => setLang(l)}
                        className={`rounded-md px-2 py-0.5 ${lang === l ? "bg-brand text-brandink" : "text-muted"}`}>
                  {l === "en" ? "EN" : "हिं"}
                </button>
              ))}
            </div>
          </div>

          {step === "loading" && <Spinner label="Loading your account…" />}
          {error && <ErrorState title="Backend unavailable" detail={error} onRetry={() => void load()} />}

          {/* greeting + payments (always visible once loaded) */}
          {overview && !error && (
            <div className="px-4 py-2">
              <p className="text-[15px] font-extrabold text-ink">Namaste, {overview.user.name.split(" ")[0]} 🙏</p>
              <p className="text-[10px] text-muted">{overview.user.city} · {overview.user.device_os === "android" ? "Android" : "iOS"} UPI handle verified</p>
            </div>
          )}

          {/* ---- check-in card ---- */}
          {step === "checkin" && demoPendingCase && (
            <section aria-label="Payment check-in" className="mx-3 mb-3 rounded-2xl border border-accent/40 bg-warnsoft p-3 shadow-card">
              <p className="flex items-center gap-1.5 text-[9px] font-bold uppercase tracking-widest text-warn">
                <Icon name="info" className="h-3.5 w-3.5" /> {t("checkinTitle")}
              </p>
              <p className="mt-1.5 text-[13px] font-semibold leading-snug text-ink">{t("checkinQuestion")}</p>
              <p className="mt-1 text-[10px] leading-snug text-muted">{t("checkinSub")}</p>
              <p className="mt-1.5 rounded-lg bg-surface/70 px-2 py-1 text-[10px] text-muted">
                Payment: <span className="font-semibold text-ink">{pendingPayment ? formatINR(pendingPayment.amount) : ""}</span>
                {pendingPayment && <> → <span className="font-mono">{pendingPayment.payee_handle}</span></>}
              </p>
              <div className="mt-2 grid grid-cols-3 gap-1.5">
                <button onClick={() => void answer("confirm")}
                        className="rounded-xl bg-brand px-2 py-2 text-[12px] font-bold text-brandink shadow-sm transition-transform hover:scale-[1.02]">
                  {t("yes")}
                </button>
                <button onClick={() => void answer("deny")}
                        className="rounded-xl border border-border bg-surface px-2 py-2 text-[12px] font-bold text-ink hover:bg-surface2">
                  {t("no")}
                </button>
                <button onClick={() => void answer("unsure")}
                        className="rounded-xl border border-border bg-surface px-2 py-2 text-[12px] font-bold text-ink hover:bg-surface2">
                  {t("unsure")}
                </button>
              </div>
            </section>
          )}

          {/* ---- acknowledgement for deny / unsure ---- */}
          {step === "ack" && (
            <section className="mx-3 mb-3 rounded-2xl border border-border bg-surface p-4 text-center">
              <Icon name="circle-check" className="mx-auto h-8 w-8 text-ok" />
              <p className="mt-2 text-sm font-bold text-ink">{ackAnswer === "deny" ? "Okay, noted. Dhanyavaad!" : "That's okay."}</p>
              <p className="mt-1 text-[11px] leading-snug text-muted">
                If you later remember pressure or a suspicious call, tap below — we'll pick it up right away. You can also call 1930 anytime.
              </p>
              <button onClick={() => setStep("checkin")} className="mt-3 rounded-xl border border-brand px-3 py-1.5 text-[11px] font-bold text-brand hover:bg-brandsoft">
                Actually, someone did pressure me
              </button>
            </section>
          )}

          {/* ---- intake form ---- */}
          {step === "intake" && (
            <section className="mx-3 mb-3 space-y-2 rounded-2xl border border-border bg-surface p-3" aria-label="Report intake">
              <p className="text-[12px] font-extrabold text-ink">{t("intakeTitle")}</p>
              {demoPendingCase && <Badge tone="warn">Case #{demoPendingCase.id} · under review</Badge>}
              <label className="block text-[10px] font-semibold text-muted">How were you contacted?
                <select value={howContacted} onChange={e => setHowContacted(e.target.value)} className="mt-0.5 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-[11px] text-ink">
                  <option>Phone call</option><option>Video call</option><option>SMS</option><option>WhatsApp</option><option>Other</option>
                </select>
              </label>
              <label className="block text-[10px] font-semibold text-muted">Who did they claim to be?
                <textarea value={claimedIdentity} onChange={e => setClaimedIdentity(e.target.value)} rows={2}
                          className="mt-0.5 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-[11px] text-ink" />
              </label>
              <label className="block text-[10px] font-semibold text-muted">What were you asked to do?
                <textarea value={askedTo} onChange={e => setAskedTo(e.target.value)} rows={2}
                          className="mt-0.5 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-[11px] text-ink" />
              </label>
              <label className="block text-[10px] font-semibold text-muted">Caller number / link they sent (if any)
                <input value={contactDetail} onChange={e => setContactDetail(e.target.value)} placeholder="e.g. 98XXX-XXXXX or a link"
                       className="mt-0.5 w-full rounded-lg border border-border bg-surface px-2 py-1.5 text-[11px] text-ink" />
              </label>
              <label className="flex items-center gap-2 text-[10px] font-semibold text-muted">
                <input type="checkbox" checked={brokeDeposit} onChange={e => setBrokeDeposit(e.target.checked)} className="h-3.5 w-3.5 accent-[#0d6e69]" />
                I broke an FD / took a loan for this payment
              </label>
              <button onClick={() => void buildReport()}
                      className="w-full rounded-xl bg-brand py-2 text-[12px] font-bold text-brandink">
                Review my report →
              </button>
            </section>
          )}

          {/* ---- report draft + approve + submit ---- */}
          {step === "report" && report && (
            <section className="mx-3 mb-3 space-y-2" aria-label="Report preview">
              <p className="text-[12px] font-extrabold text-ink">Please review before submitting</p>
              <ReportPreview report={report} actions={
                <>
                  <label className="flex items-start gap-2 text-[11px] font-semibold text-ink">
                    <input type="checkbox" checked={approveChecked} onChange={e => setApproveChecked(e.target.checked)} className="mt-0.5 h-4 w-4 accent-[#0d6e69]" />
                    {t("reportApprove")}
                  </label>
                  <button disabled={!approveChecked || submitting} onClick={() => void submit()}
                          className="mt-2 w-full rounded-xl bg-brand py-2 text-[12px] font-bold text-brandink disabled:cursor-not-allowed disabled:opacity-40">
                    {submitting ? "Submitting…" : t("submitReport")}
                  </button>
                  <p className="mt-1 text-center text-[9px] text-muted">Submission is simulated to a mock endpoint — no real authority is notified.</p>
                </>
              } />
            </section>
          )}

          {/* ---- submitted confirmation ---- */}
          {step === "submitted" && report && (
            <section className="mx-3 mb-3 rounded-2xl border border-ok/40 bg-oksoft p-4 text-center" aria-label="Submission confirmation">
              <Icon name="circle-check" className="mx-auto h-10 w-10 text-ok" />
              <p className="mt-2 text-[15px] font-extrabold text-ink">{t("reportSubmitted")}</p>
              <p className="mt-1 text-[10px] uppercase tracking-widest text-muted">{t("referenceId")}</p>
              <p className="mt-0.5 font-mono text-lg font-black tracking-wider text-brand">{report.reference_id}</p>
              <div className="mt-3 space-y-1.5 rounded-xl bg-surface/70 p-3 text-left">
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted">{t("nextStepsTitle")}</p>
                <p className="text-[10px] leading-snug text-ink">1. {t("nextSteps1")}</p>
                <p className="text-[10px] leading-snug text-ink">2. {t("nextSteps2")}</p>
                <p className="text-[10px] leading-snug text-ink">3. {t("nextSteps3")}</p>
              </div>
              <Link to={`/case/${caseId ?? ""}`} className="mt-3 inline-flex items-center gap-1 text-[11px] font-bold text-brand hover:underline">
                View in analyst case view <Icon name="arrow-right" className="h-3.5 w-3.5" />
              </Link>
            </section>
          )}

          {/* ---- recent payments list ---- */}
          {overview && (
            <section className="px-3 pb-4 pt-1" aria-label="Recent payments">
              <p className="mb-1.5 text-[10px] font-bold uppercase tracking-widest text-muted">{t("recentPayments")}</p>
              <ul className="divide-y divide-border overflow-hidden rounded-2xl border border-border bg-surface">
                {overview.payments.slice(0, 9).map(p => (
                  <li key={p.id} className="flex items-center gap-2 px-3 py-2">
                    <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-surface2 text-[10px] font-black text-muted">
                      {p.payee_name.split(" ").map(w => w[0]).slice(0, 2).join("")}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-[11px] font-semibold text-ink">{p.payee_name}</p>
                      <p className="truncate font-mono text-[9px] text-muted">{p.payee_handle}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-[11px] font-bold tabular-nums text-ink">{formatINR(p.amount)}</p>
                      <p className="text-[8px] text-muted">{timeAgo(p.ts)}</p>
                    </div>
                    {p.is_new_payee === 1 && <Badge tone="warn">New</Badge>}
                  </li>
                ))}
                {overview.payments.length === 0 && <li className="px-3 py-6"><EmptyState title="No payments yet" /></li>}
              </ul>
            </section>
          )}
        </PhoneFrame>
      </div>

      {/* ---- side panel ---- */}
      <div className="flex flex-col gap-4">
        {demo && step !== "submitted" && (
          <div className="rounded-card border border-brand/40 bg-brandsoft p-3 text-sm">
            <p className="flex items-center justify-between gap-2 font-bold text-brand">
              <span className="flex items-center gap-2"><Icon name="play" className="h-4 w-4" /> Demo story playing — fake electricity call, ₹80,000 to a new payee</span>
              {autoPlay && <button onClick={() => setAutoPlay(false)} className="rounded-lg border border-brand/40 px-2 py-1 text-[10px] font-bold uppercase tracking-wide hover:bg-surface">Stop auto-play</button>}
            </p>
            <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-ink">
              {(caseDetail?.timeline ?? []).map((e, i) => (
                <li key={i}><span className="font-semibold">{e.stage.replace(/_/g, " ")}</span> · {e.text.slice(0, 90)}{e.text.length > 90 ? "…" : ""}</li>
              ))}
            </ol>
          </div>
        )}

        <div className="rounded-card border border-border bg-surface p-5 shadow-card">
          <h1 className="text-xl font-extrabold tracking-tight text-ink">After every payment, a gentle double-check.</h1>
          <p className="mt-1 text-sm text-muted">
            When our model suspects a scam-shaped payment, the customer — never the system — decides.
            If they confirm, we build a structured report they approve line-by-line, then submission is simulated to existing channels.
          </p>
          <ol className="mt-4 space-y-2 text-sm text-ink">
            {["Silent risk scoring of all payments (model, not rules alone)",
              "Budget-aware, rate-limited check-ins — no alert spam",
              "Non-accusatory confirmation wording in English & हिंदी",
              "Customer-approved structured report (mock NCRB format)",
              "Analyst gets an explainable case graph with reason codes"].map((s, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brandsoft text-[10px] font-black text-brand">{i + 1}</span>
                {s}
              </li>
            ))}
          </ol>
        </div>

        <div className="rounded-card border border-warn/40 bg-warnsoft p-4 text-xs text-warn">
          <p className="flex items-center gap-2 font-bold"><Icon name="alert" className="h-4 w-4" /> Scope limits</p>
          <p className="mt-1 leading-snug">No fund tracing, no freezing, no recoverability claims, no contacting scammers or banks. Check-ins are rate-limited per user and per campaign. Everything shown here is synthetic.</p>
        </div>
      </div>
    </div>
  );
}
