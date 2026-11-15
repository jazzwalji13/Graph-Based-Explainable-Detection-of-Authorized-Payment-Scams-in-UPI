"""Seeded synthetic data generator: users, payees, payments, scam funnels, behaviour.

Deterministic for a given config seed. All data is synthetic.
"""
from __future__ import annotations

import json
import math
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

from . import db

CONFIG_PATH = Path(__file__).resolve().parent / "sim_config.json"

FIRST_NAMES = ["Aarav", "Vivaan", "Aditya", "Vihaan", "Ishaan", "Reyansh", "Sai", "Krishna", "Arjun", "Dhruv",
               "Ananya", "Diya", "Saanvi", "Ira", "Myra", "Sara", "Aadhya", "Kiara", "Pari", "Navya",
               "Rohan", "Karthik", "Manav", "Sneha", "Pooja", "Rohit", "Neha", "Aman", "Divya", "Anjali",
               "Meena", "Lakshmi", "Geeta", "Ramesh", "Suresh", "Priya", "Kavya", "Nikhil", "Tanvi", "Shreya"]
LAST_NAMES = ["Sharma", "Verma", "Gupta", "Patel", "Iyer", "Nair", "Reddy", "Rao", "Menon", "Joshi",
              "Bhat", "Kulkarni", "Desai", "Mehta", "Shah", "Malhotra", "Kapoor", "Chopra", "Bose", "Mukherjee",
              "Yadav", "Mishra", "Pandey", "Tripathi", "Saxena", "Agarwal", "Choudhary", "Das", "Sen", "Roy"]
CITIES = ["Lucknow", "Pune", "Jaipur", "Kochi", "Indore", "Nagpur", "Bhopal", "Chandigarh", "Coimbatore", "Patna",
          "Ahmedabad", "Hyderabad", "Delhi", "Bengaluru", "Chennai", "Kolkata", "Surat", "Kanpur", "Vadodara", "Ghaziabad"]
SEGMENTS = ["salaried", "self_employed", "retired", "student", "small_business", "gig_worker"]
SEGMENT_AVG = {"salaried": 950, "self_employed": 2400, "retired": 700, "student": 260, "small_business": 5200, "gig_worker": 480}
SEGMENT_FREQ = {"salaried": 9, "self_employed": 14, "retired": 6, "student": 8, "small_business": 18, "gig_worker": 12}

PAYEE_POOL = [
    ("shree-kirana@okhdfcbank", "Shree Kirana Store"), ("chaipoint@okicici", "Chai Point"),
    ("bigbasket@ybl", "BigBasket"), ("swiggy@okaxis", "Swiggy"), ("zomato@oksbi", "Zomato"),
    ("apollopharmacy@okicici", "Apollo Pharmacy"), ("uber@ybl", "Uber"), ("netflix@okhdfcbank", "Netflix"),
    ("tatapowerbill@okaxis", "Tata Power Bill"), ("airtelrecharge@oksbi", "Airtel Recharge"),
    ("jio@okhdfcbank", "Jio Store"), ("dmart@ybl", "DMart"), ("blinkit@okicici", "Blinkit"),
    ("cultfitness@okaxis", "Cult Fitness"), ("societymaint@okhdfcbank", "Society Maintenance"),
    ("tataplay@oksbi", "Tata Play"), ("jalboard@ybl", "Jal Board"), ("bescom@okaxis", "BESCOM"),
    ("indanegas@okicici", "Indane Gas"), ("more-supermarket@okhdfcbank", "More Supermarket"),
]

SCAM_TYPES: dict[str, dict[str, Any]] = {
    "digital_arrest": {
        "label": "Digital arrest / fake authority",
        "amount_range": (25000, 750000), "lead_minutes": (25, 240),
        "new_payee_p": 0.97, "call_p": 0.95, "fd_break_p": 0.45, "loan_p": 0.35,
        "channels": ["voice_call", "video_call", "voice_call"],
        "ask": "Transfer to a 'safe account' for verification",
        "identity": "Police / CBI / ED / customs officer",
    },
    "utility_bill": {
        "label": "Fake utility bill disconnection",
        "amount_range": (900, 9500), "lead_minutes": (6, 55),
        "new_payee_p": 0.9, "call_p": 0.8, "fd_break_p": 0.02, "loan_p": 0.01,
        "channels": ["voice_call", "sms", "whatsapp"],
        "ask": "Immediate payment to avoid power/water disconnection",
        "identity": "Electricity / water department",
    },
    "kyc_sim": {
        "label": "KYC / SIM block",
        "amount_range": (500, 6000), "lead_minutes": (8, 75),
        "new_payee_p": 0.88, "call_p": 0.45, "fd_break_p": 0.01, "loan_p": 0.0,
        "channels": ["sms", "whatsapp", "voice_call"],
        "ask": "KYC update fee to keep SIM/account active",
        "identity": "Bank KYC officer / TRAI / telecom operator",
    },
    "task_investment": {
        "label": "Task / investment scam",
        "amount_range": (4000, 250000), "lead_minutes": (120, 2880),
        "new_payee_p": 0.92, "call_p": 0.2, "fd_break_p": 0.4, "loan_p": 0.4,
        "channels": ["whatsapp", "telegram", "sms"],
        "ask": "Task deposit / investment top-up with promised returns",
        "identity": "HR recruiter / investment advisor",
    },
    "relative_impersonation": {
        "label": "Impersonated relative",
        "amount_range": (3000, 60000), "lead_minutes": (3, 45),
        "new_payee_p": 0.7, "call_p": 0.9, "fd_break_p": 0.15, "loan_p": 0.1,
        "channels": ["voice_call", "voice_call", "sms"],
        "ask": "Emergency money for a stuck relative / friend",
        "identity": "Son / daughter / nephew / friend in trouble",
    },
    # Drift variant: fake court e-summons / traffic e-challan demand (appears late in timeline).
    "e_challan_summons": {
        "label": "E-challan / court e-summons (new variant)",
        "amount_range": (700, 4200), "lead_minutes": (15, 180),
        "new_payee_p": 0.93, "call_p": 0.6, "fd_break_p": 0.0, "loan_p": 0.0,
        "channels": ["sms", "whatsapp"],
        "ask": "Pay e-challan / court fine online to avoid arrest warrant",
        "identity": "Traffic police / court e-summons portal",
    },
}

STAGES = ["contact", "authority_claim", "urgency", "payment_request", "payment", "follow_up"]

SCRIPTS: dict[str, dict[str, list[str]]] = {
    "digital_arrest": {
        "en": [
            "This is CBI officer {name}. A parcel with drugs and fake passports was seized in your name. You are under digital arrest. Stay on the call.",
            "I am inspector from CBI cyber cell. Your Aadhaar is linked to a money laundering case. Cooperate and follow instructions.",
            "Customs department here. Your courier from Mumbai contains illegal items. Transfer money to the verification account immediately.",
        ],
        "hi": [
            "मैं CBI अधिकारी {name} बोल रहा हूँ। आपके नाम से ड्रग्स वाला पार्सल पकड़ा गया है। आप डिजिटल अरेस्ट में हैं। कॉल पर बने रहें।",
            "यह कस्टम डिपार्टमेंट है। आपके आधार से मनी लॉन्ड्रिंग केस जुड़ा है। तुरंत पैसे वेरिफिकेशन अकाउंट में भेजें।",
        ],
        "hinglish": [
            "Main CBI se {name} bol raha hoon. Aapke naam ka parcel pakda gaya hai. Aap digital arrest me ho. Line pe bane raho.",
            "Ye customs department hai. Aapka Aadhaar case me linked hai. Jaldi se safe account me paise transfer karo warna warrant aa jayega.",
        ],
    },
    "utility_bill": {
        "en": [
            "Your electricity connection will be disconnected tonight at 9:30 PM. Pay the pending amount of Rs 2,847 immediately to avoid disconnection.",
            "This is the power department. Your meter update is pending. Pay Rs 1,999 now or your line will be cut within two hours.",
        ],
        "hi": [
            "आपका बिजली कनेक्शन आज रात 9:30 पर कट जाएगा। बकाया ₹2,847 तुरंत जमा करें वरना कनेक्शन काट दिया जाएगा।",
            "यह बिजली विभाग है। आज रात आपका कनेक्शन डिस्कनेक्ट होगा। अभी भुगतान करें।",
        ],
        "hinglish": [
            "Aapka bijli connection aaj raat 9:30 pe cut ho jayega. ₹2,847 pending hai. Turant pay karo, warna disconnection ho jayega.",
            "Bijli department se bol raha hoon. Aaj raat connection disconnect hoga. Abhi payment karo warna kal se meter nahi chalega.",
        ],
    },
    "kyc_sim": {
        "en": [
            "Your KYC is expired. Your SIM and bank account will be blocked within 24 hours. Pay the KYC fee of Rs 3,500 to continue service.",
            "TRAI notice: your mobile number will be deactivated today. Update KYC immediately by paying the verification charge.",
        ],
        "hi": [
            "आपकी KYC एक्सपायर हो गई है। आपका SIM और बैंक खाता 24 घंटे में ब्लॉक हो जाएगा। KYC शुल्क ₹3,500 अभी भुगतान करें।",
            "TRAI नोटिस: आपका मोबाइल नंबर आज बंद होगा। तुरंत KYC अपडेट करें।",
        ],
        "hinglish": [
            "Aapki KYC expire ho gayi hai. Aapka SIM aur bank account 24 ghante me block ho jayega. ₹3,500 KYC fee turant pay karo.",
            "TRAI notice: aapka number aaj deactivate ho jayega. KYC update karne ke liye verification charge pay karo.",
        ],
    },
    "task_investment": {
        "en": [
            "Congratulations! You are selected for a part-time work-from-home task. Deposit Rs 9,000 and earn Rs 18,000 in 3 days. Limited slots.",
            "Join our VIP investment plan. Deposit Rs 25,000 today, get 200% returns by Friday. Withdrawal screenshot attached.",
        ],
        "hi": [
            "बधाई हो! आप work-from-home टास्क के लिए चुने गए हैं। ₹9,000 जमा करें और 3 दिन में ₹18,000 कमाएँ। सीमित सीटें।",
            "हमारे VIP निवेश प्लान से जुड़ें। आज ₹25,000 निवेश करें, शुक्रवार तक 200% रिटर्न।",
        ],
        "hinglish": [
            "Congrats! Aap work-from-home task ke liye select ho gaye ho. ₹9,000 deposit karo aur 3 din me ₹18,000 kamao. Slots limited hain.",
            "VIP investment plan join karo. Aaj ₹25,000 invest karo, Friday tak 200% returns. Withdrawal screenshot laga hai.",
        ],
    },
    "relative_impersonation": {
        "en": [
            "Papa, it's Rahul. I met with an accident, my phone will switch off. Please send Rs 30,000 to this UPI ID urgently, the hospital needs it.",
            "Sis, I am stuck at the police station. Rs 15,000 will fix everything. Send it now, I will call later.",
        ],
        "hi": [
            "पापा, मैं राहुल बोल रहा हूँ। मेरा एक्सीडेंट हो गया है, फोन बंद हो जाएगा। हॉस्पिटल को ₹30,000 इस UPI पर भेजो।",
            "भैया, पुलिस स्टेशन में हूँ। ₹15,000 भेजो, सब ठीक हो जाएगा।",
        ],
        "hinglish": [
            "Papa main Rahul bol raha hoon. Accident ho gaya, phone band hone wala hai. ₹30,000 is UPI pe jaldi bhejo.",
            "Bhai main police station me hoon, challan ho gaya hai. ₹15,000 yahan bhej do, jaldi bhejo please.",
        ],
    },
    "e_challan_summons": {
        "en": [
            "E-summons from traffic court. Case PC-2026-88412 against your vehicle. Pay fine Rs 1,850 within 2 hours at the link to avoid warrant.",
            "Court notice: unpaid e-challan Rs 2,400. Non-payment will result in arrest warrant. Pay now via UPI to the court portal.",
        ],
        "hi": [
            "ट्रैफिक कोर्ट से ई-सम्मन। आपके वाहन के विरुद्ध केस। 2 घंटे में ₹1,850 जुर्माना भरें वरना वारंट जारी होगा।",
        ],
        "hinglish": [
            "Traffic court se e-summons aaya hai. Aapke vehicle ka case hai. 2 ghante me ₹1,850 fine bharo, warna warrant nikal jayega.",
        ],
    },
}

FOLLOW_UPS = {
    "digital_arrest": "Do not tell anyone about this call. Complete the verification and stay on video call.",
    "utility_bill": "Send the payment screenshot on this number. The line will be restored shortly.",
    "kyc_sim": "Your KYC is complete. Do not press any more links sent to this phone.",
    "task_investment": "Welcome aboard. Complete the next task to unlock your earnings.",
    "relative_impersonation": "Thank you papa, I will call back from a different number.",
    "e_challan_summons": "Payment received. Case PC-2026-88412 is closed. Do not share this link again.",
}

URGENCY_WORDS = ["urgent", "immediately", "right now", "within", "minutes", "today", "now", "hurry",
                 "turant", "jaldi", "abhi", "aaj", "तुरंत", "जल्दी", "अभी"]
AUTHORITY_WORDS = ["police", "cbi", "ed", "court", "customs", "department", "officer", "kyc", "trai",
                   "aadhaar", "warrant", "summons", "notice", "अधिकारी", "पुलिस", "विभाग"]
THREAT_WORDS = ["arrest", "warrant", "jail", "disconnect", "block", "fine", "case", "deactivate",
                "disconnection", "गिरफ्तार", "ब्लॉक", "बंद"]

HARD_NEGATIVE_KINDS = ["rent_deposit", "medical_emergency", "genuine_bank_call", "family_transfer", "tuition_fee"]


def load_config() -> dict[str, Any]:
    cfg = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    override = os.environ.get("SIM_CONFIG")
    if override:
        cfg.update(json.loads(Path(override).read_text(encoding="utf-8")))
    return cfg


def text_risk_scores(text: str) -> tuple[float, float, float]:
    t = text.lower()
    urg = min(1.0, 0.2 * sum(1 for w in URGENCY_WORDS if w in t) + (0.25 if any(w in t for w in ["within", "तुरंत", "turant"]) else 0))
    auth = min(1.0, 0.2 * sum(1 for w in AUTHORITY_WORDS if w in t))
    threat = min(1.0, 0.2 * sum(1 for w in THREAT_WORDS if w in t))
    return round(urg, 3), round(auth, 3), round(threat, 3)


def _log_amount(rng: np.random.Generator, lo: float, hi: float) -> float:
    return round(math.exp(rng.uniform(math.log(lo), math.log(hi))), 2)


def _iso(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%S")


class _PayeeBook:
    """Lazily creates payees; caches handles to ids."""

    def __init__(self, rng: np.random.Generator) -> None:
        self._cache: dict[str, int] = {}
        self._next_id = 1
        self._rng = rng
        self.mule_handles: list[str] = []

    def get_or_create(self, conn: sqlite3.Connection, handle: str, name: str, ts: str,
                      prior_reports: int = 0, is_scam_payee: bool = False) -> int:
        prior_reports = int(prior_reports)
        if handle in self._cache:
            pid = self._cache[handle]
            if prior_reports and is_scam_payee:
                # scam payees accumulate reports; legit merchants keep their one-time value
                conn.execute("UPDATE payees SET prior_reports = MIN(9, prior_reports + ?) WHERE id = ?", (prior_reports, pid))
            return pid
        pid = self._next_id
        self._next_id += 1
        conn.execute(
            "INSERT INTO payees(id, handle, name, first_seen, prior_reports, fan_in, is_synthetic_scam) VALUES (?,?,?,?,?,0,?)",
            (pid, handle, name, ts, prior_reports, 1 if is_scam_payee else 0),
        )
        self._cache[handle] = pid
        return pid

    def mule_payee(self, conn: sqlite3.Connection, ts: str) -> int:
        if self.mule_handles and self._rng.random() < 0.55:
            handle = self._rng.choice(self.mule_handles)
            return self.get_or_create(conn, handle, "Quick Settlements Services", ts, prior_reports=1, is_scam_payee=True)
        idx = len(self.mule_handles) + 1
        handle = f"settlement.desk{5000 + idx}@okicici"
        self.mule_handles.append(handle)
        prior = 0 if self._rng.random() < 0.25 else int(self._rng.integers(1, 6))
        return self.get_or_create(conn, handle, "Quick Settlements Services", ts, prior_reports=prior, is_scam_payee=True)


def _weighted_hour(rng: np.random.Generator, start_h: int, end_h: int) -> int:
    if start_h <= end_h:
        return int(rng.integers(start_h, end_h + 1))
    hours = list(range(start_h, 24)) + list(range(0, end_h + 1))
    return int(rng.choice(hours))


def generate(conn: sqlite3.Connection, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    rng = np.random.default_rng(cfg["seed"])
    start = datetime.strptime(cfg["start_date"], "%Y-%m-%d")
    days: int = cfg["days"]

    db.init_db(conn)
    db.wipe(conn)

    # ---------- users ----------
    users: list[dict[str, Any]] = []
    for uid in range(1, cfg["users"] + 1):
        seg = str(rng.choice(SEGMENTS, p=[0.32, 0.17, 0.12, 0.12, 0.17, 0.10]))
        if uid == 1:  # deterministic demo user
            name, seg = cfg["demo_user_name"], "retired"
        else:
            name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        avg = SEGMENT_AVG[seg] * float(rng.uniform(0.6, 1.6))
        users.append({
            "id": uid, "name": name, "segment": seg, "city": str(rng.choice(CITIES)),
            "avg_amount": round(avg, 2), "amount_stddev": round(avg * float(rng.uniform(0.35, 0.7)), 2),
            "monthly_frequency": SEGMENT_FREQ[seg] * float(rng.uniform(0.7, 1.4)),
            "hour_start": int(rng.choice([6, 7, 8])), "hour_end": int(rng.choice([20, 21, 22])),
            "device_os": str(rng.choice(["android", "android", "android", "ios"])),
            "device_age_months": int(rng.integers(2, 60)),
            "biometric_enabled": int(rng.random() < 0.55),
            "has_fd": int(rng.random() < 0.42),
            "fd_amount": round(float(_log_amount(rng, 50000, 1500000)), 2),
            "credit_limit": float(round(rng.uniform(20000, 600000), -3)),
            "created_at": _iso(start - timedelta(days=int(rng.integers(30, 900)))),
        })

    # ---------- insert users (payments reference them) ----------
    conn.executemany(
        """INSERT INTO users(id, name, segment, city, avg_amount, amount_stddev, monthly_frequency,
           hour_start, hour_end, device_os, device_age_months, biometric_enabled, has_fd, fd_amount, credit_limit, created_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        [(u["id"], u["name"], u["segment"], u["city"], u["avg_amount"], u["amount_stddev"], u["monthly_frequency"],
          u["hour_start"], u["hour_end"], u["device_os"], u["device_age_months"], u["biometric_enabled"],
          u["has_fd"], u["fd_amount"], u["credit_limit"], u["created_at"]) for u in users],
    )

    # ---------- payments (legit pass) ----------
    payee_book = _PayeeBook(rng)
    payment_rows: list[dict[str, Any]] = []
    regular_payees: dict[int, list[int]] = {}

    def regular_payee_for(user: dict[str, Any], ts: str) -> tuple[int, bool]:
        uid = user["id"]
        if uid not in regular_payees:
            k = int(rng.integers(2, 7))
            chosen = rng.choice(len(PAYEE_POOL), size=k, replace=False)
            ids = []
            for c in chosen:
                h, n = PAYEE_POOL[int(c)]
                prior = int(rng.integers(1, 4)) if rng.random() < 0.06 else 0  # false reports exist on legit merchants
                ids.append(payee_book.get_or_create(conn, h, n, ts, prior_reports=prior))
            regular_payees[uid] = ids
        return int(rng.choice(regular_payees[uid])), False

    for user in users:
        n = max(4, int(rng.poisson(user["monthly_frequency"] * days / 30.0)))
        for _ in range(n):
            day = int(rng.integers(0, days))
            hour = _weighted_hour(rng, user["hour_start"], user["hour_end"])
            minute = int(rng.integers(0, 60))
            ts_dt = start + timedelta(days=day, hours=hour, minutes=minute)
            ts = _iso(ts_dt)

            amount = _log_amount(rng, user["avg_amount"] * 0.25, user["avg_amount"] * 4)
            hard_kind = None
            r = rng.random()
            if r < cfg["hard_negative_rate"]:
                hard_kind = str(rng.choice(HARD_NEGATIVE_KINDS))
            if hard_kind == "rent_deposit":
                amount = round(float(rng.uniform(15000, 38000)), 2)
            elif hard_kind == "medical_emergency":
                amount = round(float(rng.uniform(8000, 95000)), 2)
            elif hard_kind == "family_transfer":
                amount = round(float(rng.uniform(10000, 60000)), 2)
            elif hard_kind == "tuition_fee":
                amount = round(float(rng.uniform(20000, 120000)), 2)

            new_payee_p = {"rent_deposit": 0.5, "medical_emergency": 0.65, "family_transfer": 0.45,
                           "tuition_fee": 0.6, "genuine_bank_call": 0.05}.get(hard_kind or "", 0.08)
            is_new = rng.random() < new_payee_p
            if is_new:
                handle = f"{str(rng.choice(['life', 'quick', 'city', 'star', 'metro']))}-pay{int(rng.integers(1000, 9999))}@oksbi"
                pid = payee_book.get_or_create(conn, handle, f"Merchant {handle.split('@')[0]}", ts,
                                                prior_reports=int(rng.integers(1, 3)) if rng.random() < 0.05 else 0)
            else:
                pid, _ = regular_payee_for(user, ts)

            call_active = 1 if hard_kind == "genuine_bank_call" else (1 if rng.random() < (0.3 if hard_kind == "medical_emergency" else 0.04) else 0)
            payment_rows.append({
                "user_id": user["id"], "payee_id": pid, "ts": ts, "day_index": day,
                "amount": amount, "call_active": call_active,
                "app_switches": int(rng.poisson(1.1)),
                "hesitation_secs": int(np.clip(rng.gamma(3.0, 4.0), 3, 90)),
                "is_new_payee": int(is_new), "is_scam": 0, "scam_type": None, "scam_run_id": None,
                "hard_negative": int(hard_kind is not None), "hard_negative_kind": hard_kind, "is_demo": 0,
            })

    payment_rows.sort(key=lambda p: p["ts"])

    # ---------- choose scam slots ----------
    n_total = len(payment_rows)
    n_scam = int(n_total * cfg["scam_rate"])
    scam_idx = rng.choice(n_total, size=n_scam, replace=False)
    weights = cfg["scam_type_weights"]
    w_arr = np.array(list(weights.values()))
    w_arr = w_arr / w_arr.sum()
    scam_runs: list[tuple[int, str]] = []
    for i in scam_idx:
        day = payment_rows[i]["day_index"]
        if day >= cfg["drift_start_day"] and rng.random() < cfg["new_variant_weight"]:
            stype = "e_challan_summons"
        else:
            stype = str(rng.choice(list(weights), p=w_arr))
        scam_runs.append((int(i), stype))

    scam_events: list[dict[str, Any]] = []
    behavior_events: list[dict[str, Any]] = []
    run_no = 0
    for idx, stype in scam_runs:
        run_no += 1
        spec = SCAM_TYPES[stype]
        p = payment_rows[idx]
        run_id = f"RUN-{run_no:05d}"
        pay_ts = datetime.strptime(p["ts"], "%Y-%m-%dT%H:%M:%S")
        lead = float(rng.uniform(*spec["lead_minutes"]))
        contact_ts = pay_ts - timedelta(minutes=lead)

        # Scam payee: 45% chance it is a re-used mule handle (fan-in signal).
        if rng.random() < 0.45:
            pid = payee_book.mule_payee(conn, p["ts"])
        else:
            handle = f"quick-settle{int(rng.integers(10000, 99999))}@okicici"
            prior = 0 if rng.random() < 0.25 else int(rng.integers(1, 7))
            pid = payee_book.get_or_create(conn, handle, "Quick Settlements Services", p["ts"],
                                            prior_reports=prior, is_scam_payee=True)
        p.update({
            "payee_id": pid,
            "amount": _log_amount(rng, *spec["amount_range"]),
            "is_new_payee": int(rng.random() < spec["new_payee_p"]),
            "call_active": int(rng.random() < spec["call_p"]),
            "app_switches": int(rng.poisson(7) + 3),
            "hesitation_secs": int(rng.integers(3, 15)),
            "is_scam": 1, "scam_type": stype, "scam_run_id": run_id, "hard_negative": 0, "hard_negative_kind": None,
        })

        if rng.random() < cfg["missing_text_rate"]:
            continue  # text unavailable (missing signal)
        lang = str(rng.choice(["hinglish", "hi", "en"], p=[0.45, 0.25, 0.30]))
        n_officer = str(rng.integers(1000, 9999))
        script_bank = SCRIPTS[stype]
        variants = script_bank.get(lang) or script_bank["en"]
        base_text = str(rng.choice(variants)).replace("{name}", n_officer)
        channel = str(rng.choice(spec["channels"]))

        def ev(stage: str, frac: float, text: str) -> None:
            st = contact_ts + timedelta(minutes=lead * frac)
            scam_events.append({"run": run_id, "stage": stage, "ts": _iso(st), "channel": channel, "lang": lang, "text": text})

        ev("contact", 0.0, base_text)
        ev("authority_claim", 0.35, f"{spec['identity']}. Verified ID badge shown on call." if lang == "en" else f"{spec['identity']} की ओर से फ़ोन। आईडी कार्ड दिखाया गया।")
        ev("urgency", 0.65, "You must act now. Do not disconnect the call. Time is running out." if lang == "en" else "अभी तुरंत कार्रवाई करें। कॉल मत काटिए। समय समाप्त हो रहा है।")
        ev("payment_request", 0.85, f"{spec['ask']}. Amount must be paid right now.")
        ev("payment", 1.0, f"Payment of Rs {p['amount']:.2f} confirmed on UPI.")
        scam_events.append({"run": run_id, "stage": "follow_up",
                            "ts": _iso(pay_ts + timedelta(minutes=int(rng.integers(1, 25)))),
                            "channel": channel, "lang": lang, "text": FOLLOW_UPS[stype]})

    # ---------- inject the deterministic demo payment ----------
    demo_dt = start + timedelta(days=days - 2, hours=10, minutes=24)
    demo_user = users[0]
    pid_demo = payee_book.get_or_create(conn, "bijli-helpdesk9917@okicici", "Bijli Vibhag Helpline", _iso(demo_dt),
                                        prior_reports=6, is_scam_payee=True)
    demo_row = {
        "user_id": demo_user["id"], "payee_id": pid_demo, "ts": _iso(demo_dt), "day_index": days - 2,
        "amount": float(cfg["demo_amount"]), "call_active": 1, "app_switches": 9,
        "hesitation_secs": 6, "is_new_payee": 1, "is_scam": 1, "scam_type": "utility_bill",
        "scam_run_id": "RUN-DEMO-001", "hard_negative": 0, "hard_negative_kind": None, "is_demo": 1,
    }
    payment_rows.append(demo_row)
    payment_rows.sort(key=lambda r: r["ts"])

    # ---------- insert payments ----------
    conn.executemany(
        """INSERT INTO payments(id, user_id, payee_id, ts, day_index, amount, channel, call_active,
           app_switches, hesitation_secs, is_new_payee, is_scam, scam_type, scam_run_id,
           hard_negative, hard_negative_kind, is_demo)
           VALUES (?,?,?,?,?,?,'UPI',?,?,?,?,?,?,?,?,?,?)""",
        [(i + 1, r["user_id"], r["payee_id"], r["ts"], r["day_index"], r["amount"], r["call_active"],
          r["app_switches"], r["hesitation_secs"], r["is_new_payee"], r["is_scam"], r["scam_type"],
          r["scam_run_id"], r["hard_negative"], r["hard_negative_kind"], r["is_demo"]) for i, r in enumerate(payment_rows)],
    )
    run_to_payment_id = {r["scam_run_id"]: i + 1 for i, r in enumerate(payment_rows) if r["scam_run_id"]}

    # ---------- scam events ----------
    for ev_row in scam_events:
        pid = run_to_payment_id.get(ev_row["run"])
        if pid is None:
            continue
        conn.execute(
            "INSERT INTO scam_events(payment_id, stage, ts, channel, lang, text) VALUES (?,?,?,?,?,?)",
            (pid, ev_row["stage"], ev_row["ts"], ev_row["channel"], ev_row["lang"], ev_row["text"]),
        )

    # demo scam script (deterministic, matches README story)
    demo_pid = run_to_payment_id["RUN-DEMO-001"]
    demo_events = [
        ("contact", demo_dt - timedelta(minutes=11), "voice_call", "hinglish",
         "Bijli department se bol raha hoon. Aapka bijli connection aaj raat 9:30 pe cut ho jayega. ₹80,000 pending amount hai."),
        ("authority_claim", demo_dt - timedelta(minutes=8), "voice_call", "hinglish",
         "Bijli Vibhag, Lucknow. Officer badge number LV-2211. Aapka meter update pending hai."),
        ("urgency", demo_dt - timedelta(minutes=5), "voice_call", "hinglish",
         "Abhi payment nahi kiya to connection turant disconnect ho jayega. Jalbil se ID proof bhi verification ke liye chahiye."),
        ("payment_request", demo_dt - timedelta(minutes=2), "voice_call", "hinglish",
         "Mujhe ₹80,000 is UPI ID pe transfer karna hoga. Screenshot bhejna payment ke baad."),
        ("payment", demo_dt, "voice_call", "hinglish",
         "Payment of Rs 80,000.00 confirmed on UPI. Ref UTR-904125588213."),
        ("follow_up", demo_dt + timedelta(minutes=3), "sms", "hinglish",
         "Bijli Vibhag: payment received. Line restored. Report number LV-2211-OK."),
    ]
    for stage, ts, channel, lang, text in demo_events:
        conn.execute(
            "INSERT INTO scam_events(payment_id, stage, ts, channel, lang, text) VALUES (?,?,?,?,?,?)",
            (demo_pid, stage, _iso(ts), channel, lang, text),
        )

    # ---------- behaviour events ----------
    def add_behavior(payment_id: int, kind: str, ts_dt: datetime, detail: str = "") -> None:
        behavior_events.append({"payment_id": payment_id, "kind": kind, "ts": _iso(ts_dt), "detail": detail})

    for i, r in enumerate(payment_rows):
        pid = i + 1
        p_dt = datetime.strptime(r["ts"], "%Y-%m-%dT%H:%M:%S")
        if r["is_scam"]:
            # Financial mobilisation often precedes the transfer.
            stype = r["scam_type"]
            if stype and rng.random() < SCAM_TYPES[stype]["fd_break_p"]:
                add_behavior(pid, "fd_break", p_dt - timedelta(minutes=int(rng.integers(30, 600))),
                             f"FD broken early; penalty applied. Amount ~ FD.")
            if stype and rng.random() < SCAM_TYPES[stype]["loan_p"]:
                add_behavior(pid, "loan_taken", p_dt - timedelta(minutes=int(rng.integers(60, 720))),
                             "Instant personal loan disbursed to account.")
            if rng.random() < cfg["non_realization_rate"]:
                continue  # victim shows no distress (non-realization) ~30%
            for _ in range(int(rng.integers(1, 7))):
                add_behavior(pid, "balance_check", p_dt + timedelta(minutes=int(rng.integers(1, 45))), "Balance inquiry")
            if rng.random() < 0.6:
                add_behavior(pid, "reversal_search", p_dt + timedelta(minutes=int(rng.integers(2, 40))),
                             "Searched 'how to reverse UPI payment' / visited help page")
            if rng.random() < 0.5:
                add_behavior(pid, "support_contact", p_dt + timedelta(minutes=int(rng.integers(8, 62))),
                             "Contacted bank customer care / 1930")
            if rng.random() < 0.7:
                add_behavior(pid, "payee_contact_failed", p_dt + timedelta(minutes=int(rng.integers(15, 120))),
                             "Payee number unreachable / invalid")
        elif r["hard_negative_kind"] == "medical_emergency" and rng.random() < 0.75:
            if rng.random() < 0.3:
                add_behavior(pid, "fd_break", p_dt - timedelta(minutes=int(rng.integers(120, 2000))), "FD broken for hospital deposit")
            if rng.random() < 0.2:
                add_behavior(pid, "loan_taken", p_dt - timedelta(minutes=int(rng.integers(120, 2000))), "Instant loan for treatment")
            for _ in range(int(rng.integers(2, 5))):
                add_behavior(pid, "balance_check", p_dt + timedelta(minutes=int(rng.integers(1, 50))), "Balance inquiry")
            if rng.random() < 0.6:
                add_behavior(pid, "support_contact", p_dt + timedelta(minutes=int(rng.integers(5, 40))), "Called hospital billing desk")
            if rng.random() < 0.15:
                add_behavior(pid, "payee_contact_failed", p_dt + timedelta(minutes=int(rng.integers(20, 150))), "Pharmacy counter did not answer")
        elif r["hard_negative_kind"] == "family_transfer" and rng.random() < 0.4:
            if rng.random() < 0.15:
                add_behavior(pid, "fd_break", p_dt - timedelta(minutes=int(rng.integers(120, 2000))), "FD broken for family need")
            for _ in range(int(rng.integers(1, 4))):
                add_behavior(pid, "balance_check", p_dt + timedelta(minutes=int(rng.integers(1, 40))), "Balance inquiry")
            if rng.random() < 0.25:
                add_behavior(pid, "support_contact", p_dt + timedelta(minutes=int(rng.integers(5, 45))), "Called to confirm receipt")
        elif r["hard_negative_kind"] == "rent_deposit" and rng.random() < 0.3:
            add_behavior(pid, "balance_check", p_dt + timedelta(minutes=int(rng.integers(1, 30))), "Balance inquiry")
        elif r["hard_negative_kind"] == "genuine_bank_call" and rng.random() < 0.15:
            add_behavior(pid, "support_contact", p_dt + timedelta(minutes=int(rng.integers(10, 90))), "Called bank branch to verify")
        elif r["hard_negative_kind"] == "tuition_fee" and rng.random() < 0.15:
            add_behavior(pid, "loan_taken", p_dt - timedelta(minutes=int(rng.integers(120, 2000))), "Education loan for fees")
        elif rng.random() < 0.05:
            add_behavior(pid, "balance_check", p_dt + timedelta(minutes=int(rng.integers(1, 60))), "Balance inquiry")
            if rng.random() < 0.1:
                add_behavior(pid, "reversal_search", p_dt + timedelta(minutes=int(rng.integers(3, 35))), "Searched payment reversal after fat-fingering payee")

    # Demo payment always shows distress behaviour.
    for kind, mins, detail in [("balance_check", 2, "Balance inquiry"), ("balance_check", 4, "Balance inquiry"),
                               ("balance_check", 6, "Balance inquiry (3rd check)"),
                               ("reversal_search", 7, "Searched 'UPI payment reverse kaise kare'"),
                               ("support_contact", 9, "Called 1930 cyber helpline, kept on hold"),
                               ("payee_contact_failed", 12, "Payee number 'switched off'")]:
        add_behavior(demo_pid, kind, demo_dt + timedelta(minutes=mins), detail)

    conn.executemany(
        "INSERT INTO behavior_events(payment_id, kind, ts, detail) VALUES (?,?,?,?)",
        [(b["payment_id"], b["kind"], b["ts"], b["detail"]) for b in behavior_events],
    )

    # ---------- payee fan-in ----------
    conn.execute("""UPDATE payees SET fan_in = (
        SELECT COUNT(DISTINCT user_id) FROM payments WHERE payments.payee_id = payees.id)""")

    db.set_meta(conn, "seed", json.dumps({"users": cfg["users"], "payments": len(payment_rows),
                                          "scams": sum(1 for r in payment_rows if r["is_scam"]),
                                          "start_date": cfg["start_date"], "days": days,
                                          "seed": cfg["seed"]}))
    conn.commit()
    return {"users": len(users), "payments": len(payment_rows),
            "scams": sum(1 for r in payment_rows if r["is_scam"]),
            "demo_payment_id": demo_pid}
