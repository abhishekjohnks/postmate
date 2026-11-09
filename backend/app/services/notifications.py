from datetime import timedelta
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from app.core.config import today
from app.db.session import SessionLocal
from app.models import Account, Customer, Notification, PaymentSchedule


def refresh_notifications():
    with SessionLocal.begin() as db:
        cutoff = today() + timedelta(days=7)
        schedules = db.scalars(select(PaymentSchedule).join(Account).join(Customer).where(
            PaymentSchedule.due_date <= cutoff, PaymentSchedule.cancelled.is_(False),
            PaymentSchedule.paid_amount < PaymentSchedule.expected_amount,
            Account.status == "active", Customer.active.is_(True),
            Account.deleted_at.is_(None), Customer.deleted_at.is_(None))).all()
        live = set()
        for schedule in schedules:
            live.add(schedule.id)
            kind = "overdue" if schedule.due_date < today() else "due" if schedule.due_date == today() else "upcoming"
            stmt = insert(Notification).values(schedule_id=schedule.id, kind=kind, resolved=False)
            db.execute(stmt.on_conflict_do_update(index_elements=[Notification.schedule_id],
                                                  set_={"kind": kind, "resolved": False}))
        for notification in db.scalars(select(Notification).where(Notification.resolved.is_(False))):
            if notification.schedule_id not in live:
                notification.resolved = True
