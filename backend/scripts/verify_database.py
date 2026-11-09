"""Read-only verification; prints counts, never identities or credentials."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import func, inspect, select, text
from app.db.session import SessionLocal, engine
from app.models import Account, Customer, PaymentReceipt, PaymentTransaction, Scheme, User

with SessionLocal() as db:
    print('Public tables:', len(inspect(engine).get_table_names()))
    print('Migration:', db.execute(text('SELECT version_num FROM alembic_version')).scalar_one())
    for label, model in [('Users', User), ('Schemes', Scheme), ('Customers', Customer),
                         ('Accounts', Account), ('Payments', PaymentTransaction), ('Receipts', PaymentReceipt)]:
        print(label + ':', db.scalar(select(func.count()).select_from(model)))
    mismatches = db.execute(text('''
        SELECT p.id FROM payment_schedules p LEFT JOIN payment_transactions t ON t.schedule_id=p.id
        GROUP BY p.id HAVING p.paid_amount <> COALESCE(SUM(t.amount) FILTER (WHERE t.reversed_at IS NULL), 0)
    ''')).all()
    missing_receipts = db.execute(text('''
        SELECT t.id FROM payment_transactions t LEFT JOIN payment_receipts r ON r.transaction_id=t.id WHERE r.id IS NULL
    ''')).all()
    print('Ledger balance mismatches:', len(mismatches))
    print('Payments missing receipts:', len(missing_receipts))
    if mismatches or missing_receipts:
        raise SystemExit(1)
