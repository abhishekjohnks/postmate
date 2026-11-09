import { CalendarClock, CalendarRange } from 'lucide-react';
import { date } from '../utils/format';

export function calendarDuration(value) {
  if (!value) return 'Not recorded';
  return `${value.years} year${value.years === 1 ? '' : 's'}, ${value.months} month${value.months === 1 ? '' : 's'}, ${value.days} day${value.days === 1 ? '' : 's'}`;
}

export default function AccountLifespan({ account }) {
  if (!account.account_term) return <span className="muted">Maturity date not recorded</span>;
  const ended = account.maturity_status === 'matured';
  const dueToday = account.maturity_status === 'matures_today';
  return (
    <div className="account-lifespan">
      <span>
        <CalendarRange size={14} />
        <span>
          <strong>{calendarDuration(account.account_term)}</strong>
          <small>Full term · opening to maturity</small>
        </span>
      </span>
      <span className={ended ? 'lifespan-ended' : 'lifespan-remaining'}>
        <CalendarClock size={14} />
        <span>
          {ended
            ? 'Matured'
            : dueToday
              ? 'Matures today'
              : `${calendarDuration(account.maturity_remaining)} remaining`}
          <small>
            {ended || dueToday
              ? calendarDuration(account.maturity_remaining)
              : account.maturity_status === 'not_opened'
                ? 'Account has not opened yet'
                : `As of ${date(account.maturity_as_of)}`}
          </small>
        </span>
      </span>
    </div>
  );
}
