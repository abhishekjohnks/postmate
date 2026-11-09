import { useEffect, useRef, useState } from 'react';
import DateInput from './DateInput';
import { AlertCircle, Inbox, LoaderCircle, X, ChevronLeft, ChevronRight } from 'lucide-react';
export function ErrorBox({ error }) {
  return error ? (
    <div className="error" role="alert">
      <AlertCircle size={18} />
      {error}
    </div>
  ) : null;
}
export function Loading() {
  return (
    <div className="empty">
      <LoaderCircle className="spin" /> Loading records…
    </div>
  );
}
export function Empty({ text = 'No records yet. Your records will appear here.' }) {
  return (
    <div className="empty">
      <Inbox size={30} />
      <strong>Nothing here yet</strong>
      <span>{text}</span>
    </div>
  );
}
export function Badge({ value }) {
  return <span className={`badge ${value}`}>{value?.replaceAll('_', ' ')}</span>;
}
export function PageHead({ eyebrow = 'WORKSPACE', title, subtitle, children }) {
  return (
    <div className="page-head">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{subtitle}</p>
      </div>
      <div className="head-actions">{children}</div>
    </div>
  );
}
export function Field({ label, children, ...props }) {
  return (
    <label className="field">
      <span>{label}</span>
      {children || (props.type === 'date' ? <DateInput {...props} /> : <input {...props} />)}
    </label>
  );
}
export function Modal({ title, children, onClose, wide = false }) {
  const ref = useRef();
  useEffect(() => {
    const previous = document.activeElement;
    const modal = ref.current;
    modal.showModal();
    const cancel = (e) => {
      e.preventDefault();
      onClose();
    };
    modal.addEventListener('cancel', cancel);
    return () => {
      modal.removeEventListener('cancel', cancel);
      modal.close();
      previous?.focus();
    };
  }, []);
  return (
    <dialog ref={ref} className={wide ? 'wide' : ''}>
      <div className="modal-head">
        <h2>{title}</h2>
        <button type="button" className="icon-button" onClick={onClose} aria-label="Close dialog">
          <X />
        </button>
      </div>
      {children}
    </dialog>
  );
}
export function Pager({ data, page, setPage }) {
  if (!data || data.total <= data.page_size) return null;
  return (
    <div className="pager">
      <span>
        {(page - 1) * data.page_size + 1}–{Math.min(page * data.page_size, data.total)} of{' '}
        {data.total} records
      </span>
      <div>
        <button
          className="icon-button"
          disabled={page === 1}
          onClick={() => setPage(page - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft size={18} />
        </button>
        <span>Page {page}</span>
        <button
          className="icon-button"
          disabled={page * data.page_size >= data.total}
          onClick={() => setPage(page + 1)}
          aria-label="Next page"
        >
          <ChevronRight size={18} />
        </button>
      </div>
    </div>
  );
}
export function Table({ columns, rows, rowKey = 'id', empty }) {
  return rows?.length ? (
    <div className="table-scroll">
      <table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.label}>{c.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={r[rowKey] || i}>
              {columns.map((c) => (
                <td key={c.label}>{c.render ? c.render(r) : r[c.key] || '—'}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  ) : (
    <Empty text={empty} />
  );
}
export function SaveButton({ busy, text = 'Save record' }) {
  return (
    <button className="btn primary" disabled={busy}>
      {busy ? 'Saving…' : text}
    </button>
  );
}
export function Confirm({
  title,
  description,
  action,
  onClose,
  requireReason = true,
  confirmText = 'Confirm',
}) {
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return (
    <Modal title={title} onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await action(reason);
            onClose();
          } catch (e) {
            setError(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <p>{description}</p>
        {requireReason && (
          <Field
            label="Reason (recorded in the audit trail)"
            required
            minLength={5}
            maxLength={2000}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
          />
        )}
        <ErrorBox error={error} />
        <div className="form-actions">
          <button className="btn" type="button" onClick={onClose}>
            Cancel
          </button>
          <SaveButton busy={busy} text={confirmText} />
        </div>
      </form>
    </Modal>
  );
}
