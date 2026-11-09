import { useState } from 'react';
import { Download, FileSpreadsheet, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/Auth';
import { useData } from '../hooks/useData';
import { download, params } from '../services/api';
import { ErrorBox, Field, PageHead } from '../components/UI';
import { localToday } from '../utils/format';

export default function Reports() {
  const { user } = useAuth();
  const [v, setV] = useState({
    date_from: localToday().slice(0, 8) + '01',
    date_to: localToday(),
    staff_id: '',
    scheme_id: '',
    post_office: '',
    page_number: 1,
    status: 'outstanding',
  });
  const [busy, setBusy] = useState('');
  const [error, setError] = useState('');
  const { data: schemes } = useData('/schemes');
  const { data: staff } = useData(
    user.role === 'super_admin' ? '/users?page_size=100' : '/auth/me',
  );
  const change = (key, value) => setV({ ...v, [key]: value });
  async function exportReport(kind) {
    setBusy(kind);
    setError('');
    try {
      await download(`/reports/${kind}?${params(v)}`, `postmate-${kind}-${v.date_from}.csv`);
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy('');
    }
  }
  return (
    <>
      <PageHead
        title="Reports"
        eyebrow="THE BIGGER PICTURE"
        subtitle="Turn your workspace records into clear, downloadable reports."
      />
      <section className="panel report-filters">
        <div className="panel-heading">
          <div>
            <h2>Choose your reporting period</h2>
            <p>Apply filters before downloading your report.</p>
          </div>
        </div>
        <div className="form-grid">
          <Field
            label="From date"
            type="date"
            value={v.date_from}
            onChange={(e) => change('date_from', e.target.value)}
          />
          <Field
            label="To date"
            type="date"
            value={v.date_to}
            onChange={(e) => change('date_to', e.target.value)}
          />
          <Field label="Scheme">
            <select value={v.scheme_id} onChange={(e) => change('scheme_id', e.target.value)}>
              <option value="">All schemes</option>
              {schemes?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          </Field>
          {user.role === 'super_admin' && (
            <Field label="Staff member">
              <select value={v.staff_id} onChange={(e) => change('staff_id', e.target.value)}>
                <option value="">All staff members</option>
                {staff?.items?.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.full_name}
                  </option>
                ))}
              </select>
            </Field>
          )}
          <Field
            label="Post office"
            value={v.post_office}
            onChange={(e) => change('post_office', e.target.value)}
          />
          <Field label="Due report status">
            <select value={v.status} onChange={(e) => change('status', e.target.value)}>
              {[
                'outstanding',
                'overdue',
                'due',
                'upcoming',
                'paid',
                'partially_paid',
                'cancelled',
              ].map((s) => (
                <option key={s} value={s}>
                  {s.replace('_', ' ')}
                </option>
              ))}
            </select>
          </Field>
          <Field
            label="Export batch (up to 1,000 records each)"
            type="number"
            min="1"
            value={v.page_number}
            onChange={(e) => change('page_number', e.target.value)}
          />
        </div>
      </section>
      <ErrorBox error={error} />
      <div className="report-grid">
        {[
          [
            'payments',
            'Payment collection report',
            'Transactions, collectors, references and receipt numbers. Reversed payments remain marked for reconciliation.',
          ],
          [
            'dues',
            'Payment schedule report',
            'Expected deposits, outstanding amounts, due dates and current payment status.',
          ],
        ].map(([kind, title, description]) => (
          <section className="panel report-card" key={kind}>
            <div className="stat-icon red">
              <FileSpreadsheet size={26} />
            </div>
            <h2>{title}</h2>
            <p>{description}</p>
            <button className="btn primary" disabled={!!busy} onClick={() => exportReport(kind)}>
              <Download size={17} />
              {busy === kind ? 'Preparing…' : 'Download CSV'}
            </button>
          </section>
        ))}
      </div>
      <div className="info-note">
        <ShieldCheck size={18} />
        Exports use your access permissions and are recorded in the audit trail. Dates apply to
        payment dates in collection reports and due dates in schedule reports.
      </div>
    </>
  );
}
