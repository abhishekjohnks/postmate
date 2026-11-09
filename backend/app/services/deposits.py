from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from fastapi import HTTPException
from sqlalchemy import select

from app.core.config import today
from app.models import PaymentSchedule, PaymentTransaction


def financial_year(day):
    year = day.year if day.month >= 4 else day.year - 1
    return date(year, 4, 1), date(year + 1, 4, 1)


def deposit_rows(db, account):
    return db.execute(select(PaymentTransaction.payment_date, PaymentTransaction.amount)
                      .join(PaymentSchedule).where(
                          PaymentSchedule.account_id == account.id,
                          PaymentTransaction.reversed_at.is_(None),
                          PaymentTransaction.deleted_at.is_(None))).all()


def check_annual_limit(db, account, payment_date, amount):
    if account.rule_snapshot.get('code') not in {'SSA', 'PPF'}:
        return
    start, end = financial_year(payment_date)
    paid = sum((row.amount for row in deposit_rows(db, account)
                if start <= row.payment_date < end), Decimal('0'))
    if paid + amount > Decimal('150000'):
        raise HTTPException(422, f"Annual deposit limit is INR 1,50,000 for financial year {start.year}-{end.year}. Already deposited INR {paid:,.2f}.")


def deposit_summary(db, account, as_of=None):
    as_of = as_of or today()
    rows = deposit_rows(db, account)
    total = sum((row.amount for row in rows), Decimal('0'))
    result = {'total_deposited': str(total), 'annual_deposits': []}
    code = account.rule_snapshot.get('code')
    if code not in {'SSA', 'PPF'}:
        return result
    minimum = Decimal('250' if code == 'SSA' else '500')
    maximum = Decimal('150000')
    # Only required deposit years are reviewed, not SSA's final six years.
    deposit_end = (account.start_date + relativedelta(years=15) if code == 'SSA'
                   else account.maturity_date)
    first, _ = financial_year(account.start_date)
    current, _ = financial_year(as_of)
    grouped = {}
    for row in rows:
        start, _ = financial_year(row.payment_date)
        grouped[start] = grouped.get(start, Decimal('0')) + row.amount
    year = first
    while year <= current and (deposit_end is None or year < deposit_end):
        end = date(year.year + 1, 4, 1)
        paid = grouped.get(year, Decimal('0'))
        complete = end <= as_of
        result['annual_deposits'].append({
            'financial_year': f'{year.year}-{end.year}', 'deposited': str(paid),
            'minimum': str(minimum), 'maximum': str(maximum),
            'remaining_to_minimum': str(max(minimum - paid, Decimal('0'))),
            'remaining_capacity': str(max(maximum - paid, Decimal('0'))),
            'status': ('over_limit' if paid > maximum else
                       'shortfall_review' if complete and paid < minimum else
                       'minimum_pending' if paid < minimum else 'minimum_met'),
            'complete': complete,
        })
        year = end
    return result
