import { CalendarDays, Landmark, ShieldCheck, Wallet } from 'lucide-react';
import { Field } from './UI';
import { localToday } from '../utils/format';

export const newSchemeDraft = () => ({
  clientKey: crypto.randomUUID(),
  scheme_id: '',
  amount: '',
  start_date: localToday(),
  nominee_name: '',
  maturity_date: '',
  maturity_amount: '',
  frequency_months: '',
  payment_mode: 'scheme_default',
  post_office: '',
  remarks: '',
  custom_fields: {},
  historical_record: false,
});

export function accountPayload(draft, postOffice) {
  const { clientKey, ...value } = draft;
  value.post_office = value.post_office || postOffice;
  if (value.payment_mode === 'flexible' || value.frequency_months === 'flexible')
    value.maturity_amount = null;
  if (value.maturity_amount === '') value.maturity_amount = null;
  if (!value.maturity_date) delete value.maturity_date;
  if (value.frequency_months === 'flexible') {
    value.payment_mode = 'flexible';
    delete value.frequency_months;
  } else if (value.frequency_months === '' || value.frequency_months == null)
    delete value.frequency_months;
  else value.frequency_months = Number(value.frequency_months);
  return value;
}

export default function SchemeFields({ value, onChange, schemes, postOffice }) {
  const scheme = schemes?.find((s) => s.id === value.scheme_id);
  const change = (key, next) => onChange({ ...value, [key]: next });
  const flexible =
    scheme?.schedule_kind === 'discretionary' || value.frequency_months === 'flexible';
  const recurring =
    !flexible &&
    scheme?.schedule_kind === 'collection' &&
    Number(value.frequency_months === '' ? scheme.frequency_months : value.frequency_months) > 0;
  return (
    <>
      <Field label="Savings scheme">
        <select
          required
          value={value.scheme_id}
          onChange={(e) =>
            onChange({
              ...newSchemeDraft(),
              clientKey: value.clientKey,
              scheme_id: e.target.value,
              start_date: value.start_date,
              amount: value.amount,
              nominee_name: value.nominee_name,
              maturity_amount:
                schemes.find((s) => s.id === e.target.value)?.schedule_kind === 'discretionary'
                  ? ''
                  : value.maturity_amount,
            })
          }
        >
          <option value="">Choose a savings or insurance scheme</option>
          {schemes
            ?.filter((s) => s.active)
            .map((s) => (
              <option key={s.id} value={s.id}>
                {s.code} — {s.name}
              </option>
            ))}
        </select>
      </Field>
      {scheme && (
        <div className="selected-scheme">
          <span className="scheme-emblem">
            {['PLI', 'RPLI'].includes(scheme.code) ? <ShieldCheck /> : <Landmark />}
          </span>
          <div>
            <strong>{scheme.name}</strong>
            <small>
              {scheme.schedule_kind === 'discretionary'
                ? 'Flexible deposits'
                : scheme.frequency_months === 0
                  ? 'Single opening deposit'
                  : `Every ${scheme.frequency_months} month(s)`}
              {scheme.duration_months
                ? ` · ${scheme.duration_months % 12 === 0 ? `${scheme.duration_months / 12} year` : `${scheme.duration_months} month`} term`
                : ' · Account-specific term'}
            </small>
          </div>
          <span className="scheme-code">{scheme.code}</span>
        </div>
      )}
      <div className="form-grid">
        <Field
          label={flexible ? 'Reference deposit amount (INR)' : 'Deposit / premium amount (INR)'}
          type="number"
          required
          min="0.01"
          step="0.01"
          value={value.amount}
          onChange={(e) => change('amount', e.target.value)}
        />
        <Field
          label="Account opening / commencement"
          type="date"
          required
          value={value.start_date}
          onChange={(e) => change('start_date', e.target.value)}
        />
        <Field
          label="Maturity date (or scheme default)"
          type="date"
          required={recurring && !scheme?.duration_months}
          value={value.maturity_date}
          onChange={(e) => change('maturity_date', e.target.value)}
        />
        {!flexible && (
          <Field
            label="Maturity amount (INR, optional)"
            type="number"
            min="0"
            step="0.01"
            value={value.maturity_amount ?? ''}
            placeholder="Enter the expected maturity amount"
            onChange={(e) => change('maturity_amount', e.target.value)}
          />
        )}
        <Field label="Payment frequency">
          <select
            value={scheme?.schedule_kind === 'discretionary' ? 'flexible' : value.frequency_months}
            disabled={scheme?.schedule_kind === 'discretionary'}
            onChange={(e) => change('frequency_months', e.target.value)}
          >
            <option value="">Use scheme default</option>
            <option value="flexible">Flexible deposits — no fixed schedule</option>
            {[
              [0, 'Single deposit'],
              [1, 'Monthly'],
              [3, 'Quarterly'],
              [6, 'Half-yearly'],
              [12, 'Yearly'],
            ].map(([v, label]) => (
              <option key={v} value={v}>
                {label}
              </option>
            ))}
          </select>
        </Field>
        <Field
          label={
            scheme?.fields.some((f) => f.key === 'nominee_name' && f.required)
              ? 'Nominee name *'
              : 'Nominee name (optional)'
          }
          required={scheme?.fields.some((f) => f.key === 'nominee_name' && f.required)}
          maxLength={200}
          value={value.nominee_name || ''}
          placeholder="Enter the nominee’s full name"
          onChange={(e) => change('nominee_name', e.target.value)}
        />
        {scheme?.fields
          .filter((f) => !['nominee_name', 'maturity_amount'].includes(f.key))
          .map((f) => {
            const common = ['account_number', 'policy_number', 'cif_id', 'agent_id'].includes(
              f.key,
            );
            return (
              <Field
                key={f.key}
                label={f.label + (f.required ? ' *' : ' (optional)')}
                type={f.field_type}
                required={f.required}
                value={(common ? value[f.key] : value.custom_fields[f.key]) || ''}
                onChange={(e) =>
                  common
                    ? change(f.key, e.target.value)
                    : change('custom_fields', { ...value.custom_fields, [f.key]: e.target.value })
                }
              />
            );
          })}
        <Field
          label="Scheme post office"
          required
          value={value.post_office || postOffice || ''}
          onChange={(e) => change('post_office', e.target.value)}
        />
        <Field
          label="Account remarks (optional)"
          maxLength={2000}
          value={value.remarks}
          onChange={(e) => change('remarks', e.target.value)}
        />
      </div>
      {scheme?.code === 'SSA' && (
        <p className="info-note">
          SSA: 21-year term from opening. Minimum INR 250 and maximum INR 1,50,000 per financial
          year (April–March), not per month. Deposits are permitted during the first 15 years. The
          final maturity amount is unknown and is not requested.
        </p>
      )}
      {scheme?.code === 'PPF' && (
        <p className="info-note">
          PPF: 15 complete financial years after the end of the opening financial year. Minimum INR
          500 and maximum INR 1,50,000 per financial year (April–March). The final maturity amount
          is unknown and is not requested.
        </p>
      )}
      {flexible && (
        <p className="scheme-tip">
          <CalendarDays size={15} />
          No monthly dues are generated. The reference amount is not a payment or a fixed
          instalment. After saving, use Record deposit on the customer’s account to enter each
          deposit’s actual amount and paid date and generate a receipt. You can enter INR 100 now
          and INR 500 later; months without deposits have no dues.
        </p>
      )}
      {scheme?.historical_only && (
        <label className="check-field">
          <input
            required
            type="checkbox"
            checked={value.historical_record}
            onChange={(e) => change('historical_record', e.target.checked)}
          />
          This is an existing historical account.
        </label>
      )}
    </>
  );
}
