"""Turns one activation request into the numeric feature vector the models use.

Works on plain Python values (no database), so the same function is used by:
  * the API (features gathered from PostgreSQL by app/services/workflow.py)
  * the training script (synthetic data) and unit tests
"""
from __future__ import annotations

import math
from datetime import date, datetime

# Order matters: this is the exact column order the trained model expects.
FEATURE_NAMES = [
    "completeness_ratio",          # share of required fields filled in (0-1)
    "count_mismatch",              # 1 if declared ambassador count != ambassadors listed
    "n_ambassadors",
    "pct_invalid_phone",           # share of ambassadors with an invalid phone number
    "dup_contact_ratio",           # share of ambassadors whose phone/e-mail is duplicated/reused
    "dup_submissions_24h",         # same supplier, store & date submitted repeatedly in 24h
    "has_social_data",             # 1 if any social-media metrics were supplied
    "avg_log_followers",           # log10(1 + followers), averaged over ambassadors
    "avg_engagement_rate",         # fraction, e.g. 0.035 = 3.5 %
    "min_account_age_days",
    "engagement_anomaly",          # 1 if followers/engagement combination looks fake
    "supplier_rejection_rate",     # supplier's past rejected / decided requests
    "supplier_age_days",
    "lead_time_days",              # days between submission and activation date
    "load_ratio",                  # requested ambassadors / store limit
    "category_store_approval_rate", # historic approval rate of this category at this store
]

DEFAULTS = {"followers": 5_000, "engagement_rate": 0.03, "account_age_days": 730}


def _norm_phone(p: str | None) -> str:
    return "".join(ch for ch in (p or "") if ch.isdigit())[-9:]   # last 9 digits


def build_features(*, ambassador_count: int, ambassadors: list[dict],
                   activation_date: date, submitted_on: datetime | date,
                   completeness_ratio: float, store_limit: int,
                   reused_contacts: int = 0, dup_submissions_24h: int = 0,
                   supplier_rejection_rate: float = 0.0, supplier_age_days: int = 0,
                   category_store_approval_rate: float = 0.6,
                   phone_validator=None) -> dict[str, float]:
    """Return {feature_name: value}. `ambassadors` items may contain:
    full_name, phone, email, followers, engagement_rate, account_age_days."""
    n = len(ambassadors)
    safe_n = max(n, 1)

    # --- duplicate / invalid contact details -------------------------------
    phones = [_norm_phone(a.get("phone")) for a in ambassadors if a.get("phone")]
    emails = [a["email"].strip().lower() for a in ambassadors if a.get("email")]
    internal_dups = (len(phones) - len(set(phones))) + (len(emails) - len(set(emails)))
    dup_contact_ratio = min(1.0, (internal_dups + reused_contacts) / safe_n)

    if phone_validator is None:
        from app.rules import is_valid_phone as phone_validator  # local import keeps ml/ importable alone
    invalid = sum(1 for a in ambassadors if not phone_validator(a.get("phone")))
    pct_invalid_phone = invalid / safe_n

    # --- social-media authenticity signals ---------------------------------
    followers = [a.get("followers") for a in ambassadors if a.get("followers") is not None]
    engs = [a.get("engagement_rate") for a in ambassadors if a.get("engagement_rate") is not None]
    ages = [a.get("account_age_days") for a in ambassadors if a.get("account_age_days") is not None]
    has_social = 1.0 if (followers or engs or ages) else 0.0

    avg_followers = sum(followers) / len(followers) if followers else DEFAULTS["followers"]
    avg_eng = sum(engs) / len(engs) if engs else DEFAULTS["engagement_rate"]
    min_age = min(ages) if ages else DEFAULTS["account_age_days"]

    anomaly = 0.0
    for a in ambassadors:
        f, e = a.get("followers"), a.get("engagement_rate")
        if f is not None and e is not None and ((f > 10_000 and e < 0.005) or e > 0.20):
            anomaly = 1.0
            break

    # --- timing / load ------------------------------------------------------
    sub_date = submitted_on.date() if isinstance(submitted_on, datetime) else submitted_on
    lead = (activation_date - sub_date).days

    return {
        "completeness_ratio": float(completeness_ratio),
        "count_mismatch": 1.0 if ambassador_count != n else 0.0,
        "n_ambassadors": float(n),
        "pct_invalid_phone": float(pct_invalid_phone),
        "dup_contact_ratio": float(dup_contact_ratio),
        "dup_submissions_24h": float(dup_submissions_24h),
        "has_social_data": has_social,
        "avg_log_followers": math.log10(1 + max(avg_followers, 0)),
        "avg_engagement_rate": float(avg_eng),
        "min_account_age_days": float(min_age),
        "engagement_anomaly": anomaly,
        "supplier_rejection_rate": float(supplier_rejection_rate),
        "supplier_age_days": float(supplier_age_days),
        "lead_time_days": float(lead),
        "load_ratio": float(ambassador_count) / max(store_limit, 1),
        "category_store_approval_rate": float(category_store_approval_rate),
    }
