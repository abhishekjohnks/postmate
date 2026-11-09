from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from uuid import uuid4
import pytest
from dateutil.relativedelta import relativedelta
from PIL import Image
from sqlalchemy import func, select
from app.core.config import today
from app.models import AuditLog, Customer, CustomerDocument, PaymentReceipt, PaymentSchedule, PaymentTransaction, Scheme, User
from app.services.accounts import schedule_dates
from app.services.ledger import payment_status


def create_customer(client, headers):
    response = client.post('/api/customers', headers=headers, json={
        'full_name': 'Test Customer', 'dob': '1980-01-01', 'phone': '9876543210',
        'address': '12 Test Road, Test Town', 'post_office': 'Test PO', 'location': 'Test Town',
        'aadhaar': '123456789012', 'pan': 'ABCDE1234F'})
    assert response.status_code == 201, response.text
    return response.json()


def create_account(client, db, headers, customer, scheme_code='RD', **extra):
    scheme = db.scalar(select(Scheme).where(Scheme.code == scheme_code))
    payload = {'customer_id': customer['id'], 'scheme_id': scheme.id, 'account_number': uuid4().hex,
               'cif_id': 'CIF123', 'start_date': today().replace(day=1).isoformat(), 'amount': '500.00',
               'post_office': 'Test PO', **extra}
    response = client.post('/api/accounts', headers=headers, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def payment_payload(schedule, amount='500.00'):
    return {'schedule_id': schedule['id'], 'amount': amount, 'payment_date': today().isoformat(), 'method': 'cash'}


def test_calendar_rules():
    assert schedule_dates(date(2024, 1, 31), date(2024, 5, 31), 1) == [date(2024, 1, 31), date(2024, 2, 29), date(2024, 3, 31), date(2024, 4, 30)]
    assert len(schedule_dates(date(2024, 1, 1), date(2026, 1, 1), 3)) == 8
    assert schedule_dates(date(2024, 1, 1), None, 0) == [date(2024, 1, 1)]
    assert schedule_dates(date(2024, 1, 1), None, None) == []


def test_staff_isolation_and_private_identity(client, db, actors):
    a, b, admin = [actors[n]['headers'] for n in ['test_staff_a', 'test_staff_b', 'test_admin']]
    customer = create_customer(client, a)
    assert customer['aadhaar'] == '********9012'
    assert customer['pan'] == '******234F'
    stored = db.get(Customer, customer['id'])
    assert '123456789012' not in stored.aadhaar_encrypted
    assert client.get('/api/customers/' + customer['id'], headers=b).status_code == 404
    assert client.post('/api/customers/' + customer['id'] + '/identity', headers=b, json={'reason': 'Verification'}).status_code == 404
    assert client.get('/api/customers', headers=b).json()['total'] == 0
    assert client.get('/api/customers', headers=admin).json()['total'] >= 1
    assert client.post('/api/users', headers=a, json={'username': 'new_user', 'full_name': 'Another User', 'password': 'ExamplePassword123!'}).status_code == 403
    account = create_account(client, db, a, customer)
    assert client.get('/api/accounts/' + account['id'], headers=b).status_code == 404
    assert client.get('/api/schedules?account_id=' + account['id'], headers=b).json()['total'] == 0
    identity = client.post(f"/api/customers/{customer['id']}/identity", headers=a)
    assert identity.json()['aadhaar'] == '123456789012'
    assert db.scalar(select(func.count()).select_from(AuditLog).where(AuditLog.action == 'customer.identity_viewed', AuditLog.entity_id == customer['id'])) == 1


def test_payment_receipt_idempotency_reversal(client, db, actors):
    a, b, admin = [actors[n]['headers'] for n in ['test_staff_a', 'test_staff_b', 'test_admin']]
    customer = create_customer(client, a)
    account = create_account(client, db, a, customer)
    schedules = client.get('/api/schedules?account_id=' + account['id'], headers=a).json()
    assert schedules['total'] == 60
    schedule = schedules['items'][0]
    payload = payment_payload(schedule)
    key = str(uuid4())
    headers = {**a, 'Idempotency-Key': key}
    assert client.post('/api/payments', headers={**b, 'Idempotency-Key': str(uuid4())}, json=payload).status_code == 404
    assert client.post('/api/payments', headers=headers, json={**payload, 'amount': '100'}).status_code == 422
    assert client.post('/api/payments', headers=headers, json={**payload, 'amount': '600'}).status_code == 422
    response = client.post('/api/payments', headers=headers, json=payload)
    assert response.status_code == 201, response.text
    transaction = response.json()
    repeated = client.post('/api/payments', headers=headers, json=payload)
    assert repeated.json()['id'] == transaction['id']
    assert client.post('/api/payments', headers=headers, json={**payload, 'remarks': 'changed request'}).status_code == 409
    assert client.post('/api/payments', headers={**a, 'Idempotency-Key': str(uuid4())}, json=payload).status_code == 422
    receipt_path = '/api/receipts/' + transaction['receipt_id'] + '/pdf'
    assert client.get(receipt_path, headers=b).status_code == 404
    assert client.get('/api/payments', headers=b).json()['total'] == 0
    assert transaction['id'] not in client.get('/api/reports/payments', headers=b).text
    for _ in range(2):
        pdf = client.get(receipt_path, headers=a)
        assert pdf.status_code == 200 and pdf.content.startswith(b'%PDF-')
        assert pdf.headers['content-disposition'] == f'attachment; filename="PostMate-receipt-{payload["payment_date"]}.pdf"'
    db.expire_all()
    receipt = db.get(PaymentReceipt, transaction['receipt_id'])
    assert receipt.download_count == 2
    assert db.scalar(select(func.count()).select_from(PaymentTransaction).where(PaymentTransaction.schedule_id == schedule['id'])) == 1
    assert client.post('/api/payments/' + transaction['id'] + '/reverse', headers=a, json={'reason': 'Entry correction'}).status_code == 403
    reversal = client.post('/api/payments/' + transaction['id'] + '/reverse', headers=admin, json={'reason': 'Entry correction'})
    assert reversal.status_code == 200, reversal.text
    assert client.post('/api/payments/' + transaction['id'] + '/reverse', headers=admin, json={'reason': 'Entry correction'}).status_code == 409
    db.expire_all()
    assert db.get(PaymentSchedule, schedule['id']).paid_amount == 0
    assert db.scalar(select(func.count()).select_from(PaymentTransaction).where(PaymentTransaction.schedule_id == schedule['id'])) == 1
    assert client.delete('/api/payments/' + transaction['id'], headers=admin).status_code == 204
    dashboard = client.get('/api/dashboard', headers=a)
    assert dashboard.status_code == 200, dashboard.text
    assert Decimal(dashboard.json()['month_collections']) == 0
    assert client.get('/api/dashboard', headers=b).json()['total_customers'] == 0


def test_dynamic_schemes_and_rules_snapshot(client, db, actors):
    a, admin = [actors[n]['headers'] for n in ['test_staff_a', 'test_admin']]
    customer = create_customer(client, a)
    scheme = db.scalar(select(Scheme).where(Scheme.code == 'RD'))
    scheme.allow_partial = True
    db.commit()
    account = create_account(client, db, a, customer)
    scheme.allow_partial = False
    db.commit()
    schedule = client.get('/api/schedules?account_id=' + account['id'], headers=a).json()['items'][0]
    for amount in ['100.00', '400.00']:
        response = client.post('/api/payments', headers={**a, 'Idempotency-Key': str(uuid4())}, json=payment_payload(schedule, amount))
        assert response.status_code == 201, response.text
    db.expire_all()
    assert db.get(PaymentSchedule, schedule['id']).paid_amount == Decimal('500')
    ssa = create_account(client, db, a, customer, 'SSA')
    assert client.get('/api/schedules?account_id=' + ssa['id'], headers=a).json()['total'] == 0
    manual = client.post('/api/schedules', headers=a, json={'account_id': ssa['id'], 'due_date': today().isoformat(), 'expected_amount': '1000', 'remarks': 'Agreed deposit'})
    assert manual.status_code == 201, manual.text
    td = create_account(client, db, a, customer, 'TD1')
    assert client.get('/api/schedules?account_id=' + td['id'], headers=a).json()['total'] == 1
    historical = db.scalar(select(Scheme).where(Scheme.code == 'MAHILA'))
    bad = client.post('/api/accounts', headers=a, json={'customer_id': customer['id'], 'scheme_id': historical.id, 'account_number': 'HIST-1', 'amount': '1000', 'start_date': '2024-01-01', 'post_office': 'Test PO'})
    assert bad.status_code == 422
    pli = db.scalar(select(Scheme).where(Scheme.code == 'PLI'))
    bad = client.post('/api/accounts', headers=a, json={'customer_id': customer['id'], 'scheme_id': pli.id, 'amount': '1000', 'start_date': today().isoformat(), 'post_office': 'Test PO'})
    assert bad.status_code == 422


def test_documents_encryption_isolation_and_validation(client, db, actors, tmp_path, monkeypatch):
    from app.core.config import get_settings
    monkeypatch.setattr(get_settings(), 'storage_dir', tmp_path)
    a, b = [actors[n]['headers'] for n in ['test_staff_a', 'test_staff_b']]
    customer = create_customer(client, a)
    path = f"/api/customers/{customer['id']}/documents?kind=aadhaar"
    image = BytesIO()
    Image.new('RGB', (5, 5), 'red').save(image, format='PNG')
    content = image.getvalue()
    assert client.post(path, headers=a, files={'file': ('attack.pdf', b'not pdf', 'application/pdf')}).status_code == 422
    assert client.post(path, headers=a, files={'file': ('large.pdf', b'x' * (5 * 1024 * 1024 + 1), 'application/pdf')}).status_code == 422
    assert client.post(path, headers=b, files={'file': ('photo.png', content, 'image/png')}).status_code == 404
    response = client.post(path, headers=a, files={'file': ('photo.png', content, 'image/png')})
    assert response.status_code == 201, response.text
    doc = response.json()
    assert 'storage_key' not in doc
    row = db.get(CustomerDocument, doc['id'])
    assert (tmp_path / row.storage_key).read_bytes() != content
    assert client.get('/api/documents/' + doc['id'], headers=b).status_code == 404
    assert client.get('/api/documents/' + doc['id'], headers=a).content == content
    assert client.request('DELETE', '/api/documents/' + doc['id'], headers=a, json={'reason': 'Replacing outdated document'}).status_code == 403
    assert client.request('DELETE', '/api/documents/' + doc['id'], headers=actors['test_admin']['headers'], json={'reason': 'Replacing outdated document'}).status_code == 204
    assert not (tmp_path / row.storage_key).exists()


def test_login_logout_and_revoked_access(client, db, actors):
    response = client.post('/api/auth/login', data={'username': 'test_staff_a', 'password': 'TestPassword123!'})
    assert response.status_code == 200
    headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
    assert client.get('/api/auth/me', headers=headers).status_code == 200
    assert client.post('/api/auth/logout', headers=headers).status_code == 200
    assert client.get('/api/auth/me', headers=headers).status_code == 401
    assert client.get('/api/customers').status_code == 401
    staff_b = actors['test_staff_b']['user']
    staff_b.active = False
    db.commit()
    assert client.get('/api/customers', headers=actors['test_staff_b']['headers']).status_code == 401


def test_status_boundaries():
    row = PaymentSchedule(expected_amount=Decimal('500'), paid_amount=Decimal('100'), due_date=today(), cancelled=False)
    assert payment_status(row) == 'partially_paid'
    row.due_date -= timedelta(days=1)
    assert payment_status(row) == 'overdue'
    row.paid_amount = Decimal('500')
    assert payment_status(row) == 'paid'
    row.cancelled = True
    assert payment_status(row) == 'cancelled'


def test_notifications_and_csv_security(client, db, actors):
    from app.api.reporting import csv_response
    a = actors['test_staff_a']['headers']
    customer = create_customer(client, a)
    create_account(client, db, a, customer)
    notices = client.get('/api/notifications', headers=a)
    assert notices.status_code == 200
    ids = [row['id'] for row in notices.json()['items']]
    assert len(ids) == len(set(ids))
    assert "'=HYPERLINK" in csv_response([{'customer': '=HYPERLINK("bad")'}], 'test').body.decode()
    assert client.get('/api/audit-logs', headers=a).status_code == 403


def test_scheduled_notifications_upsert_and_resolve(client, db, actors, monkeypatch):
    from contextlib import contextmanager
    from app.models import Notification
    from app.services import notifications
    a = actors['test_staff_a']['headers']
    customer = create_customer(client, a)
    account = create_account(client, db, a, customer)
    @contextmanager
    def transaction():
        yield db
        db.commit()
    class Factory:
        begin = staticmethod(transaction)
    monkeypatch.setattr(notifications, 'SessionLocal', Factory())
    notifications.refresh_notifications()
    notifications.refresh_notifications()
    count = db.scalar(select(func.count()).select_from(Notification))
    assert count > 0
    assert db.scalar(select(func.count(func.distinct(Notification.schedule_id)))) == count
    due = db.scalar(select(PaymentSchedule).where(PaymentSchedule.account_id == account['id']).order_by(PaymentSchedule.due_date))
    due.cancelled = True
    db.commit()
    notifications.refresh_notifications()
    db.expire_all()
    assert db.scalar(select(Notification).where(Notification.schedule_id == due.id)).resolved is True
