"""Cluster scam-related text into emerging-scam templates with novelty scores."""
from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .simulator import SCAM_TYPES, STAGES

APPROVED_SEED = [
    ("digital_arrest", "Digital arrest — fake CBI / customs / ED", "police|cbi|ed|customs|arrest|digital arrest|warrant|aadhaar",
     "Transfer to a 'safe account' for verification", "voice_call"),
    ("utility_bill", "Fake electricity / water disconnection", "electricity|bijli|power|disconnection|meter|pending",
     "Immediate payment to avoid power/water disconnection", "voice_call"),
    ("kyc_sim", "KYC / SIM block", "kyc|sim|trai|aadhaar|block|deactivate|verification",
     "KYC update fee to keep SIM/account active", "sms"),
    ("task_investment", "Task / investment returns", "task|invest|vip|returns|deposit|work-from-home|earnings",
     "Task deposit / investment top-up with promised returns", "whatsapp"),
    ("relative_impersonation", "Impersonated relative / friend", "papa|friend|son|accident|hospital|police station|bhej",
     "Emergency money for a stuck relative or friend", "voice_call"),
]

IDENTITY_RULES = [
    (re.compile(r"police|cbi|ed\b|customs|court|summons|challan|warrant", re.I), "Police / CBI / customs / court"),
    (re.compile(r"electricity|bijli|power|meter|water|jal\b", re.I), "Electricity / water department"),
    (re.compile(r"kyc|sim|trai|aadhaar|bank", re.I), "Bank / TRAI KYC officer"),
    (re.compile(r"task|invest|vip|return|deposit|earn|work-from-home|job", re.I), "Recruiter / investment advisor"),
    (re.compile(r"papa|friend|son|daughter|relative|accident|hospital|bhej", re.I), "Impersonated relative / friend"),
]

ASK_RULES = [
    (re.compile(r"safe account|verification account|verify.*account", re.I), "Urgent transfer to a 'safe' verification account"),
    (re.compile(r"kyc", re.I), "KYC update / verification fee"),
    (re.compile(r"task|deposit.*return|earn", re.I), "Task deposit / investment top-up"),
    (re.compile(r"disconnect|meter|electricity|bijli|pending", re.I), "Utility bill payment to avoid disconnection"),
    (re.compile(r"accident|hospital|papa|bhej", re.I), "Emergency family transfer"),
    (re.compile(r"challan|fine|summons|court", re.I), "E-challan / court fine payment"),
]


def _identity(texts: list[str]) -> str:
    joined = " ".join(texts)
    for rx, label in IDENTITY_RULES:
        if rx.search(joined):
            return label
    return "Unknown / mixed identity"


def _ask(texts: list[str]) -> str:
    joined = " ".join(texts)
    for rx, label in ASK_RULES:
        if rx.search(joined):
            return label
    return "Unspecified payment ask"


def _urgency_cue(texts: list[str]) -> str:
    cue_words = ["immediately", "within", "urgent", "today", "now", "turant", "jaldi", "abhi", "aaj", "तुरंत", "अभी"]
    joined = " ".join(texts).lower()
    hits = [w for w in cue_words if w in joined]
    return ", ".join(hits[:4]) if hits else "Implicit time pressure"


def _seed_approved(conn: sqlite3.Connection, now: str) -> None:
    conn.execute("DELETE FROM templates")
    for scam_type, name, terms, ask, channel in APPROVED_SEED:
        spec = SCAM_TYPES[scam_type]
        count = conn.execute("SELECT COUNT(*) c FROM payments WHERE scam_type = ?", (scam_type,)).fetchone()["c"]
        samples = [t[0] for t in conn.execute(
            """SELECT e.text FROM scam_events e JOIN payments p ON p.id = e.payment_id
               WHERE p.scam_type = ? AND e.stage = 'contact' ORDER BY e.id LIMIT 40""", (scam_type,))]
        stages = json.dumps(STAGES)
        conn.execute(
            """INSERT INTO templates(name, scam_type, hook, claimed_identity, urgency_cue, payment_ask, channel,
               stages, script_samples, top_terms, novelty_score, status, size, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,0.0,'approved',?,?)""",
            (name, scam_type, f"Hook: {', '.join(terms.split('|')[:4])}", spec["identity"], "seeded cue",
             ask, channel, stages, json.dumps(samples), json.dumps(terms.split("|")), int(count), now),
        )
    conn.commit()


def build(conn: sqlite3.Connection, n_clusters: int = 10, novelty_threshold: float = 0.55) -> dict[str, Any]:
    now = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    _seed_approved(conn, now)

    rows = pd.read_sql_query(
        """SELECT e.payment_id, e.text, e.channel, e.stage, p.scam_type FROM scam_events e
           JOIN payments p ON p.id = e.payment_id""", conn)
    if rows.empty:
        return {"clusters": 0, "proposed": 0}

    docs = rows.groupby("payment_id")["text"].apply(lambda s: " ".join(s)).reset_index()
    meta = rows.groupby("payment_id").agg(scam_type=("scam_type", "first"), channel=("channel", lambda s: s.mode().iloc[0])).reset_index()
    docs = docs.merge(meta, on="payment_id")

    vec = TfidfVectorizer(max_features=3000, ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    X = vec.fit_transform(docs["text"])
    k = min(n_clusters, max(2, len(docs) // 25))
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X)

    # approved-template centroids for novelty: use approved template texts as reference corpus
    approved = pd.read_sql_query("SELECT id, script_samples, top_terms FROM templates WHERE status = 'approved'", conn)
    approved_refs = []
    for _, t in approved.iterrows():
        samples = json.loads(t["script_samples"])
        terms = " ".join(json.loads(t["top_terms"]))
        approved_refs.append(" ".join(samples) + " " + terms)
    ref_vec = vec.transform(approved_refs)

    feature_names = np.array(vec.get_feature_names_out())
    proposed = 0
    centroids: list[np.ndarray] = []
    for c in range(k):
        mask = labels == c
        members = docs[mask]
        size = int(mask.sum())
        if size < 8:
            continue
        texts = members["text"].tolist()
        centroid = np.asarray(X[mask].mean(axis=0))
        centroids.append(centroid)
        sims = cosine_similarity(centroid, ref_vec)[0]
        max_sim = float(sims.max()) if len(sims) else 0.0
        novelty = round(1.0 - max_sim, 4)
        dom_type = members["scam_type"].mode().iloc[0]
        top_idx = centroid.ravel().argsort()[::-1][:14]
        top_terms = [feature_names[i] for i in top_idx if centroid.ravel()[i] > 0]
        channel = members["channel"].mode().iloc[0]
        samples = texts[:4]
        if novelty >= novelty_threshold:
            status, name = "proposed", f"Emerging pattern #{c + 1} ({dom_type or 'unknown'})"
            proposed += 1
            conn.execute(
                """INSERT INTO templates(name, scam_type, hook, claimed_identity, urgency_cue, payment_ask, channel,
                   stages, script_samples, top_terms, novelty_score, status, size, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (name, dom_type or "unknown",
                 f"Hook: {', '.join(top_terms[:4])}", _identity(texts), _urgency_cue(texts), _ask(texts),
                 channel, json.dumps(STAGES), json.dumps(samples), json.dumps(top_terms),
                 novelty, status, size, now),
            )
        # Low-novelty clusters are covered by the approved catalogue; nothing to add.

    # template_match feature: max cosine sim to approved centroids (0 for none)
    appr_rows = conn.execute("SELECT id, top_terms FROM templates WHERE status = 'approved'").fetchall()
    if appr_rows:
        ref_texts = []
        for t in appr_rows:
            terms = " ".join(json.loads(t["top_terms"]))
            samples = conn.execute("SELECT script_samples FROM templates WHERE id = ?", (t["id"],)).fetchone()["script_samples"]
            ref_texts.append(" ".join(json.loads(samples)) + " " + terms)
        appr_mat = vec.transform(ref_texts)
        sims_all = cosine_similarity(X, appr_mat).max(axis=1)
        pid_series = docs["payment_id"].to_numpy()
        conn.executemany("UPDATE payment_features SET template_match = ? WHERE payment_id = ?",
                         [(float(s), int(pid)) for s, pid in zip(sims_all, pid_series)])
    conn.commit()
    return {"clusters": int(k), "proposed": proposed, "documents": int(len(docs))}
