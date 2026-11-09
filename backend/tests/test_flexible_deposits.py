from datetime import date, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.core.config import today
from app.models import PaymentSchedule
from app.services.accounts import default_maturity
from test_workflows import create_account, create_customer


@pytest.mark.parametrize('code,extra', [('SSA', {}), ('PPF', {}), ('RD', {'payment_mode': 'flexible'})])
def test_irregular_deposits_without_monthly_dues(client, db, actors, code, extra):
    headers = actors['test_staff_a']['headers']
    customer = create_customer(client, headers)
    start = today() - timedelta(days=100)
    account = create_account(client, db, headers, customer, code,
                             start_date=start.isoformat(), **extra)
    assert account['frequency_months'] is None
    assert account['rule_snapshot']['schedule_kind'] == 'discretionary'
    if code == 'SSA':
        assert account['maturity_date'] == start.replace(year=start.year + 21).isoformat()
    elif code == 'PPF':
        assert account['maturity_date'] == date(start.year + (1 if start.month >= 4 else 0) + 15, 3, 31).isoformat()
    assert account['maturity_amount'] is None
    assert client.patch('/api/accounts/' + account['id'], headers=headers,
                        json={'status': 'active', 'maturity_amount': '10000'}).status_code == 422
    assert db.scalar(select(func.count()).select_from(PaymentSchedule).where(
        PaymentSchedule.account_id == account['id'])) == 0
    for offset, amount in [(0, '100.00'), (90, '500.00')]:
        deposit_date = (start + timedelta(days=offset)).isoformat()
        body = {'account_id': account['id'], 'due_date': deposit_date,
                'expected_amount': amount, 'remarks': 'Agreed flexible deposit'}
        assert client.post('/api/schedules', headers=actors['test_staff_b']['headers'], json=body).status_code == 404
        response = client.post('/api/schedules', headers=headers, json=body)
        assert response.status_code == 201, response.text
        payment = client.post('/api/payments', headers={**headers, 'Idempotency-Key': str(uuid4())},
                              json={'schedule_id': response.json()['id'], 'amount': amount,
                                    'payment_date': deposit_date, 'method': 'cash'})
        assert payment.status_code == 201, payment.text
        assert payment.json()['receipt_id']
    schedules = client.get('/api/schedules', headers=headers, params={'account_id': account['id']}).json()['items']
    assert len(schedules) == 2
    assert all(row['status'] == 'paid' for row in schedules)


def test_ppf_financial_year_maturity_boundary():
    ppf = SimpleNamespace(code='PPF', duration_months=180)
    assert default_maturity(date(2026, 3, 31), ppf) == date(2041, 3, 31)
    assert default_maturity(date(2026, 4, 1), ppf) == date(2042, 3, 31)
    assert default_maturity(date(2024, 2, 29), SimpleNamespace(code='SSA', duration_months=252)) == date(2045, 2, 28)


def test_flexible_creation_rejects_fixed_maturity_amount(client, db, actors):
    from app.models import Scheme
    headers = actors['test_staff_a']['headers']
    customer = create_customer(client, headers)
    scheme = db.scalar(select(Scheme).where(Scheme.code == 'SSA'))
    response = client.post('/api/accounts', headers=headers, json={
        'customer_id': customer['id'], 'scheme_id': scheme.id,
        'account_number': uuid4().hex, 'amount': '250', 'maturity_amount': '10000',
        'start_date': today().isoformat(), 'post_office': 'Test PO'})
    assert response.status_code == 422
