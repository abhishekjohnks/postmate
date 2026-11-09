from datetime import date, datetime
from decimal import Decimal
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from app.core.security import decrypt


def data(record, exclude=()):
    return jsonable_encoder({column.name: getattr(record, column.name) for column in record.__table__.columns
                             if column.name not in exclude}, custom_encoder={Decimal: str})


def customer_data(customer):
    result = data(customer, {"aadhaar_encrypted", "pan_encrypted"})
    for kind in ("aadhaar", "pan"):
        value = decrypt(getattr(customer, f"{kind}_encrypted"))
        result[kind] = ("*" * (len(value) - 4) + value[-4:]) if value else None
    return result


def page(db, statement, number, size):
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery()))
    return db.scalars(statement.offset((number - 1) * size).limit(size)).all(), total


def result(items, total, number, size):
    return {"items": items, "total": total, "page": number, "page_size": size}
