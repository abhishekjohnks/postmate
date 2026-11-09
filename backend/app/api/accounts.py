from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from sqlalchemy import or_, select
from app.api.helpers import data, page, result
from app.core.security import Actor, Admin, DB, audit
from app.models import Account, Customer, Scheme
from app.repositories import account_for, customer_for, scope
from app.schemas import AccountInput, AccountUpdate
from app.services.accounts import account_timeline, create_account
from app.services.deposits import deposit_summary

router = APIRouter(prefix="/accounts", tags=["Scheme accounts"])


def serialize(db, account):
    return {**data(account), **account_timeline(account.start_date, account.maturity_date),
            **deposit_summary(db, account),
            "customer_name": db.get(Customer, account.customer_id).full_name,
            "scheme_name": db.get(Scheme, account.scheme_id).name}


@router.get("")
def accounts(db: DB, actor: Actor, q: str = "", customer_id: str | None = None,
             scheme_id: str | None = None, staff_id: str | None = None, post_office: str | None = None,
             maturity_from: str | None = None, maturity_to: str | None = None, status: str | None = None,
             page_number: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    from datetime import date
    stmt = scope(select(Account).join(Customer), actor).where(Account.deleted_at.is_(None), Customer.deleted_at.is_(None), or_(
        Customer.full_name.ilike(f"%{q}%"), Account.account_number.ilike(f"%{q}%"),
        Account.policy_number.ilike(f"%{q}%"), Account.cif_id.ilike(f"%{q}%"), Account.account_code.ilike(f"%{q}%")))
    for column, value in [(Account.customer_id, customer_id), (Account.scheme_id, scheme_id),
                          (Customer.staff_id, staff_id), (Account.status, status)]:
        if value:
            stmt = stmt.where(column == value)
    if post_office:
        stmt = stmt.where(Account.post_office.ilike(f"%{post_office}%"))
    try:
        if maturity_from:
            stmt = stmt.where(Account.maturity_date >= date.fromisoformat(maturity_from))
        if maturity_to:
            stmt = stmt.where(Account.maturity_date <= date.fromisoformat(maturity_to))
    except ValueError:
        raise HTTPException(422, "Use ISO dates")
    rows, total = page(db, stmt.order_by(Account.created_at.desc()), page_number, page_size)
    return result([serialize(db, row) for row in rows], total, page_number, page_size)


@router.post("", status_code=201)
def create(payload: AccountInput, db: DB, actor: Actor):
    customer = customer_for(db, actor, payload.customer_id, lock=True)
    scheme = db.get(Scheme, payload.scheme_id)
    if not customer.active or not scheme or not scheme.active:
        raise HTTPException(422, "Customer and scheme must be active")
    account = create_account(db, payload, customer, scheme)
    audit(db, actor, "account.created", "customer_scheme_accounts", account.id)
    return serialize(db, account)


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: str, db: DB, actor: Admin):
    account = account_for(db, actor, account_id)
    customer_for(db, actor, account.customer_id, lock=True)
    account = account_for(db, actor, account_id, lock=True)
    account.deleted_at = datetime.now(timezone.utc)
    account.status = "inactive"
    audit(db, actor, "account.deleted", "customer_scheme_accounts", account.id)


@router.get("/{account_id}")
def detail(account_id: str, db: DB, actor: Actor):
    return serialize(db, account_for(db, actor, account_id))


@router.patch("/{account_id}")
def update(account_id: str, payload: AccountUpdate, db: DB, actor: Actor):
    account = account_for(db, actor, account_id, lock=True)
    if account.rule_snapshot.get("schedule_kind") == "discretionary" and payload.maturity_amount is not None:
        raise HTTPException(422, "Flexible deposit accounts do not have a fixed maturity amount")
    account.status, account.remarks = payload.status, payload.remarks
    if "nominee_name" in payload.model_fields_set:
        account.nominee_name = payload.nominee_name or None
    if "maturity_amount" in payload.model_fields_set:
        account.maturity_amount = payload.maturity_amount
    audit(db, actor, "account.updated", "customer_scheme_accounts", account.id)
    return serialize(db, account)
