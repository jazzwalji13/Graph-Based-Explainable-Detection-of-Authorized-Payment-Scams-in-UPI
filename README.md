# SCAM-REPORT

**A bank-agnostic post-payment layer that detects, confirms and reports payment-enabled scams — after the money has moved, while time still matters.**

When a customer has *already* paid (often under manipulation), the least bad tools are: notice fast, ask gently, capture a structured report, and treat confirmed incidents as evidence for better countermeasures. SCAM-REPORT does exactly that:

1. **Scores every UPI payment** with a calibrated GBDT model over payment context, interaction, post-payment behaviour, financial mobilisation and script-language features.
2. **Asks the customer** — a rate-limited, budget-aware, *non-accusatory* check-in ("Did someone pressure you or rush you to make this payment?"). The system never accuses.
3. **Builds a structured report** the customer approves line-by-line (mock NCRB-style format), then **simulates submission** to a mock endpoint (no real integration exists or works).
4. **Explains every flag** with a per-case, interactive case graph (LightGBM feature contributions mapped onto a timeline) plus plain-language reason codes.
5. **Discovers emerging scam workflows** from confirmed scripts via TF-IDF + KMeans clustering, proposes templates with novelty scores, and lets a human approve/reject them.
6. **Stays affordable** through an alert-budget engine (`P(scam)·V(delay) ≥ c₀·(1 + α·n_recent)`) with silent-log / soft / direct / human-callback tiers, cooldowns and campaign deduplication.

> ⚠️ **Synthetic data. Not real-world performance.** Every user, payment, payee, scam and report in this repository is simulated. Submission is a mock endpoint returning a fake reference ID. **No real bank, customer, telco or platform data is used anywhere.**

---

## Architecture

```
                        ┌─────────────────────────────┐
                        │   React + Vite + Tailwind    │
                        │  Customer app (phone frame)  │
                        │  Analyst queue · Case graph  │
                        │  Emerging scams · Budget Lab │
                        │  Metrics · Simulator         │
                        └──────────────┬───────────────┘
                                       │ typed REST (JSON)
                        ┌──────────────▼───────────────┐
                        │        FastAPI (8011)         │
                        │  /cases  /reports  /templates │
                        │  /budget/simulate  /metrics   │
                        └──────────────┬───────────────┘
              ┌────────────────┬───────┴────────┬─────────────────┐
              ▼                ▼                ▼                 ▼
        simulator.py     features.py     budget.py         report.py
        (synthetic       (payment +      (budget rule,      (structured
         funnels,         behaviour +     replay + tiers,    report, consent,
         scripts in       text risk       cooldown, dedup,   completeness;    │
         EN/HI/Hinglish,  features)       curves vs baseline template-first)  ▼
         drift, noise)         │                │            LLM optional
              ▼                ▼                ▼            (LLM_API_KEY)
        ┌──────────────────────────────────────────────────┐
        │             SQLite (data/scam_report.db)          │
        └──────────────────────────┬───────────────────────┘
                                   ▼
                 model.py (LightGBM + sigmoid calibration,
                   temporal split)  ·  explain.py (GraphJSON)
                   discovery.py (TF-IDF + KMeans → templates,
                   novelty score)  ·  evaluate.py (metrics.json)
```

Repo layout (trimmed):

```
scam-report/
  Makefile · make.py · scripts/dev.py · .env.example
  backend/app/    main.py db.py schemas.py simulator.py features.py model.py
                  explain.py discovery.py budget.py report.py evaluate.py seed.py
  backend/tests/  simulator determinism · budget engine · report completeness · case-graph schema
  frontend/src/   pages/ components/ api/ (typed client) theme.tsx i18n.tsx
```

---

## Setup & run (offline-capable)

Prereqs: **Python 3.11+**, **Node.js 18+**. No network access is needed at *runtime*; installs need it once.

```bash
make setup   # venv + pip deps + npm deps
make seed    # simulate → feature store → train → flag cases → evaluate (~45–60s)
make dev     # backend on :8011 (docs at /docs), frontend on :5173
```

On Windows without `make` (make 4.4.1 is also fine to install): use `python make.py setup|seed|dev|test` — identical.

Then open **http://localhost:5173**. API docs: **http://localhost:8011/docs**. Re-seed: `python -m app.seed '{"seed": 99, "users": 1000}'` (or the Simulator page).

Optional `.env` (see `.env.example`): `SIM_CONFIG` to point at a JSON with simulator overrides, `LLM_API_KEY`/`LLM_BASE_URL`/`LLM_MODEL` to enable LLM phrasing (off by default; see AI-use disclosure).

## Demo script (≈90 seconds)

1. **Simulator** page → **Play demo story** (or open `http://localhost:5173/?demo=1`).
2. Watch the customer phone frame: Meena Devi, a ₹80,000 payment to a new payee (`bijli-helpdesk9917@okicici`) at 10:24, while on a hinglish "Bijli Vibhag" call — flagged critical at ~99.9% confidence with reasons (new payee + active call, 12σ amount, reversal search, 1930 contact, payee unreachable).
3. Answer check-in **Yes** (auto-play does it) → intake pre-fills from the stage timeline → **Review my report** → check the line items & 100% completeness ring → tick the approval → **Submit report** → confirmation screen with reference ID `SIM-NCRB-XXXXXX` and next steps (1930 / cybercrime.gov.in as plain information text).
4. Click **View in analyst case view** → the explainable case graph (17 nodes; gold-ringed = top-3 contributors; animated edges = supports-stage evidence), top model contributors, stage timeline, reasons.
5. **Emerging scams** → proposed templates including the drift variant `e_challan_summons` (novelty ≈ 0.94) → approve/reject one.
6. **Budget Lab** → drag c₀ / α / window / decay → recall-vs-check-ins curve moves live vs the fixed-threshold baseline; tiers and per-1,000 check-in rate update.
7. **Metrics** → synthetic evaluation: PR-AUC ≈ 0.9999, recall@2% budget ≈ 1.0, hard-negative false-flag 0.0%, vs rule-based (recall 0.32) and transaction-only GBDT. Clearly labeled synthetic.

The demo case is deterministic and **replays**: Simulator → Play demo story resets it (status open, check-ins/reports wiped).

## API surface (all JSON; see `/docs`)

| Method | Path | Purpose |
|---|---|---|
| POST | `/simulate` | Re-run the whole pipeline with overrides (seed, users, days, scam_rate, flag_threshold, drift_start_day) |
| GET  | `/health` | Liveness + seeded flag |
| GET  | `/cases/summary` | Queue stats (open, confirmed, avg minutes-to-confirm) |
| GET  | `/cases?status=&scam_type=&min_score=&q=&limit=&offset=` | Flagged queue, risk-sorted, filterable |
| GET  | `/cases/{id}` | Full detail + features + timeline + behaviour + **case-graph JSON** |
| POST | `/cases/{id}/checkin` | Record `confirm\|deny\|unsure` (customer's call; updates status) |
| POST | `/cases/{id}/request-callback` | Escalate to human callback (simulated) |
| POST | `/cases/{id}/dismiss` | Mark legit |
| POST | `/cases/{id}/report` | Build/return structured report (409 until customer confirms/unsure) |
| GET  | `/reports/{id}` | Fetch report (`id` int or `report_id`) |
| POST | `/reports/{id}/submit` | **Simulated** submission → `SIM-NCRB-XXXXXX` |
| GET  | `/templates?status=` | Proposed/approved emerging-scam templates |
| POST | `/templates/{id}/approve` · `/reject` | Human governance of discovered templates |
| POST | `/budget/simulate` | Replay test window chronologically; returns operating point + 16-pt budget-aware curve + fixed-threshold baseline curve |
| GET  | `/metrics` | `metrics.json`: PR-AUC, recall@flag, recall@2% budget, hard-negative false-flag, check-ins/1k, leave-one-scam-type-out recall, baselines |
| GET  | `/customer/overview` | Demo user + recent payments + pending case |
| POST | `/demo/story` · `/demo/reset` | Reset deterministic demo case for replay |

## Assumptions (explicit defaults)

1. **Single demo customer** (`id=1`, "Meena Devi") backs the phone frame; analysts see all ~940 flagged cases.
2. **Timeline is fixed-date** (`2026-06-16` + 150 days) for full determinism; dates are synthetic.
3. **Check-ins are sent to the demo case only after flagging**, not to all ~940 flagged users; `/budget/simulate` does the honest math on the held-out window.
4. **Text signals** come from transcripts the bank *would* have only with consent/partner rails — ~55% of synthetic scams have **no text** and must be caught on behaviour/context, like reality.
5. **`stage_count`** is derived from text when present, else a noisy 0–4 from post-payment distress behaviour — deliberately overlapping with genuine emergencies.
6. **Genuine bank fraud calls** carry authority/threat language — the canonical hard negative — as do medical/family urgency pleas.
7. **Check-in answers are ground truth from the customer**; there is no third-party adjudicator.
8. **Report consent flags default to true** but are editable in the UI; the payload stores them verbatim.
9. **Report is built server-side from stored facts only.** Optional LLM is used *only* to phrase the narrative from those facts (never to invent amounts, names, UTls); on any failure the deterministic template is used.
10. **Template discovery** (TF-IDF + KMeans, k≈10) proposes clusters with novelty ≥ 0.55 as `proposed`; bank-approved templates from the seeded catalogue are never auto-approved.
11. **Metrics are synthetic** and flattering because the data is clean by construction — see Limitations.
12. `make dev` binds backend to `0.0.0.0:8011` — local/demo use only.

## Limitations

- **Synthetic ≠ predictive power.** Features separate scams almost perfectly on this corpus (PR-AUC ≈ 1.0); on real rails, expect degradation from: adversarial scripts, shared-device families, merchant miscoding, and silent victims (~38% show no distress — our leave-one-type-out table shows where recall actually bends).
- **Not real-world validation.** No backtest against real incidents, no label noise study, no adversarial red-team.
- **No fund tracing, freezing, recoverability estimates, or scammer investigation — by design.** SCAM-REPORT only detects and reports.
- **Submission is simulated.** There is no NCRB/1930/bank integration; the reference ID is a mock.
- **Budget engine** assumes recall ≈ answer rate of check-ins; real friction (unread notifications) is unmodelled.
- **Single-node SQLite**, no auth/RBAC, no PII encryption at rest — demo-grade infrastructure.
- **LLM optional**; the default path is fully deterministic. Even when enabled, the LLM phrases from a locked fact JSON and cannot create facts; narrative-only.

## AI-use & dataset disclosure

- **No real data, ever.** All 1,000 users, payees, handles, scripts, complaint funnels and metrics were generated by `backend/app/simulator.py` (seeded, configurable via `sim_config.json`).
- **Scripts** in English, Hindi (Devanagari) and Hinglish were hand-authored for the five scam families + one injected drift variant (`e_challan_summons`, a fake court/e-summons pattern, appearing only in the last ~28 days).
- **Code assistance**: built with an AI pair-programming assistant; all generated code was reviewed, typed (Type hints + TS strict), tested (`pytest`, `tsc --noEmit`) and run.
- **Explainability**: contributions are LightGBM's built-in TreeSHAP-equivalent `pred_contrib` values (`shap` itself not required); "top contributors" are largest |log-odds| nodes.
- **LLM (optional)**: if `LLM_API_KEY` is set, the narrative (2 sentences) is phrased by the configured model from *only* the extracted fact JSON. Facts, IDs, amounts, timestamps and consent flags come from the database and cannot be overridden by the model.
- **Model card (synthetic)**: LightGBM, scale_pos_weight ≈ 60, temporal split 66/12/22 train/calibration/test, sigmoid-calibrated, ~39k train rows, PR-AUC 0.9999, flag threshold 0.62, check-ins ≈ 15.5 / 1,000 payments, precision @ flag 1.0 (synthetic).

## Verification & tests

```bash
make test    # backend pytest (12 tests) + frontend tsc --noEmit + production build
```

- Simulator determinism, demo-payment injection, drift presence, EN/HI/Hinglish coverage
- Budget engine: V-decay monotonicity, cooldown/dedup, replay recall bounds, c₀ suppression
- Report completeness weighting & mandatory field presence
- Case-graph JSON schema: node types, edge types, highlighted top-contributors, resolvable node ids

---

*SCAM-REPORT is a working proof-of-concept for a review meeting. It is not legal, financial or compliance advice. Report real scams via 1930 / https://cybercrime.gov.in.*
