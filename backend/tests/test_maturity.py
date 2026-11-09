from datetime import date
from decimal import Decimal
import pytest
from app.services.accounts import account_timeline
from app.models import Account
from sqlalchemy.exc import IntegrityError
from test_registration import payload


@pytest.mark.parametrize('start,end,as_of,term,remaining,status',[
    ('2020-01-15','2026-03-20','2025-02-10',(6,2,5),(1,1,10),'active'),
    ('2024-02-29','2025-02-28','2024-02-29',(1,0,0),(1,0,0),'active'),
    ('2026-01-31','2026-02-28','2026-02-28',(0,1,0),(0,0,0),'matures_today'),
    ('2020-01-01','2021-01-01','2026-10-28',(1,0,0),(0,0,0),'matured'),
    ('2027-02-01','2032-02-01','2026-10-28',(5,0,0),(5,3,4),'not_opened'),
])
def test_calendar_term_and_remaining(start,end,as_of,term,remaining,status):
    timeline=account_timeline(date.fromisoformat(start),date.fromisoformat(end),date.fromisoformat(as_of))
    assert tuple(timeline['account_term'][key] for key in ['years','months','days'])==term
    assert tuple(timeline['maturity_remaining'][key] for key in ['years','months','days'])==remaining
    assert timeline['maturity_remaining']['total_days']>=0
    assert timeline['maturity_status']==status


def test_unknown_maturity_has_no_invented_duration():
    timeline=account_timeline(date(2026,1,1),None,date(2026,10,28))
    assert timeline['account_term'] is None and timeline['maturity_remaining'] is None


def test_maturity_amount_persistence_validation_and_updates(client,db,actors):
    headers=actors['test_staff_a']['headers']
    body=payload(db)
    body['accounts'][0]['maturity_amount']='36000.50'
    response=client.post('/api/customers/register',headers=headers,json=body)
    assert response.status_code==201,response.text
    accounts=client.get('/api/accounts?customer_id='+response.json()['id'],headers=headers).json()['items']
    account=next(a for a in accounts if a['maturity_amount'] is not None)
    assert Decimal(account['maturity_amount'])==Decimal('36000.50')
    assert account['account_term']['years']==5
    assert account['maturity_remaining']['years']==5
    assert next(a for a in accounts if a['id']!=account['id'])['maturity_amount'] is None
    patch={'status':'active','remarks':''}
    # Editing other fields does not erase a previously recorded maturity amount.
    assert Decimal(client.patch('/api/accounts/'+account['id'],headers=headers,json=patch).json()['maturity_amount'])==Decimal('36000.50')
    patch['maturity_amount']='42000.75'
    assert client.patch('/api/accounts/'+account['id'],headers=actors['test_staff_b']['headers'],json=patch).status_code==404
    assert Decimal(client.patch('/api/accounts/'+account['id'],headers=headers,json=patch).json()['maturity_amount'])==Decimal('42000.75')
    for bad in ['-1','1.005','1000000000000.00']:
        assert client.patch('/api/accounts/'+account['id'],headers=headers,json={**patch,'maturity_amount':bad}).status_code==422
    assert client.patch('/api/accounts/'+account['id'],headers=headers,json={**patch,'maturity_amount':None}).json()['maturity_amount'] is None
    with pytest.raises(IntegrityError):
        with db.begin_nested():
            db.get(Account,account['id']).maturity_amount=Decimal('-1')
            db.flush()
