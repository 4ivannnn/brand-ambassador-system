"""QualificationEngine - implements the 'Qualification Engine' class from the Class Diagram.

    ModelVersion, ConfidenceThreshold
    CheckAuthenticity()  DetectFraud()  ScoreFit()  GenerateFeedback()
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

import joblib
import pandas as pd

from app.ml.features import FEATURE_NAMES


@dataclass
class Assessment:
    model_version: str
    authenticity_score: float     # 0-1, higher = more likely genuine
    fraud_probability: float      # 0-1
    fit_score: float              # 0-1, likelihood a manager approves
    confidence: float             # 0.5-1, how sure the fraud model is
    recommendation: str           # "FLAG" | "ROUTE_TO_MANAGER"
    feedback: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


class QualificationEngine:
    def __init__(self, model_path: str | Path = "models/qualification_model.joblib",
                 confidence_threshold: float = 0.75, fraud_flag_threshold: float = 0.50):
        path = Path(model_path)
        if not path.exists():
            raise FileNotFoundError(
                f"No trained model at '{path}'. Run:  python -m app.ml.train")
        bundle = joblib.load(path)
        self._fraud = bundle["fraud_model"]
        self._fit = bundle["fit_model"]
        self._names = bundle["feature_names"]
        self.model_version: str = bundle["model_version"]
        self.metrics: dict = bundle.get("metrics", {})
        self.confidence_threshold = confidence_threshold
        self.fraud_flag_threshold = fraud_flag_threshold

    # -- helpers -------------------------------------------------------------
    def _row(self, features: dict) -> pd.DataFrame:
        return pd.DataFrame([[features[n] for n in self._names]], columns=self._names)

    # -- Class-diagram operations -------------------------------------------
    def detect_fraud(self, features: dict) -> float:
        """P(fraudulent / fake). Duplicate submissions, reused contacts, bot-like engagement..."""
        return float(self._fraud.predict_proba(self._row(features))[0, 1])

    def check_authenticity(self, features: dict) -> float:
        """Authenticity score = 1 - fraud probability."""
        return 1.0 - self.detect_fraud(features)

    def score_fit(self, features: dict) -> float:
        """P(a manager would approve), learned from past approval decisions."""
        return float(self._fit.predict_proba(self._row(features))[0, 1])

    def generate_feedback(self, features: dict, fraud_p: float, fit: float) -> list[str]:
        """Plain-language reasons, so suppliers are told WHY (a gap the proposal identifies)."""
        f, msgs = features, []
        if f["completeness_ratio"] < 1.0:
            msgs.append("Some required fields were left empty.")
        if f["count_mismatch"]:
            msgs.append("The declared ambassador count does not match the ambassadors listed.")
        if f["pct_invalid_phone"] > 0:
            msgs.append("One or more ambassador phone numbers are invalid.")
        if f["dup_contact_ratio"] > 0:
            msgs.append("Some ambassador contact details are duplicated or already used by another supplier.")
        if f["dup_submissions_24h"] >= 1:
            msgs.append("Similar requests for this store and date were submitted repeatedly in the last 24 hours.")
        if f["engagement_anomaly"]:
            msgs.append("Follower and engagement figures look unusual (possible fake followers or bot activity).")
        if f["has_social_data"] and f["min_account_age_days"] < 90:
            msgs.append("At least one ambassador social account is very new (< 90 days old).")
        if f["supplier_rejection_rate"] > 0.4:
            msgs.append("This supplier has a high rate of previously rejected requests.")
        if f["load_ratio"] > 1.0:
            msgs.append("The number of ambassadors exceeds the store's limit.")
        if f["lead_time_days"] < 2:
            msgs.append("The activation date is very close to the submission date.")
        if not msgs and fit >= 0.6:
            msgs.append("No issues detected. The request looks complete and consistent.")
        elif not msgs:
            msgs.append("No specific issue found; the manager will review this request.")
        return msgs

    # -- Main entry point ----------------------------------------------------
    def assess(self, features: dict) -> Assessment:
        fraud_p = self.detect_fraud(features)
        fit = self.score_fit(features)
        confidence = max(fraud_p, 1 - fraud_p)

        # Confident that it is fraud -> flag. Otherwise (including low confidence) a human decides.
        if fraud_p >= self.fraud_flag_threshold and confidence >= self.confidence_threshold:
            rec = "FLAG"
        else:
            rec = "ROUTE_TO_MANAGER"

        feedback = self.generate_feedback(features, fraud_p, fit)
        if confidence < self.confidence_threshold:
            feedback.append("The AI is not confident about this request, so it needs careful manual review.")

        return Assessment(
            model_version=self.model_version,
            authenticity_score=round(1 - fraud_p, 4),
            fraud_probability=round(fraud_p, 4),
            fit_score=round(fit, 4),
            confidence=round(confidence, 4),
            recommendation=rec,
            feedback=feedback,
        )
