"""Enforce nonnegative maturity amounts independently of API validation."""
from alembic import op

revision = '5210b7f6a8c9'
down_revision = 'f537c0de7ec1'
branch_labels = None
depends_on = None


def upgrade():
    op.create_check_constraint('ck_account_maturity_amount', 'customer_scheme_accounts',
                               'maturity_amount IS NULL OR maturity_amount >= 0')


def downgrade():
    op.drop_constraint('ck_account_maturity_amount', 'customer_scheme_accounts', type_='check')
