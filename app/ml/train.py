"""Train the two models behind the Qualification Engine.

    python -m app.ml.train                 # train on synthetic data (works out of the box)
    python -m app.ml.train --rows 20000    # bigger synthetic set
    python -m app.ml.train --from-db       # retrain the FIT model from real manager decisions

Two models are produced (both saved in ONE file: models/qualification_model.joblib):
  1. fraud model  -> P(request/ambassadors are fraudulent or fake)   [RandomForest]
     used by  QualificationEngine.check_authenticity() / detect_fraud()
  2. fit model    -> P(a manager would approve this request)          [GradientBoosting]
     used by  QualificationEngine.score_fit()

IMPORTANT: until you have real, labelled history, the synthetic generator below
stands in for it. Its metrics only prove the pipeline works - they are NOT evidence
of real-world accuracy. Accuracy testing against human-reviewed requests (proposal
section 3.2.5) must be done with real data, then retrain with --from-db.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split

from app.ml.features import FEATURE_NAMES

DEFAULT_MODEL_PATH = Path("models/qualification_model.joblib")


# --------------------------------------------------------------------------- #
# Synthetic data generator (replace with real data as soon as you have it)
# --------------------------------------------------------------------------- #
def generate_synthetic_data(n: int = 6000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    is_fraud = rng.random(n) < 0.12
    # Only ~65% of fraudulent requests show fake-looking signals in the data we capture;
    # the rest look exactly like genuine ones. This keeps the metrics realistic (no model
    # can catch fraud that leaves no trace in the features).
    obvious = is_fraud & (rng.random(n) < 0.65)

    def pick(genuine, fraud):
        return np.where(obvious, fraud, genuine)

    completeness = np.clip(pick(rng.normal(0.98, 0.04, n), rng.normal(0.85, 0.12, n)), 0.3, 1.0)
    n_amb = rng.integers(1, 9, n).astype(float)
    count_mismatch = (rng.random(n) < pick(0.02, 0.35)).astype(float)
    pct_invalid = np.clip(pick(rng.normal(0.01, 0.04, n), rng.normal(0.30, 0.20, n)), 0, 1)
    dup_ratio = np.clip(pick(rng.normal(0.01, 0.03, n), rng.normal(0.35, 0.25, n)), 0, 1)
    dup_sub = rng.poisson(pick(0.05, 1.5)).astype(float)
    has_social = (rng.random(n) < 0.9).astype(float)

    followers = np.exp(pick(rng.normal(9.0, 1.2, n), rng.normal(10.5, 1.4, n)))   # fake accounts inflate followers
    avg_log_followers = np.log10(1 + followers)
    eng = np.clip(pick(rng.normal(0.035, 0.015, n), rng.choice([0.002, 0.004, 0.25, 0.32], n)), 0.0005, 0.6)
    account_age = np.clip(pick(rng.normal(1100, 500, n), rng.normal(120, 100, n)), 5, 4000)
    anomaly = ((followers > 10_000) & (eng < 0.005) | (eng > 0.20)).astype(float)
    sup_rej = np.clip(pick(rng.beta(1.5, 12, n), rng.beta(4, 5, n)), 0, 1)
    sup_age = np.clip(pick(rng.normal(500, 250, n), rng.normal(40, 40, n)), 0, 3000)
    lead = np.clip(rng.normal(14, 8, n), -1, 60)
    load = np.clip(rng.normal(0.55, 0.3, n), 0.05, 1.8)
    cat_rate = np.clip(rng.normal(0.65, 0.15, n), 0.05, 0.98)

    df = pd.DataFrame({
        "completeness_ratio": completeness, "count_mismatch": count_mismatch,
        "n_ambassadors": n_amb, "pct_invalid_phone": pct_invalid, "dup_contact_ratio": dup_ratio,
        "dup_submissions_24h": dup_sub, "has_social_data": has_social,
        "avg_log_followers": avg_log_followers, "avg_engagement_rate": eng,
        "min_account_age_days": account_age, "engagement_anomaly": anomaly,
        "supplier_rejection_rate": sup_rej, "supplier_age_days": sup_age,
        "lead_time_days": lead, "load_ratio": load, "category_store_approval_rate": cat_rate,
    })[FEATURE_NAMES]
    df["is_fraud"] = is_fraud.astype(int)

    # Would a manager approve? Simple business logic + noise; fraud is almost never approved.
    score = (
        2.0 * (completeness - 0.9) + 1.5 * (cat_rate - 0.5) - 2.5 * sup_rej
        - 2.5 * np.maximum(load - 1.0, 0) - 1.2 * count_mismatch - 1.5 * pct_invalid
        - 0.04 * np.abs(lead - 14) - 1.0 * dup_ratio + 0.6
    )
    prob = 1 / (1 + np.exp(-score * 1.5))
    prob = np.where(is_fraud, prob * 0.15, prob)
    df["approved"] = (rng.random(n) < prob).astype(int)
    return df


# --------------------------------------------------------------------------- #
# Training
# --------------------------------------------------------------------------- #
def _fit_and_report(model, X, y, name):
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.25, stratify=y, random_state=7)
    model.fit(X_tr, y_tr)
    proba = model.predict_proba(X_te)[:, 1]
    auc = roc_auc_score(y_te, proba)
    print(f"\n=== {name} ===  ROC-AUC = {auc:.3f}")
    print(classification_report(y_te, (proba >= 0.5).astype(int), digits=3))
    return {"roc_auc": round(float(auc), 4), "test_rows": int(len(y_te))}


def train(df: pd.DataFrame, out_path: Path = DEFAULT_MODEL_PATH, data_source: str = "synthetic",
          retrain_fraud: bool = True, existing: dict | None = None) -> dict:
    X = df[FEATURE_NAMES]

    fraud_model = RandomForestClassifier(
        n_estimators=300, min_samples_leaf=3, class_weight="balanced", random_state=1, n_jobs=-1)
    fit_model = GradientBoostingClassifier(random_state=1)

    metrics = {}
    if retrain_fraud:
        metrics["fraud"] = _fit_and_report(fraud_model, X, df["is_fraud"], "Fraud / authenticity model")
    else:
        fraud_model = existing["fraud_model"]
        metrics["fraud"] = existing["metrics"]["fraud"]
    metrics["fit"] = _fit_and_report(fit_model, X, df["approved"], "Approval-fit model")

    bundle = {
        "fraud_model": fraud_model,
        "fit_model": fit_model,
        "feature_names": FEATURE_NAMES,
        "model_version": f"rf-gb-{datetime.now():%Y%m%d-%H%M}",
        "data_source": data_source,
        "metrics": metrics,
        "fraud_importances": dict(zip(FEATURE_NAMES, map(float, fraud_model.feature_importances_))),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(bundle, out_path)
    out_path.with_suffix(".json").write_text(json.dumps(
        {k: v for k, v in bundle.items() if k not in ("fraud_model", "fit_model")}, indent=2))
    print(f"\nSaved model '{bundle['model_version']}' -> {out_path}")
    return bundle


def load_real_decisions() -> pd.DataFrame:
    """Build a training frame from manager decisions stored in PostgreSQL (ai_assessments.features
    holds the exact feature snapshot taken when the request was assessed)."""
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import ActivationRequest, AIAssessment
    from app.state_machine import APPROVED_SET, REJECTED

    rows = []
    with SessionLocal() as db:
        q = (select(AIAssessment.features, ActivationRequest.status)
             .join(ActivationRequest, ActivationRequest.request_id == AIAssessment.request_id)
             .where(ActivationRequest.status.in_(APPROVED_SET + (REJECTED,))))
        for features, status in db.execute(q):
            if features and all(k in features for k in FEATURE_NAMES):
                rows.append({**{k: features[k] for k in FEATURE_NAMES}, "approved": int(status != REJECTED)})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rows", type=int, default=6000, help="synthetic rows to generate")
    ap.add_argument("--out", type=Path, default=DEFAULT_MODEL_PATH)
    ap.add_argument("--from-db", action="store_true",
                    help="retrain the approval-fit model from real manager decisions (needs >= 200)")
    args = ap.parse_args()

    if args.from_db:
        real = load_real_decisions()
        if len(real) < 200 or real["approved"].nunique() < 2:
            raise SystemExit(f"Only {len(real)} usable decisions found; need at least 200 with both "
                             "approvals and rejections. Keep using the synthetic model for now.")
        existing = joblib.load(args.out)
        train(real, args.out, data_source=f"database ({len(real)} decisions) + synthetic fraud model",
              retrain_fraud=False, existing=existing)
    else:
        train(generate_synthetic_data(args.rows), args.out)
