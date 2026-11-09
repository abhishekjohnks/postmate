from uuid import uuid4
from sqlalchemy import func, select
from app.core.config import today
from app.models import Account, Customer, PaymentSchedule, Scheme


def payload(db):
    rd=db.scalar(select(Scheme).where(Scheme.code=='RD'))
    td=db.scalar(select(Scheme).where(Scheme.code=='TD1'))
    return {'customer':{'full_name':'Combined Customer','dob':'1980-01-01','phone':'9876543210','address':'12 Test Road','post_office':'Test PO','location':'Test Town'},
            'accounts':[{'scheme_id':rd.id,'account_number':uuid4().hex,'cif_id':'CIF-1','start_date':today().isoformat(),'amount':'500','post_office':'Test PO'},
                        {'scheme_id':td.id,'account_number':uuid4().hex,'start_date':today().isoformat(),'amount':'10000','post_office':'Test PO'}]}


def test_atomic_registration_multiple_schemes_and_ownership(client,db,actors):
    headers=actors['test_staff_a']['headers']
    body=payload(db)
    body['accounts'][0]['nominee_name']='Test Nominee'
    response=client.post('/api/customers/register',headers=headers,json=body)
    assert response.status_code==201,response.text
    customer=response.json()
    accounts=db.scalars(select(Account).where(Account.customer_id==customer['id'])).all()
    assert len(accounts)==2
    rd_account=next(a for a in accounts if a.nominee_name=='Test Nominee')
    account_detail=client.get('/api/accounts/'+rd_account.id,headers=headers).json()
    assert account_detail['nominee_name']=='Test Nominee'
    assert account_detail['start_date']==body['accounts'][0]['start_date']
    patch={'status':'active','remarks':'Updated nomination','nominee_name':'Updated Nominee'}
    assert client.patch('/api/accounts/'+rd_account.id,headers=actors['test_staff_b']['headers'],json=patch).status_code==404
    assert client.patch('/api/accounts/'+rd_account.id,headers=headers,json=patch).json()['nominee_name']=='Updated Nominee'
    assert client.patch('/api/accounts/'+rd_account.id,headers=headers,json={**patch,'nominee_name':'x'*201}).status_code==422
    assert db.scalar(select(func.count()).select_from(PaymentSchedule).where(PaymentSchedule.account_id.in_([a.id for a in accounts])))==61
    listed=client.get('/api/customers?q=Combined',headers=headers).json()['items'][0]
    assert listed['account_count']==2 and listed['schemes']==['RD','TD1']
    assert client.put('/api/customers/'+customer['id']+'/registration',headers=actors['test_staff_b']['headers'],json=body).status_code==404
    body['accounts']=[]
    body['customer']['full_name']='Updated Combined Customer'
    assert client.put('/api/customers/'+customer['id']+'/registration',headers=headers,json=body).status_code==200


def test_registration_failure_rolls_back_customer_and_all_accounts(client,db,actors):
    headers=actors['test_staff_a']['headers']
    body=payload(db)
    body['accounts'][1]['account_number']=None
    before=db.scalar(select(func.count()).select_from(Customer))
    assert client.post('/api/customers/register',headers=headers,json=body).status_code==422
    assert db.scalar(select(func.count()).select_from(Customer))==before
    assert db.scalar(select(func.count()).select_from(Account).where(Account.account_number==body['accounts'][0]['account_number']))==0
