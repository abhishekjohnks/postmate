from fastapi import APIRouter, HTTPException, Query
from datetime import datetime, timezone
from sqlalchemy import func, or_, select
from app.api.helpers import customer_data, page, result
from app.core.security import Actor, Admin, DB, audit, decrypt, encrypt
from app.models import Account, Customer, Scheme, User
from app.repositories import customer_for, scope
from app.schemas import AccountInput, CustomerInput, CustomerRegistration, Reason
from app.services.accounts import create_account

router = APIRouter(prefix="/customers", tags=["Customers"])


def assign(db, actor, requested):
    staff_id = actor.id if actor.role == "staff" else requested or actor.id
    staff = db.get(User, staff_id)
    if not staff or not staff.active:
        raise HTTPException(422, "Assigned staff member must be active")
    return staff_id


def apply(customer, payload, actor, db):
    values = payload.model_dump(exclude={"aadhaar", "pan", "staff_id"})
    for key, value in values.items():
        setattr(customer, key, value)
    customer.staff_id = assign(db, actor, payload.staff_id)
    # Omitted identity fields retain existing encrypted values during an edit.
    for kind in ("aadhaar", "pan"):
        if kind in payload.model_fields_set:
            setattr(customer, f"{kind}_encrypted", encrypt(getattr(payload, kind)))


@router.get("")
def customers(db: DB, actor: Actor, q: str = "", staff_id: str | None = None,
              post_office: str | None = None, active: bool | None = None,
              sort: str = "name", page_number: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    stmt = scope(select(Customer), actor).where(Customer.deleted_at.is_(None), or_(Customer.full_name.ilike(f"%{q}%"), Customer.phone.ilike(f"%{q}%"), Customer.customer_code.ilike(f"%{q}%")))
    if staff_id:
        stmt = stmt.where(Customer.staff_id == staff_id)
    if post_office:
        stmt = stmt.where(Customer.post_office.ilike(f"%{post_office}%"))
    if active is not None:
        stmt = stmt.where(Customer.active == active)
    stmt = stmt.order_by(Customer.created_at.desc() if sort == "newest" else Customer.full_name)
    rows, total = page(db, stmt, page_number, page_size)
    summaries = {}
    if rows:
        linked = db.execute(select(Account.customer_id, Scheme.code).join(Scheme).where(
            Account.customer_id.in_([row.id for row in rows]), Account.deleted_at.is_(None))).all()
        for customer_id, code in linked:
            summaries.setdefault(customer_id, []).append(code)
    return result([{**customer_data(row), "account_count": len(summaries.get(row.id, [])),
                    "schemes": sorted(set(summaries.get(row.id, [])))} for row in rows], total, page_number, page_size)


def add_accounts(db, actor, customer, drafts):
    if drafts and not customer.active:
        raise HTTPException(422, "Activate the customer before adding scheme accounts")
    for draft in drafts:
        scheme = db.get(Scheme, draft.scheme_id)
        if not scheme or not scheme.active:
            raise HTTPException(422, "Select an active scheme")
        payload = AccountInput(customer_id=customer.id, **draft.model_dump(exclude={"customer_id"}))
        account = create_account(db, payload, customer, scheme)
        audit(db, actor, "account.created", "customer_scheme_accounts", account.id)


@router.post("/register", status_code=201)
def register(payload: CustomerRegistration, db: DB, actor: Actor):
    if not payload.accounts:
        raise HTTPException(422, "Add at least one scheme account")
    customer = Customer()
    apply(customer, payload.customer, actor, db)
    db.add(customer)
    db.flush()
    add_accounts(db, actor, customer, payload.accounts)
    audit(db, actor, "customer.created", "customers", customer.id)
    db.flush()
    return customer_data(customer)


@router.put("/{customer_id}/registration")
def update_registration(customer_id: str, payload: CustomerRegistration, db: DB, actor: Actor):
    customer = customer_for(db, actor, customer_id, lock=True)
    if actor.role == "super_admin" and payload.customer.staff_id is None:
        payload.customer.staff_id = customer.staff_id
    apply(customer, payload.customer, actor, db)
    add_accounts(db, actor, customer, payload.accounts)
    audit(db, actor, "customer.updated", "customers", customer.id)
    db.flush()
    return customer_data(customer)


@router.post("", status_code=201)
def create(payload: CustomerInput, db: DB, actor: Actor):
    customer = Customer()
    apply(customer, payload, actor, db)
    db.add(customer)
    db.flush()
    audit(db, actor, "customer.created", "customers", customer.id)
    return customer_data(customer)


@router.get("/{customer_id}")
def detail(customer_id: str, db: DB, actor: Actor):
    return customer_data(customer_for(db, actor, customer_id))


@router.put("/{customer_id}")
def update(customer_id: str, payload: CustomerInput, db: DB, actor: Actor):
    customer = customer_for(db, actor, customer_id, lock=True)
    if actor.role == "super_admin" and payload.staff_id is None:
        payload.staff_id = customer.staff_id
    apply(customer, payload, actor, db)
    audit(db, actor, "customer.updated", "customers", customer.id)
    db.flush()
    return customer_data(customer)


@router.post("/{customer_id}/identity")
def identity(customer_id: str, db: DB, actor: Actor):
    customer = customer_for(db, actor, customer_id)
    audit(db, actor, "customer.identity_viewed", "customers", customer.id)
    return {"aadhaar": decrypt(customer.aadhaar_encrypted), "pan": decrypt(customer.pan_encrypted)}


@router.delete("/{customer_id}", status_code=204)
def delete_customer(customer_id: str, db: DB, actor: Admin):
    customer = customer_for(db, actor, customer_id, lock=True)
    customer.deleted_at = datetime.now(timezone.utc)
    customer.active = False
    audit(db, actor, "customer.deleted", "customers", customer.id)
