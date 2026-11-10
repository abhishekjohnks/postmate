import DateInput from '../components/DateInput';
import { useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Download, Plus, Search, RotateCcw, Trash2 } from 'lucide-react';
import { useAuth } from '../context/Auth';
import { useData } from '../hooks/useData';
import { api, download, params } from '../services/api';
import {
  Badge,
  Confirm,
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  Pager,
  SaveButton,
  Table,
} from '../components/UI';
import { date, localToday, money, receiptFilename } from '../utils/format';

export function PaymentForm({ schedule, account, onClose, onSaved }) {
  const [q, setQ] = useState('');
  const { data: schedules, loading } = useData(
    '/schedules?' + params({ status: 'outstanding', q, page_size: 100 }),
  );
  const [values, setValues] = useState({
    schedule_id: schedule?.id || '',
    amount: schedule?.outstanding || '',
    payment_date: localToday(),
    method: 'cash',
    reference: '',
    remarks: '',
  });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(null);
  const idempotency = useRef({ signature: '', key: '' });
  const selected = schedule || schedules?.items.find((s) => s.id === values.schedule_id);
  const update = (key, value) => setValues((v) => ({ ...v, [key]: value }));
  return (
    <Modal title={saved ? 'Payment recorded' : 'Record a payment'} onClose={onClose} wide>
      {saved ? (
        <div className="payment-success">
          <span className="success-mark">✓</span>
          <h2>A payment, safely recorded.</h2>
          <p>
            {saved.customer_name} · {money(saved.amount)}
          </p>
          <button
            className="btn primary"
            onClick={async () => {
              try {
                await download(
                  `/receipts/${saved.receipt_id}/pdf`,
                  receiptFilename(saved.customer_name),
                );
              } catch (e) {
                setError(e.message);
              }
            }}
          >
            <Download size={17} />
            Download PDF receipt
          </button>
          <ErrorBox error={error} />
          <p className="muted">
            Internal PostMate payment record. Not an official India Post receipt unless authorized.
          </p>
        </div>
      ) : (
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setError('');
            setBusy(true);
            const body = { ...values, reference: values.reference || null };
            if (account) {
              delete body.schedule_id;
              body.account_id = account.id;
            }
            const signature = JSON.stringify(body);
            if (signature !== idempotency.current.signature)
              idempotency.current = { signature, key: crypto.randomUUID() };
            try {
              const payment = await api(account ? '/payments/flexible' : '/payments', {
                method: 'POST',
                body,
                headers: { 'Idempotency-Key': idempotency.current.key },
              });
              setSaved(payment);
              onSaved();
            } catch (e) {
              setError(e.message);
            } finally {
              setBusy(false);
            }
          }}
        >
          {account && (
            <div className="info-note">
              <strong>{account.customer_name}</strong> · {account.scheme_name}
              <br />
              Enter the amount received and the date paid. This creates the deposit and receipt
              together.
            </div>
          )}
          {!schedule && !account && (
            <>
              <Field
                label="Find customer, account or policy"
                placeholder="Search outstanding instalments…"
                value={q}
                onChange={(e) => setQ(e.target.value)}
              />
              <Field label="Select account & instalment">
                <select
                  required
                  value={values.schedule_id}
                  onChange={(e) => {
                    const s = schedules.items.find((s) => s.id === e.target.value);
                    setValues((v) => ({ ...v, schedule_id: s.id, amount: s.outstanding }));
                  }}
                >
                  <option value="">
                    {loading ? 'Loading outstanding payments…' : 'Select an instalment'}
                  </option>
                  {schedules?.items.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.customer_name} · {s.identifier} · #{s.sequence} · {date(s.due_date)} ·{' '}
                      {money(s.outstanding)}
                    </option>
                  ))}
                </select>
              </Field>
            </>
          )}
          {selected && (
            <div className="info-note">
              <strong>{selected.customer_name}</strong> · {selected.scheme_name}
              <br />
              {selected.identifier} · Instalment {selected.sequence} · Due {date(selected.due_date)}
              <br />
              Outstanding: <strong>{money(selected.outstanding)}</strong>
            </div>
          )}
          <div className="form-grid">
            <Field
              label="Amount received (INR)"
              type="number"
              required
              min="0.01"
              max={selected?.outstanding}
              step="0.01"
              value={values.amount}
              onChange={(e) => update('amount', e.target.value)}
            />
            <Field
              label="Actual payment date"
              type="date"
              required
              min={account?.start_date}
              max={localToday()}
              value={values.payment_date}
              onChange={(e) => update('payment_date', e.target.value)}
            />
            <Field label="Payment method">
              <select value={values.method} onChange={(e) => update('method', e.target.value)}>
                {['cash', 'upi', 'bank_transfer', 'cheque'].map((m) => (
                  <option key={m} value={m}>
                    {m.replace('_', ' ')}
                  </option>
                ))}
              </select>
            </Field>
            <Field
              label="Transaction reference (optional)"
              maxLength={150}
              value={values.reference}
              onChange={(e) => update('reference', e.target.value)}
            />
            <Field
              label="Remarks (optional)"
              maxLength={2000}
              value={values.remarks}
              onChange={(e) => update('remarks', e.target.value)}
            />
          </div>
          <ErrorBox error={error} />
          <div className="form-actions">
            <button className="btn" type="button" onClick={onClose}>
              Cancel
            </button>
            <SaveButton busy={busy} text="Save payment & create receipt" />
          </div>
        </form>
      )}
    </Modal>
  );
}

export default function Payments({ dues = false }) {
  const { user } = useAuth();
  const [url, setUrl] = useSearchParams();
  const [filters, setFilters] = useState({
    q: '',
    status: dues ? 'outstanding' : '',
    date_from: '',
    date_to: '',
    scheme_id: '',
    staff_id: '',
    post_office: '',
    include_deleted: false,
  });
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const [record, setRecord] = useState(null);
  const [reverse, setReverse] = useState(null);
  const [remove, setRemove] = useState(null);
  const [cancel, setCancel] = useState(null);
  const [actionError, setActionError] = useState('');
  const { data: schemes } = useData('/schemes');
  const { data: staff } = useData(
    user.role === 'super_admin' ? '/users?page_size=100' : '/auth/me',
  );
  const { data, loading, error } = useData(
    (dues ? '/schedules?' : '/payments?') +
      params({ ...filters, account_id: url.get('account_id'), page_number: page }),
    revision,
  );
  const change = (key, value) => {
    setFilters((f) => ({ ...f, [key]: value }));
    setPage(1);
  };
  const saved = () => setRevision((r) => r + 1);
  const columns = dues
    ? [
        {
          label: 'CUSTOMER / ACCOUNT',
          render: (s) => (
            <div>
              <strong>{s.customer_name}</strong>
              <small>{s.identifier}</small>
            </div>
          ),
        },
        { label: 'SCHEME', key: 'scheme_name' },
        { label: 'INSTALMENT', render: (s) => `#${s.sequence}` },
        { label: 'DUE DATE', render: (s) => date(s.due_date) },
        {
          label: 'EXPECTED / PAID',
          render: (s) => (
            <div>
              <strong>{money(s.expected_amount)}</strong>
              <small>{money(s.paid_amount)} received</small>
            </div>
          ),
        },
        { label: 'STATUS', render: (s) => <Badge value={s.status} /> },
        {
          label: 'ACTIONS',
          render: (s) => (
            <div className="row-actions">
              {!s.cancelled && Number(s.outstanding) > 0 && (
                <button className="btn small primary" onClick={() => setRecord(s)}>
                  Record payment
                </button>
              )}
              {user.role === 'super_admin' && !s.cancelled && Number(s.paid_amount) === 0 && (
                <button className="text-link danger" onClick={() => setCancel(s)}>
                  Cancel
                </button>
              )}
            </div>
          ),
        },
      ]
    : [
        {
          label: 'CUSTOMER',
          render: (p) => (
            <div>
              <strong>{p.customer_name}</strong>
              <small>{p.identifier}</small>
            </div>
          ),
        },
        { label: 'SCHEME', key: 'scheme_name' },
        { label: 'PAYMENT DATE', render: (p) => date(p.payment_date) },
        { label: 'AMOUNT', render: (p) => <strong>{money(p.amount)}</strong> },
        { label: 'COLLECTED BY', key: 'staff_name' },
        {
          label: 'STATUS',
          render: (p) => (
            <Badge value={p.deleted_at ? 'deleted' : p.reversed_at ? 'reversed' : 'paid'} />
          ),
        },
        {
          label: 'RECEIPT / ACTIONS',
          render: (p) => (
            <div className="row-actions">
              {user.role === 'super_admin' && !p.deleted_at && (
                <button
                  className="icon-button danger"
                  aria-label="Delete transaction"
                  onClick={() => setRemove(p)}
                >
                  <Trash2 size={16} />
                </button>
              )}
              <button
                className="text-link"
                onClick={async () => {
                  try {
                    await download(
                      `/receipts/${p.receipt_id}/pdf`,
                      receiptFilename(p.customer_name),
                    );
                  } catch (e) {
                    setActionError(e.message);
                  }
                }}
              >
                <Download size={15} />
                PDF
              </button>
              {user.role === 'super_admin' && !p.reversed_at && (
                <button
                  className="icon-button"
                  aria-label="Reverse payment"
                  onClick={() => setReverse(p)}
                >
                  <RotateCcw size={16} />
                </button>
              )}
            </div>
          ),
        },
      ];
  return (
    <>
      <PageHead
        eyebrow={dues ? 'A STEP AHEAD' : 'EVERY PAYMENT, ACCOUNTED FOR'}
        title={dues ? 'Payment dues' : 'Transactions'}
        subtitle={
          dues
            ? 'See what’s coming up, due today, and overdue.'
            : 'A traceable history of collections and payment receipts.'
        }
      >
        <button className="btn primary" onClick={() => setRecord({})}>
          <Plus size={17} />
          Record payment
        </button>
      </PageHead>
      {url.get('account_id') && (
        <div className="info-note">
          Showing one account.{' '}
          <button className="text-link" onClick={() => setUrl({})}>
            Show all accounts
          </button>
        </div>
      )}
      <section className="panel">
        <div className="toolbar">
          {!dues && (
            <label className="check-field">
              <input
                type="checkbox"
                checked={filters.include_deleted}
                onChange={(e) => change('include_deleted', e.target.checked)}
              />
              Show deleted transactions
            </label>
          )}
          <label className="search-input">
            <Search size={18} />
            <input
              aria-label="Search payments"
              placeholder="Customer, account, policy or CIF…"
              value={filters.q}
              onChange={(e) => change('q', e.target.value)}
            />
          </label>
          <select
            aria-label="Filter by scheme"
            value={filters.scheme_id}
            onChange={(e) => change('scheme_id', e.target.value)}
          >
            <option value="">All schemes</option>
            {schemes?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.code}
              </option>
            ))}
          </select>
          {dues && (
            <select
              aria-label="Payment status"
              value={filters.status}
              onChange={(e) => change('status', e.target.value)}
            >
              {[
                ['outstanding', 'Outstanding'],
                ['', 'All statuses'],
                ['due', 'Due today'],
                ['upcoming', 'Upcoming'],
                ['overdue', 'Overdue'],
                ['partially_paid', 'Partially paid'],
                ['paid', 'Paid'],
                ['cancelled', 'Cancelled'],
              ].map(([v, label]) => (
                <option key={v} value={v}>
                  {label}
                </option>
              ))}
            </select>
          )}
          {user.role === 'super_admin' && (
            <select
              aria-label="Filter by staff"
              value={filters.staff_id}
              onChange={(e) => change('staff_id', e.target.value)}
            >
              <option value="">All staff</option>
              {staff?.items?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name}
                </option>
              ))}
            </select>
          )}
          <input
            className="office-filter"
            aria-label="Filter by post office"
            placeholder="Post office"
            value={filters.post_office}
            onChange={(e) => change('post_office', e.target.value)}
          />
          <label className="inline-field">
            From
            <DateInput
              type="date"
              value={filters.date_from}
              onChange={(e) => change('date_from', e.target.value)}
            />
          </label>
          <label className="inline-field">
            To
            <DateInput
              type="date"
              value={filters.date_to}
              onChange={(e) => change('date_to', e.target.value)}
            />
          </label>
        </div>
        <ErrorBox error={error || actionError} />
        {loading ? <Loading /> : <Table rows={data?.items} columns={columns} />}
        <Pager data={data} page={page} setPage={setPage} />
      </section>
      {(record || url.has('record')) && (
        <PaymentForm
          schedule={record?.id ? record : null}
          onClose={() => {
            setRecord(null);
            url.delete('record');
            setUrl(url);
          }}
          onSaved={saved}
        />
      )}{' '}
      {reverse && (
        <Confirm
          title="Reverse this payment?"
          description={`${money(reverse.amount)} for ${reverse.customer_name}. The original payment and receipt remain traceable. The instalment balance will be restored.`}
          action={async (reason) => {
            await api(`/payments/${reverse.id}/reverse`, { method: 'POST', body: { reason } });
            saved();
          }}
          onClose={() => setReverse(null)}
        />
      )}{' '}
      {cancel && (
        <Confirm
          title="Cancel scheduled instalment?"
          description="This instalment will no longer accept payments."
          action={async (reason) => {
            await api(`/schedules/${cancel.id}/cancel`, { method: 'POST', body: { reason } });
            saved();
          }}
          onClose={() => setCancel(null)}
        />
      )}
      {user.role === 'super_admin' && remove && (
        <Confirm
          title="Delete transaction?"
          description={
            remove.reversed_at
              ? 'This transaction was already reversed. It will be hidden from the active list; the due balance will stay unchanged.'
              : `${money(remove.amount)} for ${remove.customer_name} will become outstanding again. The original payment and receipt will remain available in deleted history.`
          }
          requireReason={false}
          confirmText="Delete transaction"
          action={async () => {
            await api(`/payments/${remove.id}`, { method: 'DELETE' });
            saved();
          }}
          onClose={() => setRemove(null)}
        />
      )}
    </>
  );
}
