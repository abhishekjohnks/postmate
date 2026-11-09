from decimal import Decimal
from uuid import uuid4
import pytest
from sqlalchemy import select
from app.models import Account, AuditLog, Customer, PaymentSchedule, PaymentTransaction, Scheme
from test_workflows import create_account, create_customer, payment_payload


@pytest.mark.parametrize('partial',[False,True])
def test_delete_transaction_restores_due_exactly_once(client,db,actors,partial):
    owner=actors['test_staff_a']['headers']
    other=actors['test_staff_b']['headers']
    admin=actors['test_admin']['headers']
    if partial:
        scheme=db.scalar(select(Scheme).where(Scheme.code=='RD'))
        scheme.allow_partial=True
        db.commit()
    customer=create_customer(client,owner)
    account=create_account(client,db,owner,customer)
    schedule=client.get('/api/schedules?account_id='+account['id'],headers=owner).json()['items'][0]
    amount='200.00' if partial else '500.00'
    payment=client.post('/api/payments',headers={**owner,'Idempotency-Key':str(uuid4())},json=payment_payload(schedule,amount)).json()
    if partial:
        assert client.post('/api/payments',headers={**owner,'Idempotency-Key':str(uuid4())},json=payment_payload(schedule,'300.00')).status_code==201
    assert client.delete('/api/payments/'+payment['id'],headers=other).status_code==403
    assert client.delete('/api/payments/'+payment['id'],headers=owner).status_code==403
    assert client.delete('/api/payments/'+payment['id'],headers=admin).status_code==204
    assert client.delete('/api/payments/'+payment['id'],headers=admin).status_code==204
    db.expire_all()
    stored=db.get(PaymentTransaction,payment['id'])
    assert stored.deleted_at and stored.reversed_at
    assert db.get(PaymentSchedule,schedule['id']).paid_amount==Decimal('300' if partial else '0')
    active=client.get('/api/payments?account_id='+account['id'],headers=owner).json()['items']
    assert payment['id'] not in [p['id'] for p in active]
    history=client.get('/api/payments?include_deleted=true&account_id='+account['id'],headers=owner).json()['items']
    assert next(p for p in history if p['id']==payment['id'])['deleted_at']
    assert client.get('/api/receipts/'+payment['receipt_id']+'/pdf',headers=owner).content.startswith(b'%PDF-')
    due=client.get('/api/schedules?status=outstanding&account_id='+account['id'],headers=owner).json()['items'][0]
    assert due['id']==schedule['id'] and Decimal(due['outstanding'])==Decimal(amount)
    assert client.post('/api/payments',headers={**owner,'Idempotency-Key':str(uuid4())},json=payment_payload(schedule,amount)).status_code==201
    assert Decimal(client.get('/api/dashboard',headers=owner).json()['month_collections'])==Decimal('500')


@pytest.mark.parametrize('entity',['account','customer'])
def test_customer_account_deletion_keeps_financial_history(client,db,actors,entity):
    owner=actors['test_staff_a']['headers']
    other=actors['test_staff_b']['headers']
    admin=actors['test_admin']['headers']
    customer=create_customer(client,owner)
    account=create_account(client,db,owner,customer)
    schedule=client.get('/api/schedules?account_id='+account['id'],headers=owner).json()['items'][0]
    payment=client.post('/api/payments',headers={**owner,'Idempotency-Key':str(uuid4())},json=payment_payload(schedule)).json()
    path='/api/accounts/'+account['id'] if entity=='account' else '/api/customers/'+customer['id']
    assert client.delete(path,headers=other).status_code==403
    assert client.delete(path,headers=owner).status_code==403
    assert client.delete(path,headers=admin).status_code==204
    assert client.get(path,headers=owner).status_code==404
    assert client.get('/api/accounts?customer_id='+customer['id'],headers=owner).json()['total']==0
    assert client.get('/api/schedules?account_id='+account['id'],headers=owner).json()['total']==0
    assert client.post('/api/payments',headers={**owner,'Idempotency-Key':str(uuid4())},json=payment_payload(schedule)).status_code==404
    history=client.get('/api/payments?account_id='+account['id'],headers=owner).json()['items']
    assert history[0]['id']==payment['id']
    assert client.get('/api/receipts/'+payment['receipt_id']+'/pdf',headers=owner).status_code==200
    dashboard=client.get('/api/dashboard',headers=owner).json()
    assert dashboard['total_accounts']==0
    assert Decimal(dashboard['month_collections'])==Decimal('500')
    db.expire_all()
    assert db.get(Account,account['id']) is not None and db.get(Customer,customer['id']) is not None
    if entity=='customer':
        assert client.post('/api/customers/'+customer['id']+'/identity',headers=owner).status_code==404
        assert dashboard['total_customers']==0


def test_direct_identity_reveal_requires_ownership_and_is_audited(client,db,actors):
    owner=actors['test_staff_a']['headers']
    customer=create_customer(client,owner)
    path='/api/customers/'+customer['id']+'/identity'
    assert client.post(path,headers=actors['test_staff_b']['headers']).status_code==404
    assert client.post(path).status_code==401
    response=client.post(path,headers=owner)
    assert response.status_code==200 and response.json()['aadhaar']=='123456789012'
    log=db.scalar(select(AuditLog).where(AuditLog.entity_id==customer['id'],AuditLog.action=='customer.identity_viewed'))
    assert log is not None and log.details=={}
