"""Tests that need no database:   pytest -v"""
from datetime import date, datetime, time

import pytest

from app import rules
from app.state_machine import assert_transition, InvalidTransition, can_transition
from app.ml.features import build_features, FEATURE_NAMES
from app.ml.train import generate_synthetic_data, train
from app.ml.qualification_engine import QualificationEngine


# ---------- validation rules ---------------------------------------------
def test_phone_formats():
    assert rules.is_valid_phone("0712345678")
    assert rules.is_valid_phone("+254 712 345 678")
    assert rules.is_valid_phone("0112345678")
    assert not rules.is_valid_phone("12345")
    assert not rules.is_valid_phone(None)


def _checks(**over):
    base = dict(company="Acme", contact="0712345678", email="a@b.co", brand_name="Fizz",
                category="Beverages", store_id=1, slot_id=1, ambassador_count=2)
    base.update(over)
    return rules.required_field_checks(**base)


AMBS = [{"full_name": "A", "phone": "0711111111"}, {"full_name": "B", "phone": "0722222222"}]


def test_valid_submission_has_no_errors():
    assert rules.validate_submission(checks=_checks(), contact="0712345678", email="a@b.co",
                                     ambassador_count=2, ambassadors=AMBS) == []


def test_count_mismatch_and_missing_field_detected():
    errs = rules.validate_submission(checks=_checks(category=""), contact="0712345678",
                                     email="a@b.co", ambassador_count=3, ambassadors=AMBS)
    assert any("does not match" in e for e in errs)
    assert any("product category" in e for e in errs)


# ---------- conflict prevention ---------------------------------------------
def test_store_limit_exceeded():
    overlaps = [{"supplier_id": 9, "company": "X", "category": "Snacks", "ambassador_count": 4}]
    out = rules.find_conflicts(requested_count=3, effective_limit=6, category="Beverages",
                               supplier_id=1, overlaps=overlaps)
    assert len(out) == 1 and "Store limit" in out[0]


def test_competing_brand_conflict_only_for_same_category_other_supplier():
    same = [{"supplier_id": 9, "company": "Rival", "category": "beverages", "ambassador_count": 1}]
    assert rules.find_conflicts(requested_count=1, effective_limit=10, category="Beverages",
                                supplier_id=1, overlaps=same)
    own = [{"supplier_id": 1, "company": "Me", "category": "Beverages", "ambassador_count": 1}]
    assert not rules.find_conflicts(requested_count=1, effective_limit=10, category="Beverages",
                                    supplier_id=1, overlaps=own)


def test_time_overlap():
    assert rules.times_overlap(time(9), time(12), time(11), time(14))
    assert not rules.times_overlap(time(9), time(12), time(12), time(14))


# ---------- state machine ---------------------------------------------------
def test_state_machine():
    assert can_transition("DRAFT", "SUBMITTED")
    assert can_transition("FLAGGED_FOR_REVIEW", "PENDING_APPROVAL")
    with pytest.raises(InvalidTransition):
        assert_transition("DRAFT", "APPROVED")
    with pytest.raises(InvalidTransition):
        assert_transition("REJECTED", "APPROVED")


# ---------- ML --------------------------------------------------------------
def _features(bad: bool):
    ambs = [{"full_name": "A", "phone": "0711111111", "email": "x@y.co",
             "followers": 250_000 if bad else 8_000, "engagement_rate": 0.002 if bad else 0.04,
             "account_age_days": 20 if bad else 900}] * (3 if bad else 1)
    ambs = [dict(a, phone=f"07000000{i:02d}", email=f"{i}@y.co") for i, a in enumerate(ambs)] if not bad else ambs
    return build_features(
        ambassador_count=len(ambs) + (1 if bad else 0), ambassadors=ambs,
        activation_date=date(2026, 10, 20), submitted_on=datetime(2026, 10, 19),
        completeness_ratio=0.6 if bad else 1.0, store_limit=6,
        reused_contacts=2 if bad else 0, dup_submissions_24h=3 if bad else 0,
        supplier_rejection_rate=0.7 if bad else 0.05, supplier_age_days=5 if bad else 600)


def test_features_have_every_expected_column():
    assert set(_features(False)) == set(FEATURE_NAMES)


def test_engine_trains_and_separates_bad_from_good(tmp_path):
    path = tmp_path / "m.joblib"
    train(generate_synthetic_data(4000), path)
    eng = QualificationEngine(path)
    good, bad = eng.assess(_features(False)), eng.assess(_features(True))
    assert bad.fraud_probability > good.fraud_probability
    assert bad.recommendation == "FLAG"
    assert good.recommendation == "ROUTE_TO_MANAGER"
    assert bad.feedback and good.feedback
