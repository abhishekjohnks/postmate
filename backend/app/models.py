"""Normalized ledger. Money uses Decimal; identifiers use UUIDs, never client counters."""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index,
                        Integer, JSON, Numeric, String, Text, UniqueConstraint, text)
from sqlalchemy.orm import Mapped, mapped_column
from app.db.session import Base


def uid():
    return str(uuid4())


class Record:
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))


class User(Record, Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(100), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(20), default="staff")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(Integer, default=0)
    __table_args__ = (
        CheckConstraint("role IN ('super_admin', 'staff')", name="ck_user_role"),
        Index("uq_single_super_admin", "role", unique=True, postgresql_where=text("role = 'super_admin'")),
    )


class StaffProfile(Record, Base):
    __tablename__ = "staff_profiles"
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    post_office: Mapped[str | None] = mapped_column(String(200))
    agent_id: Mapped[str | None] = mapped_column(String(100))


class Customer(Record, Base):
    __tablename__ = "customers"
    customer_code: Mapped[str] = mapped_column(String(30), unique=True, default=lambda: "CUS-" + uuid4().hex[:12].upper())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    full_name: Mapped[str] = mapped_column(String(200), index=True)
    dob: Mapped[date] = mapped_column(Date)
    phone: Mapped[str] = mapped_column(String(20), index=True)
    address: Mapped[str] = mapped_column(Text)
    aadhaar_encrypted: Mapped[str | None] = mapped_column(Text)
    pan_encrypted: Mapped[str | None] = mapped_column(Text)
    post_office: Mapped[str] = mapped_column(String(200), index=True)
    location: Mapped[str] = mapped_column(String(200))
    staff_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Scheme(Record, Base):
    __tablename__ = "schemes"
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    # 'none' means deposits are discretionary and must be explicitly scheduled.
    frequency_months: Mapped[int | None] = mapped_column(Integer)
    duration_months: Mapped[int | None] = mapped_column(Integer)
    schedule_kind: Mapped[str] = mapped_column(String(20), default="collection")
    allow_partial: Mapped[bool] = mapped_column(Boolean, default=False)
    historical_only: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (
        CheckConstraint("frequency_months IS NULL OR frequency_months >= 0", name="ck_scheme_frequency"),
        CheckConstraint("duration_months IS NULL OR duration_months > 0", name="ck_scheme_duration"),
        CheckConstraint("schedule_kind IN ('collection', 'discretionary', 'income')", name="ck_scheme_kind"),
    )


class SchemeField(Record, Base):
    __tablename__ = "scheme_fields"
    scheme_id: Mapped[str] = mapped_column(ForeignKey("schemes.id"), index=True)
    key: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(150))
    field_type: Mapped[str] = mapped_column(String(20), default="text")
    required: Mapped[bool] = mapped_column(Boolean, default=False)
    __table_args__ = (UniqueConstraint("scheme_id", "key", name="uq_scheme_field"),)


class Account(Record, Base):
    __tablename__ = "customer_scheme_accounts"
    account_code: Mapped[str] = mapped_column(String(30), unique=True, default=lambda: "ACC-" + uuid4().hex[:12].upper())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    scheme_id: Mapped[str] = mapped_column(ForeignKey("schemes.id"), index=True)
    account_number: Mapped[str | None] = mapped_column(String(100), index=True)
    policy_number: Mapped[str | None] = mapped_column(String(100), index=True)
    cif_id: Mapped[str | None] = mapped_column(String(100), index=True)
    start_date: Mapped[date] = mapped_column(Date)
    nominee_name: Mapped[str | None] = mapped_column(String(200))
    maturity_date: Mapped[date | None] = mapped_column(Date, index=True)
    maturity_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    frequency_months: Mapped[int | None] = mapped_column(Integer)
    post_office: Mapped[str] = mapped_column(String(200))
    agent_id: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(20), default="active")
    remarks: Mapped[str] = mapped_column(Text, default="")
    custom_fields: Mapped[dict] = mapped_column(JSON, default=dict)
    rule_snapshot: Mapped[dict] = mapped_column(JSON)
    __table_args__ = (
        UniqueConstraint("scheme_id", "account_number", name="uq_scheme_account_number"),
        UniqueConstraint("scheme_id", "policy_number", name="uq_scheme_policy_number"),
        CheckConstraint("amount > 0", name="ck_account_amount"),
        CheckConstraint("maturity_amount IS NULL OR maturity_amount >= 0", name="ck_account_maturity_amount"),
        CheckConstraint("status IN ('active','closed','matured','inactive')", name="ck_account_status"),
    )


class PaymentSchedule(Record, Base):
    __tablename__ = "payment_schedules"
    account_id: Mapped[str] = mapped_column(ForeignKey("customer_scheme_accounts.id"), index=True)
    sequence: Mapped[int] = mapped_column(Integer)
    due_date: Mapped[date] = mapped_column(Date, index=True)
    expected_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    cancelled: Mapped[bool] = mapped_column(Boolean, default=False)
    remarks: Mapped[str] = mapped_column(Text, default="")
    __table_args__ = (
        UniqueConstraint("account_id", "sequence", name="uq_account_sequence"),
        CheckConstraint("expected_amount > 0 AND paid_amount >= 0 AND paid_amount <= expected_amount", name="ck_schedule_amount"),
    )


class PaymentTransaction(Record, Base):
    __tablename__ = "payment_transactions"
    schedule_id: Mapped[str] = mapped_column(ForeignKey("payment_schedules.id"), index=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    staff_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    payment_date: Mapped[date] = mapped_column(Date, index=True)
    method: Mapped[str] = mapped_column(String(30))
    reference: Mapped[str | None] = mapped_column(String(150), unique=True)
    remarks: Mapped[str] = mapped_column(Text, default="")
    idempotency_key: Mapped[str] = mapped_column(String(100), unique=True)
    request_fingerprint: Mapped[str] = mapped_column(String(64))
    reversed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reversal_reason: Mapped[str | None] = mapped_column(Text)
    reversed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    __table_args__ = (CheckConstraint("amount > 0", name="ck_transaction_amount"),)


class PaymentReceipt(Record, Base):
    __tablename__ = "payment_receipts"
    transaction_id: Mapped[str] = mapped_column(ForeignKey("payment_transactions.id"), unique=True)
    receipt_number: Mapped[str] = mapped_column(String(60), unique=True, default=lambda: "PM-" + uuid4().hex.upper())
    snapshot: Mapped[dict] = mapped_column(JSON)
    download_count: Mapped[int] = mapped_column(Integer, default=0)
    last_downloaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CustomerDocument(Record, Base):
    __tablename__ = "customer_documents"
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    storage_key: Mapped[str] = mapped_column(String(80), unique=True)
    content_type: Mapped[str] = mapped_column(String(60))
    size: Mapped[int] = mapped_column(Integer)
    uploaded_by: Mapped[str] = mapped_column(ForeignKey("users.id"))


class Notification(Record, Base):
    __tablename__ = "notifications"
    schedule_id: Mapped[str] = mapped_column(ForeignKey("payment_schedules.id"), unique=True)
    kind: Mapped[str] = mapped_column(String(20))
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)


class AuditLog(Record, Base):
    __tablename__ = "audit_logs"
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(80), index=True)
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[str | None] = mapped_column(String(36))
    details: Mapped[dict] = mapped_column(JSON, default=dict)


Index("ix_schedule_due_cancelled", PaymentSchedule.due_date, PaymentSchedule.cancelled)
