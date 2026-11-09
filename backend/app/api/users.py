from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select
from app.api.helpers import data, page, result
from app.core.security import Admin, DB, audit, passwords
from app.models import StaffProfile, User
from app.schemas import StaffCreate, StaffUpdate

router = APIRouter(prefix="/users", tags=["Staff"])


def serialize(db, user):
    value = data(user, {"password_hash", "token_version"})
    profile = db.scalar(select(StaffProfile).where(StaffProfile.user_id == user.id))
    value["profile"] = data(profile) if profile else None
    return value


@router.get("")
def users(db: DB, actor: Admin, q: str = "", page_number: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    statement = select(User).where(User.full_name.ilike(f"%{q}%")).order_by(User.full_name)
    rows, total = page(db, statement, page_number, page_size)
    return result([serialize(db, row) for row in rows], total, page_number, page_size)


@router.post("", status_code=201)
def create(payload: StaffCreate, db: DB, actor: Admin):
    user = User(username=payload.username.lower(), full_name=payload.full_name,
                password_hash=passwords.hash(payload.password), role="staff")
    db.add(user)
    db.flush()
    db.add(StaffProfile(user_id=user.id, phone=payload.phone, post_office=payload.post_office, agent_id=payload.agent_id))
    audit(db, actor, "staff.created", "users", user.id)
    db.flush()
    return serialize(db, user)


@router.patch("/{user_id}")
def update(user_id: str, payload: StaffUpdate, db: DB, actor: Admin):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "Staff member not found")
    if user.role == "super_admin":
        raise HTTPException(403, "The Super Admin cannot be modified through staff management")
    user.full_name, user.active = payload.full_name, payload.active
    user.role = "staff"
    user.token_version += 1
    if payload.password:
        user.password_hash = passwords.hash(payload.password)
    profile = db.scalar(select(StaffProfile).where(StaffProfile.user_id == user_id))
    if not profile:
        profile = StaffProfile(user_id=user_id)
        db.add(profile)
    profile.phone, profile.post_office, profile.agent_id = payload.phone, payload.post_office, payload.agent_id
    audit(db, actor, "staff.updated", "users", user.id)
    db.flush()
    return serialize(db, user)
