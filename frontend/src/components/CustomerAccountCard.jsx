import { CalendarDays, CreditCard, Pencil, Trash2, UserRound, Wallet } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Badge } from './UI';
import AccountLifespan from './AccountLifespan';
import { date, money } from '../utils/format';

export default function CustomerAccountCard({
  account,
  onEdit,
  onDelete,
  onNavigate,
  canDelete = false,
  onDeposit,
}) {
  return (
    <article className="profile-account-card">
      <header>
        <span className="profile-account-icon">
          <CreditCard size={21} />
        </span>
        <div>
          <h4>{account.scheme_name}</h4>
          <span>{account.account_number || account.policy_number || account.account_code}</span>
        </div>
        <Badge value={account.status} />
      </header>
      <dl className="profile-account-facts">
        <div>
          <dt>
            <Wallet size={13} />
            Total deposited
          </dt>
          <dd>{money(account.total_deposited)}</dd>
        </div>
        <div>
          <dt>
            <CalendarDays size={13} />
            Opening date
          </dt>
          <dd>{date(account.start_date)}</dd>
        </div>
        <div>
          <dt>
            <CalendarDays size={13} />
            Maturity date
          </dt>
          <dd>{date(account.maturity_date)}</dd>
        </div>
        {account.rule_snapshot?.schedule_kind !== 'discretionary' && (
          <div className="maturity-value">
            <dt>
              <Wallet size={13} />
              Maturity amount
            </dt>
            <dd>
              {account.maturity_amount == null ? 'Not recorded' : money(account.maturity_amount)}
            </dd>
          </div>
        )}
        <div>
          <dt>
            <UserRound size={13} />
            Nominee
          </dt>
          <dd>{account.nominee_name || 'Not recorded'}</dd>
        </div>
      </dl>
      <div className="profile-account-term">
        <AccountLifespan account={account} />
      </div>
      {account.annual_deposits?.length > 0 && (
        <details className="account-annual-deposits" open>
          <summary>Deposits by financial year (April–March)</summary>
          <p className="muted">
            Recorded deposits only. Missing historical payments need verification. Annual shortfalls
            require review; accounts are not automatically closed.
          </p>
          {account.annual_deposits
            .slice()
            .reverse()
            .map((year) => (
              <div key={year.financial_year} className="info-note">
                <strong>
                  {year.financial_year}: {money(year.deposited)}
                </strong>
                <br />
                Minimum {money(year.minimum)} · Maximum {money(year.maximum)}
                <br />
                {year.status === 'shortfall_review'
                  ? `Annual shortfall: ${money(year.remaining_to_minimum)} — review required`
                  : year.status === 'minimum_pending'
                    ? `${money(year.remaining_to_minimum)} still needed before financial year end`
                    : year.status === 'over_limit'
                      ? 'Annual maximum exceeded — review required'
                      : 'Annual minimum met'}
              </div>
            ))}
        </details>
      )}
      <footer>
        {account.rule_snapshot?.schedule_kind === 'discretionary' && onDeposit && (
          <button className="text-link" onClick={() => onDeposit(account)}>
            Record deposit
          </button>
        )}
        <Link className="text-link" to={`/dues?account_id=${account.id}`} onClick={onNavigate}>
          Payment schedule
        </Link>
        <Link className="text-link" to={`/payments?account_id=${account.id}`} onClick={onNavigate}>
          Payment history
        </Link>
        <button
          className="icon-button"
          aria-label={`Edit account ${account.account_number || account.policy_number || account.account_code}`}
          onClick={() => onEdit(account)}
        >
          <Pencil size={15} />
        </button>
        {canDelete && (
          <button
            className="icon-button danger"
            aria-label="Delete scheme account"
            onClick={() => onDelete(account)}
          >
            <Trash2 size={15} />
          </button>
        )}
      </footer>
    </article>
  );
}
