import DateInput from '../components/DateInput';
import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Search, Pencil, CalendarPlus, Trash2 } from 'lucide-react';
import { useData } from '../hooks/useData';
import { useAuth } from '../context/Auth';
import { api, params } from '../services/api';
import {
  Badge,
  Confirm,
  ErrorBox,
  Field,
  Loading,
  Modal,
  Pager,
  SaveButton,
  Table,
} from '../components/UI';
import { date, money } from '../utils/format';
import AccountLifespan from '../components/AccountLifespan';
import { PaymentForm } from './Payments';

export function EditAccount({ account, onClose, onSaved }) {
  const flexible = account.rule_snapshot?.schedule_kind === 'discretionary';
  const [status, setStatus] = useState(account.status);
  const [remarks, setRemarks] = useState(account.remarks);
  const [nomineeName, setNomineeName] = useState(account.nominee_name || '');
  const [maturityAmount, setMaturityAmount] = useState(account.maturity_amount ?? '');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <Modal title="Update account details" onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await api(`/accounts/${account.id}`, {
              method: 'PATCH',
              body: {
                status,
                remarks,
                nominee_name: nomineeName || null,
                ...(!flexible && {
                  maturity_amount: maturityAmount === '' ? null : maturityAmount,
                }),
              },
            });
            onSaved();
            onClose();
          } catch (e) {
            setError(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <p>
          Changes are recorded in the audit trail. Closed and inactive accounts cannot receive
          payments.
        </p>
        <Field
          label="Nominee name (optional)"
          maxLength={200}
          value={nomineeName}
          onChange={(e) => setNomineeName(e.target.value)}
        />
        {!flexible && (
          <Field
            label="Maturity amount (INR, optional)"
            type="number"
            min="0"
            step="0.01"
            value={maturityAmount}
            onChange={(e) => setMaturityAmount(e.target.value)}
          />
        )}
        {flexible && (
          <p className="info-note">The maturity amount is unknown for flexible deposits.</p>
        )}
        <Field label="Status">
          <select value={status} onChange={(e) => setStatus(e.target.value)}>
            {['active', 'closed', 'matured', 'inactive'].map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </Field>
        <Field
          label="Remarks (optional)"
          value={remarks}
          onChange={(e) => setRemarks(e.target.value)}
        />
        <ErrorBox error={error} />
        <div className="form-actions">
          <SaveButton busy={busy} />
        </div>
      </form>
    </Modal>
  );
}

export function DepositSchedule({ account, onClose, onSaved }) {
  const [values, setValues] = useState({
    account_id: account.id,
    due_date: '',
    expected_amount: '',
    remarks: '',
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <Modal title="Add a flexible deposit schedule" onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await api('/schedules', { method: 'POST', body: values });
            onSaved();
            onClose();
          } catch (e) {
            setError(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <p>
          Enter only the amount and date agreed for this deposit. Each deposit can have a different
          amount; skipped months do not create dues. After saving, record its payment from Payment
          dues.
        </p>
        {[
          ['due_date', 'Due date', 'date'],
          ['expected_amount', 'Expected deposit (INR)', 'number'],
          ['remarks', 'Remarks', 'text'],
        ].map(([key, label, type]) => (
          <Field
            key={key}
            label={label}
            type={type}
            required
            step={type === 'number' ? '0.01' : undefined}
            min={type === 'number' ? '0.01' : undefined}
            value={values[key]}
            onChange={(e) => setValues({ ...values, [key]: e.target.value })}
          />
        ))}
        <ErrorBox error={error} />
        <div className="form-actions">
          <SaveButton busy={busy} />
        </div>
      </form>
    </Modal>
  );
}

export default function Accounts() {
  const { user } = useAuth();
  const canDelete = user.role === 'super_admin';
  const [remove, setRemove] = useState(null);
  const [edit, setEdit] = useState(null);
  const [deposit, setDeposit] = useState(null);
  const [filters, setFilters] = useState({ q: '', scheme_id: '', maturity_to: '' });
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const { data: schemes } = useData('/schemes');
  const { data, loading, error } = useData(
    '/accounts?' + params({ ...filters, page_number: page }),
    revision,
  );
  const saved = () => setRevision((r) => r + 1);
  return (
    <>
      <section className="panel">
        <div className="toolbar">
          <label className="search-input">
            <Search size={18} />
            <input
              aria-label="Search accounts"
              placeholder="Name, account, policy or CIF…"
              value={filters.q}
              onChange={(e) => {
                setFilters({ ...filters, q: e.target.value });
                setPage(1);
              }}
            />
          </label>
          <select
            aria-label="Scheme filter"
            value={filters.scheme_id}
            onChange={(e) => {
              setFilters({ ...filters, scheme_id: e.target.value });
              setPage(1);
            }}
          >
            <option value="">All schemes</option>
            {schemes?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.code}
              </option>
            ))}
          </select>
          <label className="inline-field">
            Maturing by
            <DateInput
              aria-label="Maturity date filter"
              type="date"
              value={filters.maturity_to}
              onChange={(e) => {
                setFilters({ ...filters, maturity_to: e.target.value });
                setPage(1);
              }}
            />
          </label>
        </div>
        <ErrorBox error={error} />
        {loading ? (
          <Loading />
        ) : (
          <Table
            rows={data?.items}
            columns={[
              { label: 'CUSTOMER', key: 'customer_name' },
              { label: 'SCHEME', key: 'scheme_name' },
              {
                label: 'ACCOUNT / POLICY',
                render: (a) => (
                  <div>
                    <strong>{a.account_number || a.policy_number || a.account_code}</strong>
                    <small>{a.cif_id ? `CIF ${a.cif_id}` : ''}</small>
                  </div>
                ),
              },
              { label: 'AMOUNT', render: (a) => money(a.amount) },
              { label: 'TOTAL DEPOSITED', render: (a) => money(a.total_deposited) },
              { label: 'OPENING DATE', render: (a) => date(a.start_date) },
              { label: 'NOMINEE', key: 'nominee_name' },
              { label: 'MATURITY', render: (a) => date(a.maturity_date) },
              {
                label: 'MATURITY AMOUNT',
                render: (a) =>
                  a.rule_snapshot?.schedule_kind === 'discretionary'
                    ? 'Unknown — flexible deposits'
                    : a.maturity_amount == null
                      ? 'Not recorded'
                      : money(a.maturity_amount),
              },
              { label: 'ACCOUNT LIFESPAN', render: (a) => <AccountLifespan account={a} /> },
              { label: 'STATUS', render: (a) => <Badge value={a.status} /> },
              {
                label: 'ACTIONS',
                render: (a) => (
                  <div className="row-actions">
                    {canDelete && (
                      <button
                        className="icon-button danger"
                        aria-label="Delete scheme account"
                        onClick={() => setRemove(a)}
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                    <Link className="text-link" to={`/dues?account_id=${a.id}`}>
                      Schedule
                    </Link>
                    <Link className="text-link" to={`/payments?account_id=${a.id}`}>
                      History
                    </Link>
                    {a.rule_snapshot.schedule_kind === 'discretionary' && (
                      <button
                        className="icon-button"
                        aria-label="Record deposit"
                        onClick={() => setDeposit(a)}
                      >
                        <CalendarPlus size={17} />
                      </button>
                    )}
                    <button
                      className="icon-button"
                      aria-label="Edit account"
                      onClick={() => setEdit(a)}
                    >
                      <Pencil size={16} />
                    </button>
                  </div>
                ),
              },
            ]}
          />
        )}
        <Pager data={data} page={page} setPage={setPage} />
      </section>
      {edit && <EditAccount account={edit} onClose={() => setEdit(null)} onSaved={saved} />}{' '}
      {deposit && (
        <PaymentForm account={deposit} onClose={() => setDeposit(null)} onSaved={saved} />
      )}
      {canDelete && remove && (
        <Confirm
          title="Delete scheme account?"
          description="This account and its payment dues will be removed from your workspace. Existing payments and receipts remain in financial history."
          requireReason={false}
          confirmText="Delete account"
          action={async () => {
            await api(`/accounts/${remove.id}`, { method: 'DELETE' });
            saved();
          }}
          onClose={() => setRemove(null)}
        />
      )}
    </>
  );
}
