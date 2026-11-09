import hashlib
from datetime import datetime, timezone
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from app.core.config import today
from app.core.security import audit
from app.models import Account, Customer, PaymentReceipt, PaymentTransaction, Scheme, User
from app.repositories import account_for, customer_for, schedule_for
from app.services.deposits import check_annual_limit


def payment_status(schedule, as_of=None):
    as_of = as_of or today()
    if schedule.cancelled:
        return "cancelled"
    if schedule.paid_amount >= schedule.expected_amount:
        return "paid"
    if schedule.due_date < as_of:
        return "overdue"
    if schedule.paid_amount > 0:
        return "partially_paid"
    return "due" if schedule.due_date == as_of else "upcoming"


def record_payment(db, actor, payload, key):
    fingerprint = hashlib.sha256(payload.model_dump_json().encode()).hexdigest()
    schedule = schedule_for(db, actor, payload.schedule_id)
    initial_account = db.get(Account, schedule.account_id)
    # Entity deletion and collection use the same parent-first lock order.
    customer_for(db, actor, initial_account.customer_id, lock=True)
    account_for(db, actor, initial_account.id, lock=True)
    schedule = schedule_for(db, actor, payload.schedule_id, lock=True)
    previous = db.scalar(select(PaymentTransaction).where(PaymentTransaction.idempotency_key == key))
    if previous:
        if previous.staff_id != actor.id or previous.request_fingerprint != fingerprint:
            raise HTTPException(409, "Idempotency key already used for a different payment")
        return previous
    account = db.get(Account, schedule.account_id)
    if schedule.cancelled or account.status != "active":
        raise HTTPException(409, "Schedule or account is not active")
    customer = db.get(Customer, account.customer_id)
    if not customer.active:
        raise HTTPException(409, "Customer is inactive")
    outstanding = schedule.expected_amount - schedule.paid_amount
    if payload.amount > outstanding:
        raise HTTPException(422, "Amount exceeds the outstanding instalment balance")
    if payload.amount < outstanding and not account.rule_snapshot.get("allow_partial", False):
        raise HTTPException(422, "Partial payments are disabled for this account")
    if payload.payment_date > today() or payload.payment_date < account.start_date:
        raise HTTPException(422, "Payment date must be between account opening and today")
    check_annual_limit(db, account, payload.payment_date, payload.amount)
    transaction = PaymentTransaction(**payload.model_dump(), staff_id=actor.id,
                                     idempotency_key=key, request_fingerprint=fingerprint)
    transaction.reference = transaction.reference or None
    db.add(transaction)
    db.flush()
    schedule.paid_amount += payload.amount
    scheme = db.get(Scheme, account.scheme_id)
    snapshot = {
        "customer_name": customer.full_name, "customer_code": customer.customer_code,
        "scheme": scheme.name, "account_number": account.account_number,
        "policy_number": account.policy_number, "cif_id": account.cif_id,
        "staff_name": actor.full_name, "staff_id": actor.id, "sequence": schedule.sequence,
        "amount": str(payload.amount), "payment_date": payload.payment_date.isoformat(),
        "method": payload.method, "reference": payload.reference,
        "due_date": schedule.due_date.isoformat(), "outstanding": str(outstanding - payload.amount),
    }
    db.add(PaymentReceipt(transaction_id=transaction.id, snapshot=snapshot))
    audit(db, actor, "payment.recorded", "payment_transactions", transaction.id)
    db.flush()
    return transaction


def reverse_payment(db, actor, transaction, reason):
    schedule = schedule_for(db, actor, transaction.schedule_id, lock=True)
    # Refresh after the schedule lock so concurrent reversals cannot subtract twice.
    db.refresh(transaction)
    if transaction.reversed_at:
        raise HTTPException(409, "Payment already reversed")
    transaction.reversed_at = datetime.now(timezone.utc)
    transaction.reversed_by = actor.id
    transaction.reversal_reason = reason
    schedule.paid_amount -= transaction.amount
    audit(db, actor, "payment.reversed", "payment_transactions", transaction.id, {"reason": reason})
