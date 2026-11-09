from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StaffCreate(Input):
    username: str = Field(min_length=3, max_length=100, pattern=r"^[a-zA-Z0-9_.@-]+$")
    full_name: str = Field(min_length=2, max_length=200)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["staff"] = "staff"
    phone: str | None = Field(default=None, max_length=20)
    post_office: str | None = Field(default=None, max_length=200)
    agent_id: str | None = Field(default=None, max_length=100)


class StaffUpdate(Input):
    full_name: str = Field(min_length=2, max_length=200)
    active: bool
    role: Literal["staff"] = "staff"
    password: str | None = Field(default=None, min_length=12, max_length=128)
    phone: str | None = Field(default=None, max_length=20)
    post_office: str | None = Field(default=None, max_length=200)
    agent_id: str | None = Field(default=None, max_length=100)


class CustomerInput(Input):
    full_name: str = Field(min_length=2, max_length=200)
    dob: date
    phone: str = Field(pattern=r"^[0-9+ ()-]{10,20}$")
    address: str = Field(min_length=5, max_length=2000)
    aadhaar: str | None = Field(default=None, pattern=r"^\d{12}$")
    pan: str | None = Field(default=None, pattern=r"^[A-Z]{5}\d{4}[A-Z]$")
    post_office: str = Field(min_length=2, max_length=200)
    location: str = Field(min_length=2, max_length=200)
    staff_id: str | None = None
    active: bool = True

    @field_validator("dob")
    @classmethod
    def valid_dob(cls, value):
        from app.core.config import today
        if value > today():
            raise ValueError("Date of birth cannot be in the future")
        return value


class FieldInput(Input):
    key: str = Field(pattern=r"^[a-z][a-z0-9_]{0,79}$")
    label: str = Field(min_length=1, max_length=150)
    field_type: Literal["text", "number", "date"] = "text"
    required: bool = False


class SchemeInput(Input):
    code: str = Field(min_length=2, max_length=40, pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=2, max_length=200)
    description: str = Field(default="", max_length=4000)
    active: bool = True
    frequency_months: int | None = Field(default=None, ge=0, le=120)
    duration_months: int | None = Field(default=None, ge=1, le=1200)
    schedule_kind: Literal["collection", "discretionary", "income"] = "collection"
    allow_partial: bool = False
    historical_only: bool = False
    fields: list[FieldInput] = Field(default_factory=list, max_length=50)


class AccountInput(Input):
    customer_id: str
    scheme_id: str
    account_number: str | None = Field(default=None, max_length=100)
    policy_number: str | None = Field(default=None, max_length=100)
    cif_id: str | None = Field(default=None, max_length=100)
    start_date: date
    nominee_name: str | None = Field(default=None, max_length=200)
    maturity_date: date | None = None
    maturity_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    frequency_months: int | None = Field(default=None, ge=0, le=120)
    payment_mode: Literal["scheme_default", "flexible"] = "scheme_default"
    post_office: str = Field(min_length=2, max_length=200)
    agent_id: str | None = Field(default=None, max_length=100)
    remarks: str = Field(default="", max_length=2000)
    custom_fields: dict[str, str] = Field(default_factory=dict)
    historical_record: bool = False


class AccountUpdate(Input):
    status: Literal["active", "closed", "matured", "inactive"]
    remarks: str = Field(default="", max_length=2000)
    nominee_name: str | None = Field(default=None, max_length=200)
    maturity_amount: Decimal | None = Field(default=None, ge=0, max_digits=14, decimal_places=2)


class AccountDraft(AccountInput):
    customer_id: None = None


class CustomerRegistration(Input):
    customer: CustomerInput
    accounts: list[AccountDraft] = Field(default_factory=list, max_length=20)


class ScheduleInput(Input):
    account_id: str
    due_date: date
    expected_amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    remarks: str = Field(min_length=3, max_length=2000)


class PaymentInput(Input):
    schedule_id: str
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    payment_date: date
    method: Literal["cash", "upi", "bank_transfer", "cheque"]
    reference: str | None = Field(default=None, max_length=150)
    remarks: str = Field(default="", max_length=2000)


class Reason(Input):
    reason: str = Field(min_length=5, max_length=2000)


class FlexibleDepositInput(Input):
    account_id: str
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    payment_date: date
    method: Literal["cash", "upi", "bank_transfer", "cheque"] = "cash"
    reference: str | None = Field(default=None, max_length=150)
    remarks: str = Field(default="", max_length=2000)
