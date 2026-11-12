"""The approval workflow: implements the Sequence + Activity diagrams.

Supplier submits -> validate data -> Qualification Engine (authenticity / fraud / fit)
-> check store-limit & competing-brand conflicts -> route to Approving Manager
-> decision -> notification -> confirmation (slot booked).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app import rules
from app.booking_calendar import booking_window
from app import state_machine as sm
from app.ml.features import build_features
from app.ml.qualification_engine import QualificationEngine
from app.models import (Ambassador, ActivationRequest, AIAssessment, Approval, AuditLog, Brand,
                        Store, StoreSlot, Supplier, User)
from app.services import notifications


class WorkflowError(Exception):
    def __init__(self, message: str, status_code: int = 400, details: list[str] | None = None):
        super().__init__(message)
        self.message, self.status_code, self.details = message, status_code, details or []


# --------------------------------------------------------------------------- audit + state
def log_action(db: Session, request_id, user_id, action, from_status=None, to_status=None, detail=None):
    db.add(AuditLog(request_id=request_id, user_id=user_id, action=action,
                    from_status=from_status, to_status=to_status, detail=detail))


def move(db: Session, req: ActivationRequest, new_status: str, user_id=None, action="STATUS_CHANGE",
         detail=None) -> None:
    try:
        sm.assert_transition(req.status, new_status)
    except sm.InvalidTransition as e:
        raise WorkflowError(str(e), 409)
    old, req.status = req.status, new_status
    log_action(db, req.request_id, user_id, action, old, new_status, detail)


# --------------------------------------------------------------------------- conflict checks
def _overlapping(db: Session, store_id: int, day: date, start, end, exclude_id: int | None) -> list[dict]:
    q = (select(ActivationRequest, Brand.category, Supplier.company)
         .join(Brand, Brand.brand_id == ActivationRequest.brand_id)
         .join(Supplier, Supplier.supplier_id == ActivationRequest.supplier_id)
         .where(ActivationRequest.store_id == store_id,
                ActivationRequest.activation_date == day,
                ActivationRequest.status.in_(sm.ACTIVE_STATUSES),
                ActivationRequest.start_time < end,
                ActivationRequest.end_time > start))
    if exclude_id is not None:
        q = q.where(ActivationRequest.request_id != exclude_id)
    return [{"supplier_id": r.supplier_id, "company": company, "category": category,
             "ambassador_count": r.ambassador_count} for r, category, company in db.execute(q)]


def evaluate_conflicts(db: Session, *, store: Store, slot: StoreSlot, category: str,
                       supplier_id: int, count: int, exclude_id: int | None = None) -> list[str]:
    if slot.status != "OPEN":
        return [f"The selected slot is {slot.status.lower()}."]
    overlaps = _overlapping(db, store.store_id, slot.slot_date, slot.start_time, slot.end_time, exclude_id)
    return rules.find_conflicts(requested_count=count,
                                effective_limit=min(store.ambassador_limit, slot.capacity),
                                category=category, supplier_id=supplier_id, overlaps=overlaps)


def suggest_alternatives(db: Session, req: ActivationRequest, how_many: int = 3) -> list[dict]:
    """'Suggest alternative' step of the activity diagram: next open slots with no conflict."""
    slots = db.scalars(
        select(StoreSlot).where(StoreSlot.store_id == req.store_id, StoreSlot.slot_id != req.slot_id,
                StoreSlot.slot_date > date.today(), StoreSlot.status == "OPEN")
        .order_by(StoreSlot.slot_date, StoreSlot.start_time).limit(60)).all()
    found = []
    for s in slots:
        if not evaluate_conflicts(db, store=req.store, slot=s, category=req.brand.category,
                                  supplier_id=req.supplier_id, count=req.ambassador_count,
                                  exclude_id=req.request_id):
            found.append({"slot_id": s.slot_id, "slot_date": s.slot_date.isoformat(),
                          "start_time": s.start_time.isoformat(), "end_time": s.end_time.isoformat()})
            if len(found) == how_many:
                break
    return found


# --------------------------------------------------------------------------- ML feature gathering
def _approval_rate(db: Session, *conds, default: float, min_n: int = 3) -> float:
    base = (select(func.count()).select_from(ActivationRequest)
            .join(Brand, Brand.brand_id == ActivationRequest.brand_id).where(*conds))
    total = db.scalar(base.where(ActivationRequest.status.in_(sm.DECIDED_STATUSES))) or 0
    good = db.scalar(base.where(ActivationRequest.status.in_(sm.APPROVED_SET))) or 0
    return default if total < min_n else good / total


def _ambassador_dicts(req: ActivationRequest) -> list[dict]:
    return [{"full_name": a.full_name, "phone": a.phone, "email": a.email, "followers": a.followers,
             "engagement_rate": a.engagement_rate, "account_age_days": a.account_age_days}
            for a in req.ambassadors]


def _checks(req: ActivationRequest) -> dict[str, bool]:
    return rules.required_field_checks(
        company=req.supplier.company, contact=req.supplier.contact, email=req.supplier.email,
        brand_name=req.brand.brand_name, category=req.brand.category, store_id=req.store_id,
        slot_id=req.slot_id, ambassador_count=req.ambassador_count)


def gather_features(db: Session, req: ActivationRequest, now: datetime) -> dict:
    checks = _checks(req)
    others = ActivationRequest.request_id != req.request_id

    supplier_rejection = 1.0 - _approval_rate(
        db, ActivationRequest.supplier_id == req.supplier_id, others, default=1.0)
    category_rate = _approval_rate(
        db, Brand.category == req.brand.category, ActivationRequest.store_id == req.store_id, others,
        default=0.6)

    dup_24h = db.scalar(select(func.count()).select_from(ActivationRequest).where(
        ActivationRequest.supplier_id == req.supplier_id, ActivationRequest.store_id == req.store_id,
        ActivationRequest.activation_date == req.activation_date, others,
        ActivationRequest.date_submitted >= now - timedelta(hours=24))) or 0

    reused = 0                                # contacts already used by a DIFFERENT supplier
    for a in req.ambassadors:
        same_person = [Ambassador.phone == a.phone]
        if a.email:
            same_person.append(Ambassador.email == a.email)
        hit = db.scalar(select(func.count()).select_from(Ambassador)
                        .join(ActivationRequest, ActivationRequest.request_id == Ambassador.request_id)
                        .where(ActivationRequest.supplier_id != req.supplier_id, or_(*same_person))) or 0
        reused += 1 if hit else 0

    supplier_created = req.supplier.created_at
    if supplier_created.tzinfo is None:
        supplier_created = supplier_created.replace(tzinfo=timezone.utc)

    return build_features(
        ambassador_count=req.ambassador_count, ambassadors=_ambassador_dicts(req),
        activation_date=req.activation_date, submitted_on=now,
        completeness_ratio=sum(checks.values()) / len(checks), store_limit=req.store.ambassador_limit,
        reused_contacts=reused, dup_submissions_24h=dup_24h,
        supplier_rejection_rate=supplier_rejection,
        supplier_age_days=max((now - supplier_created).days, 0),
        category_store_approval_rate=category_rate)


# --------------------------------------------------------------------------- 1. submit
def submit_request(db: Session, req: ActivationRequest, user: User, engine: QualificationEngine) -> dict:
    if req.status != sm.DRAFT:
        raise WorkflowError("Only draft requests can be submitted.", 409)

    errors = rules.validate_submission(
        checks=_checks(req), contact=req.supplier.contact, email=req.supplier.email,
        ambassador_count=req.ambassador_count, ambassadors=_ambassador_dicts(req))
    earliest_date, latest_date = booking_window()
    if req.activation_date < earliest_date or req.activation_date > latest_date:
        errors.append(f"Activation date must be between {earliest_date.isoformat()} and {latest_date.isoformat()}.")
    if req.activation_date <= date.today():
        errors.append("The activation date must be at least one day in the future.")
    if errors:   # activity diagram: invalid -> Error back to the supplier (request stays a draft)
        raise WorkflowError("The request is incomplete or invalid.", 422, errors)

    now = datetime.now(timezone.utc)
    req.date_submitted = now
    move(db, req, sm.SUBMITTED, user.user_id, "SUBMIT")
    move(db, req, sm.UNDER_VALIDATION, None, "VALIDATION_STARTED")

    features = gather_features(db, req, now)
    result = engine.assess(features)
    db.add(AIAssessment(request_id=req.request_id, model_version=result.model_version,
                        authenticity_score=result.authenticity_score,
                        fraud_probability=result.fraud_probability, fit_score=result.fit_score,
                        confidence=result.confidence, recommendation=result.recommendation,
                        feedback=result.feedback, features=features))

    conflicts = evaluate_conflicts(db, store=req.store, slot=req.slot, category=req.brand.category,
                                   supplier_id=req.supplier_id, count=req.ambassador_count,
                                   exclude_id=req.request_id)
    problems = conflicts + (["AI review: " + m for m in result.feedback]
                            if result.recommendation == "FLAG" else [])
    alternatives: list[dict] = []

    if problems:
        req.flag_reason = " | ".join(problems)
        if conflicts:
            alternatives = suggest_alternatives(db, req)
        move(db, req, sm.FLAGGED, None, "FLAGGED", req.flag_reason)
        msg = f"Request #{req.request_id} was flagged for review: {req.flag_reason}"
        if alternatives:
            msg += " Alternative slot ids: " + ", ".join(str(a["slot_id"]) for a in alternatives)
        notifications.notify_supplier(db, req.supplier_id, req.request_id, msg)
        notifications.notify_managers(db, req.request_id,
                                      f"Request #{req.request_id} needs manual review (flagged).")
    else:
        move(db, req, sm.PENDING_APPROVAL, None, "VALIDATION_PASSED")
        notifications.notify_managers(
            db, req.request_id,
            f"New request #{req.request_id} awaiting approval (AI fit score {result.fit_score:.0%}).")
        notifications.notify_supplier(db, req.supplier_id, req.request_id,
                                      f"Request #{req.request_id} passed validation and is awaiting approval.")

    return {"request_id": req.request_id, "status": req.status, "assessment": result.as_dict(),
            "problems": problems, "alternative_slots": alternatives}


# --------------------------------------------------------------------------- 2. manager decisions
def decide(db: Session, req: ActivationRequest, manager: User, decision: str, reason: str | None) -> dict:
    if decision == "REJECT":
        if req.status not in (sm.PENDING_APPROVAL, sm.FLAGGED):
            raise WorkflowError(f"A request in status {req.status} cannot be rejected.", 409)
        if not reason:
            raise WorkflowError("A reason is required when rejecting a request.", 422)
        db.add(Approval(request_id=req.request_id, user_id=manager.user_id, decision="REJECTED", reason=reason))
        move(db, req, sm.REJECTED, manager.user_id, "REJECTED", reason)
        notifications.notify_supplier(db, req.supplier_id, req.request_id,
                                      f"Request #{req.request_id} was rejected. Reason: {reason}")
        return {"request_id": req.request_id, "status": req.status}

    # APPROVE ---------------------------------------------------------------
    if req.status != sm.PENDING_APPROVAL:
        raise WorkflowError(f"A request in status {req.status} cannot be approved "
                            "(flagged requests need a manual override first).", 409)

    # Lock the store row so two managers cannot over-book the same store at the same moment.
    store = db.scalar(select(Store).where(Store.store_id == req.store_id).with_for_update())
    slot = db.get(StoreSlot, req.slot_id)
    conflicts = evaluate_conflicts(db, store=store, slot=slot, category=req.brand.category,
                                   supplier_id=req.supplier_id, count=req.ambassador_count,
                                   exclude_id=req.request_id)
    if conflicts:
        raise WorkflowError("Cannot approve: a conflict now exists.", 409, conflicts)

    db.add(Approval(request_id=req.request_id, user_id=manager.user_id, decision="APPROVED", reason=reason))
    move(db, req, sm.APPROVED, manager.user_id, "APPROVED", reason)
    move(db, req, sm.SLOT_BOOKED, None, "SLOT_BOOKED", f"slot {slot.slot_id}")

    db.flush()
    booked = db.scalar(select(func.coalesce(func.sum(ActivationRequest.ambassador_count), 0)).where(
        ActivationRequest.slot_id == slot.slot_id,
        ActivationRequest.status.in_((sm.APPROVED, sm.SLOT_BOOKED)))) or 0
    if booked >= min(slot.capacity, store.ambassador_limit):
        slot.status = "FULL"

    text = (f"Request #{req.request_id} approved: {req.brand.brand_name} at {store.store_name} on "
            f"{req.activation_date} {req.start_time:%H:%M}-{req.end_time:%H:%M}, "
            f"{req.ambassador_count} ambassador(s).")
    notifications.notify_supplier(db, req.supplier_id, req.request_id, text)
    notifications.notify_user(db, store.manager_user_id, req.request_id,
                              "Please prepare for an upcoming activation. " + text)
    return {"request_id": req.request_id, "status": req.status}


def override_flag(db: Session, req: ActivationRequest, manager: User, reason: str) -> dict:
    """'Manual Override' arrow of the state diagram: Flagged -> Pending Approval."""
    if req.status != sm.FLAGGED:
        raise WorkflowError("Only flagged requests can be overridden.", 409)
    if not reason:
        raise WorkflowError("A reason is required for a manual override.", 422)
    db.add(Approval(request_id=req.request_id, user_id=manager.user_id, decision="OVERRIDE", reason=reason))
    move(db, req, sm.PENDING_APPROVAL, manager.user_id, "MANUAL_OVERRIDE", reason)
    return {"request_id": req.request_id, "status": req.status}


def complete(db: Session, req: ActivationRequest, user: User) -> dict:
    if req.activation_date > date.today():
        raise WorkflowError("The activation date has not been reached yet.", 409)
    move(db, req, sm.COMPLETED, user.user_id, "COMPLETED")
    return {"request_id": req.request_id, "status": req.status}
