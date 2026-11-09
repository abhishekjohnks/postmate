from datetime import date
from decimal import Decimal, InvalidOperation
from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlalchemy import select
from app.models import Account, PaymentSchedule, SchemeField
from app.core.config import today

COMMON = {"account_number", "policy_number", "cif_id", "agent_id", "nominee_name", "maturity_amount"}


def account_timeline(start_date, maturity_date, as_of=None):
    """Calendar durations, calculated live in the application's configured timezone."""
    as_of = as_of or today()
    if maturity_date is None:
        return {"account_term": None, "maturity_remaining": None,
                "maturity_status": "not_recorded", "maturity_as_of": as_of.isoformat()}

    def duration(start, end):
        delta = relativedelta(end, start)
        return {"years": delta.years, "months": delta.months, "days": delta.days,
                "total_days": (end - start).days}

    status = ("matured" if maturity_date < as_of else "matures_today" if maturity_date == as_of
              else "not_opened" if start_date > as_of else "active")
    return {"account_term": duration(start_date, maturity_date),
            "maturity_remaining": duration(min(as_of, maturity_date), maturity_date),
            "maturity_status": status, "maturity_as_of": as_of.isoformat()}


def schedule_dates(start, maturity, frequency):
    if frequency == 0:
        return [start]
    if frequency is None:
        return []
    dates = []
    index = 0
    # Anchor every occurrence to the original day (Jan 31 -> Feb 28 -> Mar 31).
    while (due := start + relativedelta(months=index * frequency)) < maturity:
        dates.append(due)
        index += 1
        if index > 1200:
            raise HTTPException(422, "Schedule exceeds 1200 instalments")
    return dates


def default_maturity(start, scheme):
    if not scheme.duration_months:
        return None
    if scheme.code == "PPF" and scheme.duration_months == 180:
        # Fifteen complete financial years after the opening financial year.
        financial_year_end = start.year + (1 if start.month >= 4 else 0)
        return date(financial_year_end + 15, 3, 31)
    return start + relativedelta(months=scheme.duration_months)


def create_account(db, payload, customer, scheme):
    fields = db.scalars(select(SchemeField).where(SchemeField.scheme_id == scheme.id)).all()
    values = payload.model_dump()
    values["nominee_name"] = payload.nominee_name or None
    allowed = {field.key for field in fields if field.key not in COMMON}
    if set(payload.custom_fields) - allowed:
        raise HTTPException(422, "Unknown scheme fields")
    for field in fields:
        value = values.get(field.key) if field.key in COMMON else payload.custom_fields.get(field.key)
        if field.required and not value:
            raise HTTPException(422, f"{field.label} is required")
        if value:
            try:
                if field.field_type == "number" and not Decimal(str(value)).is_finite():
                    raise ValueError()
                if field.field_type == "date":
                    date.fromisoformat(str(value))
            except (ValueError, InvalidOperation):
                raise HTTPException(422, f"Invalid {field.label}")
    if scheme.historical_only and not payload.historical_record:
        raise HTTPException(422, "This scheme only permits historical records; confirm explicitly")
    maturity = payload.maturity_date
    if maturity is None and scheme.duration_months:
        maturity = default_maturity(payload.start_date, scheme)
    kind = "discretionary" if payload.payment_mode == "flexible" else scheme.schedule_kind
    if kind == "discretionary" and payload.maturity_amount is not None:
        raise HTTPException(422, "Flexible deposit accounts do not have a fixed maturity amount")
    frequency = (None if kind == "discretionary" else
                 payload.frequency_months if payload.frequency_months is not None else scheme.frequency_months)
    if maturity and maturity <= payload.start_date:
        raise HTTPException(422, "Maturity date must be after start date")
    if kind == "collection" and frequency not in (None, 0) and not maturity:
        raise HTTPException(422, "Recurring schedules require a maturity date")
    if kind == "collection" and frequency is None:
        raise HTTPException(422, "Select a payment frequency")
    values.pop("historical_record")
    values.pop("payment_mode")
    values.update(maturity_date=maturity, frequency_months=frequency,
                  rule_snapshot={"code": scheme.code, "allow_partial": scheme.allow_partial,
                                 "schedule_kind": kind,
                                 "fields": [{"key": f.key, "required": f.required, "field_type": f.field_type} for f in fields]})
    account = Account(**values)
    db.add(account)
    db.flush()
    # Income schemes collect the initial deposit once. Interest payouts are not collections.
    frequency_for_generation = 0 if kind == "income" else frequency
    if kind == "discretionary":
        frequency_for_generation = None
    for sequence, due in enumerate(schedule_dates(payload.start_date, maturity, frequency_for_generation), 1):
        db.add(PaymentSchedule(account_id=account.id, sequence=sequence,
                               due_date=due, expected_amount=payload.amount))
    return account
