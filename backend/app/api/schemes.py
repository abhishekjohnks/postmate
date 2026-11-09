from fastapi import APIRouter, HTTPException
from sqlalchemy import delete, select
from app.api.helpers import data
from app.core.security import Actor, Admin, DB, audit
from app.models import Scheme, SchemeField
from app.schemas import SchemeInput

router = APIRouter(prefix="/schemes", tags=["Scheme configuration"])


def serialize(db, scheme):
    return {**data(scheme), "fields": [data(field) for field in db.scalars(select(SchemeField).where(SchemeField.scheme_id == scheme.id).order_by(SchemeField.created_at))]}


def apply(db, scheme, payload):
    if len({field.key for field in payload.fields}) != len(payload.fields):
        raise HTTPException(422, "Scheme field keys must be unique")
    reserved = {"customer_id", "scheme_id", "start_date", "maturity_date", "amount", "frequency_months", "post_office", "remarks", "status"}
    if any(field.key in reserved for field in payload.fields):
        raise HTTPException(422, "Use the common account form for reserved fields")
    for key, value in payload.model_dump(exclude={"fields"}).items():
        setattr(scheme, key, value)
    if scheme.schedule_kind == "discretionary":
        scheme.frequency_months = None
    db.add(scheme)
    db.flush()
    db.execute(delete(SchemeField).where(SchemeField.scheme_id == scheme.id))
    db.add_all([SchemeField(scheme_id=scheme.id, **field.model_dump()) for field in payload.fields])
    db.flush()


@router.get("")
def list_schemes(db: DB, actor: Actor):
    return [serialize(db, scheme) for scheme in db.scalars(select(Scheme).order_by(Scheme.code))]


@router.post("", status_code=201)
def create(payload: SchemeInput, db: DB, actor: Admin):
    scheme = Scheme()
    apply(db, scheme, payload)
    audit(db, actor, "scheme.created", "schemes", scheme.id)
    return serialize(db, scheme)


@router.put("/{scheme_id}")
def update(scheme_id: str, payload: SchemeInput, db: DB, actor: Admin):
    scheme = db.get(Scheme, scheme_id)
    if not scheme:
        raise HTTPException(404, "Scheme not found")
    apply(db, scheme, payload)
    audit(db, actor, "scheme.updated", "schemes", scheme.id)
    return serialize(db, scheme)
