"""SQLAlchemy models - one class per table in database/schema.sql (same names, same columns)."""
from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Integer, Numeric,
                        String, Text, Time, func)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Supplier(Base):
    __tablename__ = "suppliers"
    supplier_id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(150))
    contact: Mapped[str] = mapped_column(String(20))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(back_populates="supplier")
    brands: Mapped[list["Brand"]] = relationship(back_populates="supplier")
    requests: Mapped[list["ActivationRequest"]] = relationship(back_populates="supplier")


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int | None] = mapped_column(ForeignKey("suppliers.supplier_id"))
    role: Mapped[str] = mapped_column(String(20))
    full_name: Mapped[str] = mapped_column(String(150))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    gender: Mapped[str | None] = mapped_column(String(10), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    supplier: Mapped["Supplier | None"] = relationship(back_populates="users")


class Brand(Base):
    __tablename__ = "brands"
    brand_id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.supplier_id"))
    brand_name: Mapped[str] = mapped_column(String(150))
    category: Mapped[str] = mapped_column(String(80))

    supplier: Mapped["Supplier"] = relationship(back_populates="brands")


class Store(Base):
    __tablename__ = "stores"
    store_id: Mapped[int] = mapped_column(primary_key=True)
    store_name: Mapped[str] = mapped_column(String(150))
    location: Mapped[str] = mapped_column(String(200))
    ambassador_limit: Mapped[int] = mapped_column(Integer)
    manager_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))

    slots: Mapped[list["StoreSlot"]] = relationship(back_populates="store")


class StoreSlot(Base):
    __tablename__ = "store_slots"
    slot_id: Mapped[int] = mapped_column(primary_key=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.store_id"))
    slot_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    capacity: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(10), default="OPEN")

    store: Mapped["Store"] = relationship(back_populates="slots")


class ActivationRequest(Base):
    __tablename__ = "activation_requests"
    request_id: Mapped[int] = mapped_column(primary_key=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.supplier_id"))
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.brand_id"))
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.store_id"))
    slot_id: Mapped[int] = mapped_column(ForeignKey("store_slots.slot_id"))
    activation_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    ambassador_count: Mapped[int] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    flag_reason: Mapped[str | None] = mapped_column(Text)
    date_submitted: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    supplier: Mapped["Supplier"] = relationship(back_populates="requests")
    brand: Mapped["Brand"] = relationship()
    store: Mapped["Store"] = relationship()
    slot: Mapped["StoreSlot"] = relationship()
    ambassadors: Mapped[list["Ambassador"]] = relationship(
        back_populates="request", cascade="all, delete-orphan")
    approvals: Mapped[list["Approval"]] = relationship(back_populates="request")
    assessments: Mapped[list["AIAssessment"]] = relationship(back_populates="request")


class Ambassador(Base):
    __tablename__ = "ambassadors"
    ambassador_id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("activation_requests.request_id"))
    full_name: Mapped[str] = mapped_column(String(150))
    phone: Mapped[str] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(255))
    social_handle: Mapped[str | None] = mapped_column(String(100))
    followers: Mapped[int | None] = mapped_column(Integer)
    engagement_rate: Mapped[float | None] = mapped_column(Numeric(6, 4, asdecimal=False))
    account_age_days: Mapped[int | None] = mapped_column(Integer)

    request: Mapped["ActivationRequest"] = relationship(back_populates="ambassadors")


class Approval(Base):
    __tablename__ = "approvals"
    approval_id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("activation_requests.request_id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    decision: Mapped[str] = mapped_column(String(10))
    reason: Mapped[str | None] = mapped_column(Text)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped["ActivationRequest"] = relationship(back_populates="approvals")


class Notification(Base):
    __tablename__ = "notifications"
    notification_id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("activation_requests.request_id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    message: Mapped[str] = mapped_column(Text)
    channel: Mapped[str] = mapped_column(String(10), default="DASHBOARD")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AIAssessment(Base):
    __tablename__ = "ai_assessments"
    assessment_id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int] = mapped_column(ForeignKey("activation_requests.request_id"))
    model_version: Mapped[str] = mapped_column(String(50))
    authenticity_score: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False))
    fraud_probability: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False))
    fit_score: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False))
    confidence: Mapped[float] = mapped_column(Numeric(5, 4, asdecimal=False))
    recommendation: Mapped[str] = mapped_column(String(20))
    feedback: Mapped[list] = mapped_column(JSONB, default=list)
    features: Mapped[dict | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    request: Mapped["ActivationRequest"] = relationship(back_populates="assessments")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    audit_id: Mapped[int] = mapped_column(primary_key=True)
    request_id: Mapped[int | None] = mapped_column(ForeignKey("activation_requests.request_id"))
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id"))
    action: Mapped[str] = mapped_column(String(50))
    from_status: Mapped[str | None] = mapped_column(String(20))
    to_status: Mapped[str | None] = mapped_column(String(20))
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
