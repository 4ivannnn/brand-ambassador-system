"""FastAPI application - the back-end for the React front-end.

Run:   uvicorn app.main:app --reload
Docs:  http://127.0.0.1:8000/docs   (interactive - you can test every endpoint here)
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import config, security
from app import state_machine as sm
from app.database import get_db
from app.ml.qualification_engine import QualificationEngine
from app.models import (ActivationRequest, AIAssessment, AuditLog, Ambassador, Brand, Notification,
                        Store, StoreSlot, Supplier, User)
from app.schemas import (AssessmentOut, AuditOut, BrandIn, BrandOut, DecisionIn, LoginIn, NotificationOut, OverrideIn,
                         RegisterIn, RequestDetailOut, RequestIn, RequestOut, SlotOut, StoreOut, TokenOut)
from app.services import workflow
from app.services.workflow import WorkflowError

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        app.state.engine = QualificationEngine(config.MODEL_PATH, config.CONFIDENCE_THRESHOLD,
                                               config.FRAUD_FLAG_THRESHOLD)
        log.info("Qualification model loaded: %s", app.state.engine.model_version)
    except FileNotFoundError as e:
        app.state.engine = None
        log.warning("%s  (submissions will be refused until a model exists)", e)
    yield


app = FastAPI(title="Automated Brand Ambassador Approval System", version="1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://localhost:5173",
                                                   "http://127.0.0.1:5173"],
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(WorkflowError)
async def workflow_error_handler(_: Request, exc: WorkflowError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "errors": exc.details})


# --------------------------------------------------------------------------- auth helpers
bearer = HTTPBearer()


def current_user(creds: HTTPAuthorizationCredentials = Depends(bearer), db: Session = Depends(get_db)) -> User:
    uid = security.verify_token(creds.credentials)
    user = db.get(User, uid) if uid else None
    if not user:
        raise HTTPException(401, "Invalid or expired token.")
    return user


def require_role(*roles: str):
    def dep(user: User = Depends(current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(403, "You do not have permission for this action.")
        return user
    return dep


def get_engine(request: Request) -> QualificationEngine:
    if request.app.state.engine is None:
        raise HTTPException(503, "The qualification model is not trained yet. Run: python -m app.ml.train")
    return request.app.state.engine


def load_request(db: Session, request_id: int, user: User) -> ActivationRequest:
    req = db.get(ActivationRequest, request_id)
    if not req or (user.role == "SUPPLIER" and req.supplier_id != user.supplier_id):
        raise HTTPException(404, "Request not found.")
    return req


# --------------------------------------------------------------------------- auth
@app.post("/auth/register", response_model=TokenOut, status_code=201, tags=["Auth"])
def register(body: RegisterIn, db: Session = Depends(get_db)):
    """Use case 'Register': creates the supplier company and its first user."""
    if db.scalar(select(User).where(User.email == body.email)) or \
       db.scalar(select(Supplier).where(Supplier.email == body.email)):
        raise HTTPException(409, "An account with this email already exists.")
    supplier = Supplier(company=body.company, contact=body.contact, email=body.email)
    db.add(supplier)
    db.flush()
    user = User(supplier_id=supplier.supplier_id, role="SUPPLIER", full_name=body.full_name,
                email=body.email, phone=body.contact, password_hash=security.hash_password(body.password))
    db.add(user)
    db.commit()
    return TokenOut(access_token=security.create_token(user.user_id), role=user.role)


@app.post("/auth/login", response_model=TokenOut, tags=["Auth"])
def login(body: LoginIn, db: Session = Depends(get_db)):
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not security.verify_password(body.password, user.password_hash):
        raise HTTPException(401, "Incorrect email or password.")
    return TokenOut(access_token=security.create_token(user.user_id), role=user.role)


# --------------------------------------------------------------------------- reference data
@app.get("/stores", response_model=list[StoreOut], tags=["Stores"])
def list_stores(_: User = Depends(current_user), db: Session = Depends(get_db)):
    return db.scalars(select(Store).order_by(Store.store_name)).all()


@app.get("/stores/{store_id}/slots", response_model=list[SlotOut], tags=["Stores"])
def list_slots(store_id: int, only_open: bool = True, _: User = Depends(current_user),
               db: Session = Depends(get_db)):
    """Use case 'Select Time Slot' - the calendar shows these."""
    q = select(StoreSlot).where(StoreSlot.store_id == store_id).order_by(StoreSlot.slot_date, StoreSlot.start_time)
    if only_open:
        q = q.where(StoreSlot.status == "OPEN")
    return db.scalars(q).all()


@app.post("/brands", response_model=BrandOut, status_code=201, tags=["Brands"])
def add_brand(body: BrandIn, user: User = Depends(require_role("SUPPLIER")), db: Session = Depends(get_db)):
    brand = Brand(supplier_id=user.supplier_id, brand_name=body.brand_name, category=body.category)
    db.add(brand)
    db.commit()
    return brand


@app.get("/brands", response_model=list[BrandOut], tags=["Brands"])
def my_brands(user: User = Depends(require_role("SUPPLIER")), db: Session = Depends(get_db)):
    return db.scalars(select(Brand).where(Brand.supplier_id == user.supplier_id)).all()


# --------------------------------------------------------------------------- activation requests
@app.post("/requests", response_model=RequestOut, status_code=201, tags=["Requests"])
def create_request(body: RequestIn, user: User = Depends(require_role("SUPPLIER")),
                   db: Session = Depends(get_db)):
    """Creates a DRAFT request (with its ambassadors) for the chosen slot. Nothing is validated yet."""
    brand = db.get(Brand, body.brand_id)
    if not brand or brand.supplier_id != user.supplier_id:
        raise HTTPException(404, "Brand not found.")
    slot = db.get(StoreSlot, body.slot_id)
    if not slot:
        raise HTTPException(404, "Slot not found.")
    req = ActivationRequest(
        supplier_id=user.supplier_id, brand_id=brand.brand_id, store_id=slot.store_id, slot_id=slot.slot_id,
        activation_date=slot.slot_date, start_time=slot.start_time, end_time=slot.end_time,
        ambassador_count=body.ambassador_count, status=sm.DRAFT,
        ambassadors=[Ambassador(**a.model_dump()) for a in body.ambassadors])
    db.add(req)
    db.flush()
    workflow.log_action(db, req.request_id, user.user_id, "CREATED", None, sm.DRAFT)
    db.commit()
    return req


@app.post("/requests/{request_id}/submit", tags=["Requests"])
def submit(request_id: int, user: User = Depends(require_role("SUPPLIER")), db: Session = Depends(get_db),
           engine: QualificationEngine = Depends(get_engine)):
    """Runs the whole pipeline: validation -> AI checks -> conflict checks -> route to the manager."""
    req = load_request(db, request_id, user)
    try:
        result = workflow.submit_request(db, req, user, engine)
    except WorkflowError:
        db.rollback()
        raise
    db.commit()
    return result


@app.get("/requests", response_model=list[RequestOut], tags=["Requests"])
def list_requests(status: str | None = None, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(ActivationRequest).order_by(ActivationRequest.request_id.desc())
    if user.role == "SUPPLIER":
        q = q.where(ActivationRequest.supplier_id == user.supplier_id)
    elif user.role == "STORE_MANAGER":     # only approved activations at their own stores
        my_stores = select(Store.store_id).where(Store.manager_user_id == user.user_id)
        q = q.where(ActivationRequest.store_id.in_(my_stores),
                    ActivationRequest.status.in_(sm.APPROVED_SET))
    if status:
        q = q.where(ActivationRequest.status == status)
    return db.scalars(q).all()


@app.get("/requests/{request_id}", response_model=RequestDetailOut, tags=["Requests"])
def request_status(request_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """'Request tracking' output: current status plus the latest AI assessment."""
    req = load_request(db, request_id, user)
    latest = db.scalar(select(AIAssessment).where(AIAssessment.request_id == request_id)
                       .order_by(AIAssessment.created_at.desc()).limit(1))
    out = RequestDetailOut.model_validate(req)
    out.latest_assessment = AssessmentOut.model_validate(latest) if latest else None
    return out


@app.post("/requests/{request_id}/decision", tags=["Approval"])
def decide(request_id: int, body: DecisionIn, user: User = Depends(require_role("APPROVING_MANAGER")),
           db: Session = Depends(get_db)):
    """Use case 'Approve Request' (or reject, with a mandatory reason)."""
    req = load_request(db, request_id, user)
    try:
        result = workflow.decide(db, req, user, body.decision, body.reason)
    except WorkflowError:
        db.rollback()
        raise
    db.commit()
    return result


@app.post("/requests/{request_id}/override", tags=["Approval"])
def override(request_id: int, body: OverrideIn, user: User = Depends(require_role("APPROVING_MANAGER")),
             db: Session = Depends(get_db)):
    req = load_request(db, request_id, user)
    try:
        result = workflow.override_flag(db, req, user, body.reason)
    except WorkflowError:
        db.rollback()
        raise
    db.commit()
    return result


@app.post("/requests/{request_id}/complete", tags=["Approval"])
def complete(request_id: int, user: User = Depends(require_role("APPROVING_MANAGER", "STORE_MANAGER")),
             db: Session = Depends(get_db)):
    req = load_request(db, request_id, user)
    try:
        result = workflow.complete(db, req, user)
    except WorkflowError:
        db.rollback()
        raise
    db.commit()
    return result


# --------------------------------------------------------------------------- audit + notifications
@app.get("/audit-trail", response_model=list[AuditOut], tags=["Audit"])
def audit_trail(request_id: int | None = None, user: User = Depends(require_role("APPROVING_MANAGER")),
                db: Session = Depends(get_db)):
    """Use case 'View audit trail'."""
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(500)
    if request_id is not None:
        q = q.where(AuditLog.request_id == request_id)
    return db.scalars(q).all()


@app.get("/notifications", response_model=list[NotificationOut], tags=["Notifications"])
def my_notifications(unread_only: bool = False, user: User = Depends(current_user), db: Session = Depends(get_db)):
    q = select(Notification).where(Notification.user_id == user.user_id).order_by(Notification.created_at.desc())
    if unread_only:
        q = q.where(Notification.is_read.is_(False))
    return db.scalars(q).all()


@app.post("/notifications/{notification_id}/read", tags=["Notifications"])
def mark_read(notification_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.user_id:
        raise HTTPException(404, "Notification not found.")
    n.is_read = True
    db.commit()
    return {"ok": True}


@app.get("/health", tags=["System"])
def health(request: Request):
    eng = request.app.state.engine
    return {"status": "ok", "model_version": eng.model_version if eng else None}
