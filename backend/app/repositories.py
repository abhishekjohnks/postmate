from fastapi import HTTPException
from sqlalchemy import select
from app.models import Account, Customer, PaymentSchedule


def scope(stmt, actor):
    return stmt.where(Customer.staff_id == actor.id) if actor.role == "staff" else stmt


def customer_for(db, actor, customer_id, lock=False):
    stmt = scope(select(Customer).where(Customer.id == customer_id, Customer.deleted_at.is_(None)), actor)
    if lock:
        stmt = stmt.with_for_update(of=Customer)
    customer = db.scalar(stmt.execution_options(populate_existing=True))
    if not customer:
        raise HTTPException(404, "Customer not found")
    return customer


def account_for(db, actor, account_id, lock=False):
    stmt = scope(select(Account).join(Customer).where(Account.id == account_id,
                  Account.deleted_at.is_(None), Customer.deleted_at.is_(None)), actor)
    if lock:
        stmt = stmt.with_for_update(of=Account)
    account = db.scalar(stmt.execution_options(populate_existing=True))
    if not account:
        raise HTTPException(404, "Account not found")
    return account


def schedule_for(db, actor, schedule_id, lock=False):
    stmt = scope(select(PaymentSchedule).join(Account).join(Customer).where(PaymentSchedule.id == schedule_id), actor)
    if lock:
        stmt = stmt.with_for_update(of=PaymentSchedule)
    schedule = db.scalar(stmt)
    if not schedule:
        raise HTTPException(404, "Payment schedule not found")
    return schedule
