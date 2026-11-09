from datetime import date, datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Header, HTTPException, Query, Response
from sqlalchemy import func, or_, select
from app.api.helpers import data, page, result
from app.core.config import today
from app.core.security import Actor, Admin, DB, audit
from app.models import Account, Customer, Notification, PaymentReceipt, PaymentSchedule, PaymentTransaction, Scheme, User
from app.repositories import account_for, customer_for, schedule_for, scope
from app.schemas import FlexibleDepositInput, PaymentInput, Reason, ScheduleInput
from app.services.ledger import payment_status, record_payment, reverse_payment
from app.services.receipts import render_receipt

router = APIRouter(tags=["Payments & receipts"])


def schedule_data(db, row):
    account = db.get(Account, row.account_id)
    customer = db.get(Customer, account.customer_id)
    return {**data(row), "status": payment_status(row), "customer_name": customer.full_name,
            "customer_id": customer.id, "staff_id": customer.staff_id,
            "scheme_name": db.get(Scheme, account.scheme_id).name,
            "identifier": account.account_number or account.policy_number or account.account_code,
            "post_office": account.post_office,
            "outstanding": str(row.expected_amount - row.paid_amount)}


def schedule_query(actor, q="", account_id=None, scheme_id=None, staff_id=None, post_office=None,
                   status=None, date_from=None, date_to=None):
    stmt = scope(select(PaymentSchedule).join(Account).join(Customer), actor).where(
        Account.deleted_at.is_(None), Customer.deleted_at.is_(None))
    if q:
        stmt = stmt.where(or_(Customer.full_name.ilike(f"%{q}%"), Account.account_number.ilike(f"%{q}%"), Account.policy_number.ilike(f"%{q}%"), Account.cif_id.ilike(f"%{q}%")))
    for column, value in [(PaymentSchedule.account_id, account_id), (Account.scheme_id, scheme_id), (Customer.staff_id, staff_id)]:
        if value:
            stmt = stmt.where(column == value)
    if post_office:
        stmt = stmt.where(Account.post_office.ilike(f"%{post_office}%"))
    if date_from:
        stmt = stmt.where(PaymentSchedule.due_date >= date_from)
    if date_to:
        stmt = stmt.where(PaymentSchedule.due_date <= date_to)
    if status == "cancelled":
        stmt = stmt.where(PaymentSchedule.cancelled.is_(True))
    elif status:
        stmt = stmt.where(PaymentSchedule.cancelled.is_(False))
        if status == "paid":
            stmt = stmt.where(PaymentSchedule.paid_amount >= PaymentSchedule.expected_amount)
        else:
            stmt = stmt.where(PaymentSchedule.paid_amount < PaymentSchedule.expected_amount)
            if status == "overdue":
                stmt = stmt.where(PaymentSchedule.due_date < today())
            elif status == "partially_paid":
                stmt = stmt.where(PaymentSchedule.paid_amount > 0, PaymentSchedule.due_date >= today())
            elif status == "due":
                stmt = stmt.where(PaymentSchedule.due_date == today(), PaymentSchedule.paid_amount == 0)
            elif status == "upcoming":
                stmt = stmt.where(PaymentSchedule.due_date > today(), PaymentSchedule.paid_amount == 0)
            elif status == "outstanding":
                stmt = stmt.where(Account.status == "active", Customer.active.is_(True))
            else:
                raise HTTPException(422, "Unknown payment status")
    return stmt


@router.get("/schedules")
def schedules(db: DB, actor: Actor, q: str = "", account_id: str | None = None,
              scheme_id: str | None = None, staff_id: str | None = None, post_office: str | None = None,
              status: str | None = None, date_from: date | None = None, date_to: date | None = None,
              page_number: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    stmt = schedule_query(actor, q, account_id, scheme_id, staff_id, post_office, status, date_from, date_to)
    rows, total = page(db, stmt.order_by(PaymentSchedule.due_date, PaymentSchedule.sequence), page_number, page_size)
    return result([schedule_data(db, row) for row in rows], total, page_number, page_size)


@router.post("/schedules", status_code=201)
def add_schedule(payload: ScheduleInput, db: DB, actor: Actor):
    account = account_for(db, actor, payload.account_id, lock=True)
    if account.status != "active":
        raise HTTPException(409, "Account is inactive")
    if account.rule_snapshot["schedule_kind"] != "discretionary":
        raise HTTPException(422, "Manual schedules are only allowed for discretionary deposits")
    if payload.due_date < account.start_date or (account.maturity_date and payload.due_date >= account.maturity_date):
        raise HTTPException(422, "Due date must fall within the account term")
    sequence = (db.scalar(select(func.max(PaymentSchedule.sequence)).where(PaymentSchedule.account_id == account.id)) or 0) + 1
    row = PaymentSchedule(**payload.model_dump(), sequence=sequence)
    db.add(row)
    db.flush()
    audit(db, actor, "schedule.created", "payment_schedules", row.id)
    return schedule_data(db, row)


@router.post("/schedules/{schedule_id}/cancel")
def cancel_schedule(schedule_id: str, payload: Reason, db: DB, actor: Admin):
    row = schedule_for(db, actor, schedule_id, lock=True)
    if row.paid_amount:
        raise HTTPException(409, "Reverse payments before cancelling the schedule")
    row.cancelled, row.remarks = True, payload.reason
    audit(db, actor, "schedule.cancelled", "payment_schedules", row.id, {"reason": payload.reason})
    return schedule_data(db, row)


def transaction_data(db, row):
    schedule = db.get(PaymentSchedule, row.schedule_id)
    account = db.get(Account, schedule.account_id)
    receipt = db.scalar(select(PaymentReceipt).where(PaymentReceipt.transaction_id == row.id))
    return {**data(row, {"request_fingerprint", "idempotency_key"}),
            "customer_name": db.get(Customer, account.customer_id).full_name,
            "scheme_name": db.get(Scheme, account.scheme_id).name,
            "staff_name": db.get(User, row.staff_id).full_name,
            "identifier": account.account_number or account.policy_number or account.account_code,
            "sequence": schedule.sequence, "receipt_id": receipt.id,
            "receipt_number": receipt.receipt_number}


def transaction_query(actor, q="", staff_id=None, scheme_id=None, post_office=None, date_from=None, date_to=None, account_id=None):
    stmt = scope(select(PaymentTransaction).join(PaymentSchedule).join(Account).join(Customer), actor)
    if q:
        stmt = stmt.where(or_(Customer.full_name.ilike(f"%{q}%"), Account.account_number.ilike(f"%{q}%"), Account.policy_number.ilike(f"%{q}%"), Account.cif_id.ilike(f"%{q}%")))
    for column, value in [(PaymentTransaction.staff_id, staff_id), (Account.scheme_id, scheme_id), (Account.id, account_id)]:
        if value:
            stmt = stmt.where(column == value)
    if post_office:
        stmt = stmt.where(Account.post_office.ilike(f"%{post_office}%"))
    if date_from:
        stmt = stmt.where(PaymentTransaction.payment_date >= date_from)
    if date_to:
        stmt = stmt.where(PaymentTransaction.payment_date <= date_to)
    return stmt


@router.get("/payments")
def payments(db: DB, actor: Actor, q: str = "", staff_id: str | None = None,
             scheme_id: str | None = None, post_office: str | None = None,
             date_from: date | None = None, date_to: date | None = None, account_id: str | None = None,
             page_number: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), include_deleted: bool = False):
    stmt = transaction_query(actor, q, staff_id, scheme_id, post_office, date_from, date_to, account_id)
    if not include_deleted:
        stmt = stmt.where(PaymentTransaction.deleted_at.is_(None))
    rows, total = page(db, stmt.order_by(PaymentTransaction.created_at.desc()), page_number, page_size)
    return result([transaction_data(db, row) for row in rows], total, page_number, page_size)


@router.post("/payments", status_code=201)
def create_payment(payload: PaymentInput, db: DB, actor: Actor,
                   idempotency_key: Annotated[str, Header(min_length=16, max_length=100)]):
    transaction = record_payment(db, actor, payload, idempotency_key)
    return transaction_data(db, transaction)


@router.post("/payments/flexible", status_code=201)
def create_flexible_deposit(payload: FlexibleDepositInput, db: DB, actor: Actor,
                            idempotency_key: Annotated[str, Header(min_length=16, max_length=100)]):
    account = account_for(db, actor, payload.account_id)
    customer_for(db, actor, account.customer_id, lock=True)
    account = account_for(db, actor, account.id, lock=True)
    if account.rule_snapshot.get("schedule_kind") != "discretionary":
        raise HTTPException(422, "Direct deposits are only available for flexible accounts")
    previous = db.scalar(select(PaymentTransaction).where(PaymentTransaction.idempotency_key == idempotency_key))
    if previous:
        schedule = db.get(PaymentSchedule, previous.schedule_id)
        if previous.staff_id != actor.id or schedule.account_id != account.id:
            raise HTTPException(409, "Idempotency key already used for a different payment")
    else:
        if account.maturity_date and payload.payment_date >= account.maturity_date:
            raise HTTPException(422, "Payment date must fall before account maturity")
        sequence = (db.scalar(select(func.max(PaymentSchedule.sequence)).where(
            PaymentSchedule.account_id == account.id)) or 0) + 1
        schedule = PaymentSchedule(account_id=account.id, sequence=sequence,
                                   due_date=payload.payment_date, expected_amount=payload.amount,
                                   remarks=payload.remarks)
        db.add(schedule)
        db.flush()
        audit(db, actor, "schedule.created", "payment_schedules", schedule.id)
    payment = PaymentInput(schedule_id=schedule.id, **payload.model_dump(exclude={"account_id"}))
    return transaction_data(db, record_payment(db, actor, payment, idempotency_key))


@router.delete("/payments/{transaction_id}", status_code=204)
def delete_payment(transaction_id: str, db: DB, actor: Admin):
    transaction = db.get(PaymentTransaction, transaction_id)
    if not transaction:
        raise HTTPException(404, "Payment not found")
    schedule_for(db, actor, transaction.schedule_id, lock=True)
    db.refresh(transaction)
    if transaction.deleted_at:
        return
    if not transaction.reversed_at:
        reverse_payment(db, actor, transaction, "Transaction deleted by user")
    transaction.deleted_at = datetime.now(timezone.utc)
    audit(db, actor, "payment.deleted", "payment_transactions", transaction.id)


@router.post("/payments/{transaction_id}/reverse")
def reverse(transaction_id: str, payload: Reason, db: DB, actor: Admin):
    transaction = db.get(PaymentTransaction, transaction_id)
    if not transaction:
        raise HTTPException(404, "Payment not found")
    reverse_payment(db, actor, transaction, payload.reason)
    return transaction_data(db, transaction)


@router.get("/receipts/{receipt_id}/pdf")
def receipt_pdf(receipt_id: str, db: DB, actor: Actor):
    receipt = db.get(PaymentReceipt, receipt_id)
    if not receipt:
        raise HTTPException(404, "Receipt not found")
    transaction = db.get(PaymentTransaction, receipt.transaction_id)
    schedule_for(db, actor, transaction.schedule_id)
    # Atomic counter; a reprint always uses the immutable original receipt snapshot.
    from sqlalchemy import update
    db.execute(update(PaymentReceipt).where(PaymentReceipt.id == receipt.id).values(
        download_count=PaymentReceipt.download_count + 1, last_downloaded_at=datetime.now(timezone.utc)))
    audit(db, actor, "receipt.downloaded", "payment_receipts", receipt.id)
    content = render_receipt(receipt, transaction.reversed_at)
    return Response(content, media_type="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="PostMate-receipt-{transaction.payment_date.isoformat()}.pdf"', "Cache-Control": "no-store"})
