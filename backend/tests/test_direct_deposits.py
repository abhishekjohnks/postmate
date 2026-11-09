from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.config import today
from app.models import Account, PaymentSchedule, PaymentTransaction
from app.services.deposits import deposit_summary, financial_year
from test_workflows import create_account, create_customer


def deposit(client, headers, account, amount, paid_date, key=None):
    return client.post('/api/payments/flexible',
                       headers={**headers, 'Idempotency-Key': key or str(uuid4())},
                       json={'account_id': account['id'], 'amount': amount,
                             'payment_date': paid_date.isoformat(), 'method': 'cash'})


@pytest.mark.parametrize('code', ['SSA', 'PPF'])
def test_direct_deposit_receipt_replay_totals_and_ownership(client, db, actors, code):
    owner = actors['test_staff_a']['headers']
    other = actors['test_staff_b']['headers']
    account = create_account(client, db, owner, create_customer(client, owner), code)
    key = str(uuid4())
    response = deposit(client, owner, account, '100', today(), key)
    assert response.status_code == 201, response.text
    payment = response.json()
    assert payment['receipt_id']
    assert deposit(client, owner, account, '100', today(), key).json()['id'] == payment['id']
    assert deposit(client, owner, account, '200', today(), key).status_code == 409
    assert deposit(client, other, account, '100', today()).status_code == 404
    assert db.scalar(select(func.count()).select_from(PaymentSchedule).where(
        PaymentSchedule.account_id == account['id'])) == 1
    assert client.get('/api/receipts/' + payment['receipt_id'] + '/pdf', headers=owner).content.startswith(b'%PDF-')
    detail = client.get('/api/accounts/' + account['id'], headers=owner).json()
    assert Decimal(detail['total_deposited']) == 100
    assert detail['annual_deposits'][-1]['status'] == 'minimum_pending'
    assert client.delete('/api/payments/' + payment['id'], headers=actors['test_admin']['headers']).status_code == 204
    detail = client.get('/api/accounts/' + account['id'], headers=owner).json()
    assert Decimal(detail['total_deposited']) == 0


@pytest.mark.parametrize('code', ['SSA', 'PPF'])
def test_limit_applies_to_direct_and_scheduled_payments_and_reversal(client, db, actors, code):
    owner = actors['test_staff_a']['headers']
    account = create_account(client, db, owner, create_customer(client, owner), code)
    first = deposit(client, owner, account, '149900', today()).json()
    assert deposit(client, owner, account, '100', today()).status_code == 201
    count = db.scalar(select(func.count()).select_from(PaymentSchedule).where(PaymentSchedule.account_id == account['id']))
    assert deposit(client, owner, account, '0.01', today()).status_code == 422
    assert db.scalar(select(func.count()).select_from(PaymentSchedule).where(PaymentSchedule.account_id == account['id'])) == count
    schedule = client.post('/api/schedules', headers=owner, json={
        'account_id': account['id'], 'due_date': today().isoformat(),
        'expected_amount': '100', 'remarks': 'Test agreed deposit'}).json()
    response = client.post('/api/payments', headers={**owner, 'Idempotency-Key': str(uuid4())}, json={
        'schedule_id': schedule['id'], 'amount': '100', 'payment_date': today().isoformat(), 'method': 'cash'})
    assert response.status_code == 422
    assert client.post('/api/payments/' + first['id'] + '/reverse', headers=actors['test_admin']['headers'],
                       json={'reason': 'Correct erroneous deposit'}).status_code == 200
    assert deposit(client, owner, account, '100', today()).status_code == 201


def test_financial_year_status_boundaries_and_closed_year_shortfall(client, db, actors):
    owner = actors['test_staff_a']['headers']
    current, _ = financial_year(today())
    start = date(current.year - 1, 4, 1)
    account = create_account(client, db, owner, create_customer(client, owner), 'SSA', start_date=start.isoformat())
    assert deposit(client, owner, account, '100', start).status_code == 201
    assert deposit(client, owner, account, '500', current).status_code == 201
    summary = deposit_summary(db, db.get(Account, account['id']))
    assert Decimal(summary['total_deposited']) == 600
    assert [row['status'] for row in summary['annual_deposits']] == ['shortfall_review', 'minimum_met']
    assert db.get(Account, account['id']).status == 'active'
    assert financial_year(date(2026, 3, 31))[0] == date(2025, 4, 1)
    assert financial_year(date(2026, 4, 1))[0] == date(2026, 4, 1)


def test_rejected_direct_deposit_rolls_back_schedule(client, db, actors):
    owner = actors['test_staff_a']['headers']
    customer = create_customer(client, owner)
    fixed = create_account(client, db, owner, customer, 'RD')
    assert deposit(client, owner, fixed, '500', today()).status_code == 422
    flexible = create_account(client, db, owner, customer, 'SSA')
    assert deposit(client, owner, flexible, '100', today() + timedelta(days=1)).status_code == 422
    assert db.scalar(select(func.count()).select_from(PaymentSchedule).where(PaymentSchedule.account_id == flexible['id'])) == 0
