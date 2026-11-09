import csv
from datetime import date, timedelta
from decimal import Decimal
from io import StringIO

from dateutil.relativedelta import relativedelta
from fastapi import APIRouter, Query, Response
from sqlalchemy import case, func, select
from app.api.helpers import data, page, result
from app.api.payments import schedule_data, schedule_query, transaction_data, transaction_query
from app.core.config import today
from app.core.security import Actor, Admin, DB, audit
from app.models import Account, AuditLog, Customer, Notification, PaymentSchedule, PaymentTransaction, Scheme, User
from app.repositories import scope

router = APIRouter(tags=["Dashboards, notifications & reports"])


@router.get("/dashboard")
def dashboard(db: DB, actor: Actor, staff_id: str | None = None, scheme_id: str | None = None,
              post_office: str | None = None, date_from: date | None = None, date_to: date | None = None,
              status: str | None = None):
    day = today()
    accounts = scope(select(Account).join(Customer), actor).where(Account.deleted_at.is_(None), Customer.deleted_at.is_(None))
    customers = scope(select(Customer), actor).where(Customer.deleted_at.is_(None))
    if staff_id:
        accounts, customers = accounts.where(Customer.staff_id == staff_id), customers.where(Customer.staff_id == staff_id)
    if scheme_id:
        accounts = accounts.where(Account.scheme_id == scheme_id)
        customers = customers.where(Customer.id.in_(select(Account.customer_id).where(Account.scheme_id == scheme_id, Account.deleted_at.is_(None))))
    if post_office:
        accounts = accounts.where(Account.post_office.ilike(f"%{post_office}%"))
        customers = customers.where(Customer.post_office.ilike(f"%{post_office}%"))
    a = accounts.subquery()
    count = lambda stmt: db.scalar(select(func.count()).select_from(stmt.subquery()))
    base = transaction_query(actor, staff_id=staff_id, scheme_id=scheme_id, post_office=post_office).where(PaymentTransaction.reversed_at.is_(None))
    p = base.subquery()
    amount = lambda *conditions: str(db.scalar(select(func.coalesce(func.sum(p.c.amount), 0)).where(*conditions)))
    selected = transaction_query(actor, staff_id=staff_id, scheme_id=scheme_id, post_office=post_office,
                                 date_from=date_from or day.replace(day=1), date_to=date_to or day).where(PaymentTransaction.reversed_at.is_(None)).subquery()
    dues = schedule_query(actor, scheme_id=scheme_id, staff_id=staff_id, post_office=post_office,
                          status="outstanding", date_from=date_from, date_to=date_to)
    d = dues.subquery()
    overdue = db.scalar(select(func.count()).select_from(d).where(d.c.due_date < day))
    upcoming = db.scalar(select(func.count()).select_from(d).where(d.c.due_date >= day, d.c.due_date <= day + timedelta(days=7)))
    maturity = accounts.where(Account.maturity_date >= day, Account.maturity_date <= day + timedelta(days=30), Account.status == "active")
    scheme_distribution = db.execute(select(Scheme.name, func.count(a.c.id)).join(a, a.c.scheme_id == Scheme.id).group_by(Scheme.name)).all()
    c = customers.subquery()
    staff_distribution = db.execute(select(User.full_name, func.count(c.c.id)).join(c, c.c.staff_id == User.id).group_by(User.id, User.full_name)).all()
    collections = db.execute(select(User.full_name, func.sum(selected.c.amount)).join(selected, selected.c.staff_id == User.id).group_by(User.id, User.full_name)).all()
    scheme_collections = db.execute(select(Scheme.name, func.sum(selected.c.amount)).select_from(Scheme)
                                   .join(Account, Account.scheme_id == Scheme.id)
                                   .join(PaymentSchedule, PaymentSchedule.account_id == Account.id)
                                   .join(selected, selected.c.schedule_id == PaymentSchedule.id)
                                   .group_by(Scheme.id, Scheme.name)).all()
    month = func.date_trunc("month", p.c.payment_date)
    trends = db.execute(select(month, func.sum(p.c.amount)).where(p.c.payment_date >= day.replace(day=1) - relativedelta(months=5)).group_by(month).order_by(month)).all()
    attention = schedule_query(actor, scheme_id=scheme_id, staff_id=staff_id, post_office=post_office,
                               status=status or 'outstanding', date_from=date_from, date_to=date_to)
    due_rows = db.scalars(attention.order_by(PaymentSchedule.due_date).limit(8)).all()
    recent = db.scalars(base.order_by(PaymentTransaction.created_at.desc()).limit(5)).all()
    return {
        "total_staff": db.scalar(select(func.count()).select_from(User).where(User.role == "staff")) if actor.role == "super_admin" else None,
        "total_customers": count(customers), "total_accounts": count(accounts),
        "active_accounts": db.scalar(select(func.count()).select_from(a).where(a.c.status == "active")),
        "today_collections": amount(p.c.payment_date == day),
        "month_collections": amount(p.c.payment_date >= day.replace(day=1), p.c.payment_date <= day),
        "upcoming": upcoming, "overdue": overdue, "maturing": count(maturity),
        "scheme_distribution": [{"name": name, "value": value} for name, value in scheme_distribution],
        "staff_distribution": [{"name": name, "value": value} for name, value in staff_distribution],
        "staff_collections": [{"name": name, "value": str(value)} for name, value in collections],
        "scheme_collections": [{"name": name, "value": str(value)} for name, value in scheme_collections],
        "monthly_trends": [{"name": month.strftime("%b %Y"), "value": str(value)} for month, value in trends],
        "dues": [schedule_data(db, row) for row in due_rows],
        "maturing_accounts": [{**data(row), "customer_name": db.get(Customer, row.customer_id).full_name,
                              "scheme_name": db.get(Scheme, row.scheme_id).name} for row in db.scalars(maturity.order_by(Account.maturity_date).limit(8))],
        "recent_payments": [transaction_data(db, row) for row in recent],
    }


@router.get("/notifications")
def notifications(db: DB, actor: Actor, page_number: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    # Live ledger predicates make notifications accurate between scheduled refreshes.
    stmt = schedule_query(actor, status="outstanding", date_to=today() + timedelta(days=7))
    rows, total = page(db, stmt.order_by(PaymentSchedule.due_date), page_number, page_size)
    return result([schedule_data(db, row) for row in rows], total, page_number, page_size)


def csv_response(rows, name):
    stream = StringIO(newline="")
    if rows:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        # Neutralize formulas before opening exported text in a spreadsheet.
        for row in rows:
            writer.writerow({key: ("'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")) else value)
                             for key, value in row.items()})
    return Response("\ufeff" + stream.getvalue(), media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": f'attachment; filename="postmate-{name}.csv"', "Cache-Control": "no-store"})


@router.get("/reports/{report_type}")
def report(report_type: str, db: DB, actor: Actor, staff_id: str | None = None,
           scheme_id: str | None = None, post_office: str | None = None, status: str | None = None,
           date_from: date | None = None, date_to: date | None = None,
           page_number: int = Query(1, ge=1), page_size: int = Query(1000, ge=1, le=10000)):
    from fastapi import HTTPException
    if report_type == "payments":
        stmt = transaction_query(actor, staff_id=staff_id, scheme_id=scheme_id, post_office=post_office, date_from=date_from, date_to=date_to)
        rows = db.scalars(stmt.order_by(PaymentTransaction.payment_date.desc()).offset((page_number - 1) * page_size).limit(page_size)).all()
        values = [transaction_data(db, row) for row in rows]
    elif report_type == "dues":
        stmt = schedule_query(actor, staff_id=staff_id, scheme_id=scheme_id, post_office=post_office, status=status or "outstanding", date_from=date_from, date_to=date_to)
        rows = db.scalars(stmt.order_by(PaymentSchedule.due_date).offset((page_number - 1) * page_size).limit(page_size)).all()
        values = [schedule_data(db, row) for row in rows]
    else:
        raise HTTPException(404, "Report type must be payments or dues")
    audit(db, actor, "report.exported", report_type, details={"row_count": len(values), "page": page_number})
    return csv_response(values, report_type)


@router.get("/audit-logs")
def logs(db: DB, actor: Admin, q: str = "", page_number: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100)):
    stmt = select(AuditLog).where(AuditLog.action.ilike(f"%{q}%")).order_by(AuditLog.created_at.desc())
    rows, total = page(db, stmt, page_number, page_size)
    return result([data(row) for row in rows], total, page_number, page_size)
