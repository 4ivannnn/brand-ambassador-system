"""Pydantic models = the shape of data going in and out of the API."""
from datetime import date, datetime, time
from typing import Literal
import pydantic  # pyright: ignore[reportMissingImports]

class RegisterIn(pydantic.BaseModel):           # use case: Register (supplier)
    company: str
    contact: str
    email: pydantic.EmailStr
    full_name: str
    gender: Literal["MALE", "FEMALE"]
    password: str = pydantic.Field(min_length=8)


class SupplierGenderIn(pydantic.BaseModel):
    gender: Literal["MALE", "FEMALE"]


class LoginIn(pydantic.BaseModel):
    email: pydantic.EmailStr
    password: str


class TokenOut(pydantic.BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    gender: str | None = None


class BrandIn(pydantic.BaseModel):
    brand_name: str
    category: str


class BrandOut(BrandIn):
    model_config = pydantic.ConfigDict(from_attributes=True)
    brand_id: int


class StoreOut(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)
    store_id: int
    store_name: str
    location: str
    ambassador_limit: int


class SlotOut(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)
    slot_id: int
    store_id: int
    slot_date: date
    start_time: time
    end_time: time
    capacity: int
    status: str


class AmbassadorIn(pydantic.BaseModel):         # use case: Register Ambassadors
    full_name: str
    phone: str
    email: str | None = None
    social_handle: str | None = None
    followers: int | None = pydantic.Field(None, ge=0)
    engagement_rate: float | None = pydantic.Field(None, ge=0, description="fraction, e.g. 0.035 = 3.5%")
    account_age_days: int | None = pydantic.Field(None, ge=0)


class AmbassadorOut(AmbassadorIn):
    model_config = pydantic.ConfigDict(from_attributes=True)
    ambassador_id: int


class RequestIn(pydantic.BaseModel):            # use case: Submit Request + Select Time Slot
    brand_id: int
    slot_id: int
    ambassador_count: int = pydantic.Field(ge=1)
    ambassadors: list[AmbassadorIn]


class RequestOut(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)
    request_id: int
    supplier_id: int
    brand_id: int
    store_id: int
    slot_id: int
    activation_date: date
    start_time: time
    end_time: time
    ambassador_count: int
    status: str
    flag_reason: str | None
    date_submitted: datetime | None
    ambassadors: list[AmbassadorOut] = []


class AssessmentOut(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)
    model_version: str
    authenticity_score: float
    fraud_probability: float
    fit_score: float
    confidence: float
    recommendation: str
    feedback: list[str]
    created_at: datetime


class RequestDetailOut(RequestOut):
    latest_assessment: AssessmentOut | None = None


class DecisionIn(pydantic.BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    reason: str | None = None


class OverrideIn(pydantic.BaseModel):
    reason: str


class NotificationOut(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)
    notification_id: int
    request_id: int | None
    message: str
    is_read: bool
    created_at: datetime


class AuditOut(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(from_attributes=True)
    audit_id: int
    request_id: int | None
    user_id: int | None
    action: str
    from_status: str | None
    to_status: str | None
    detail: str | None
    created_at: datetime
