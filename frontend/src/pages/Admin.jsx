import { useState } from 'react';
import { Plus, Pencil, Search, ShieldCheck } from 'lucide-react';
import { useData } from '../hooks/useData';
import { api, params } from '../services/api';
import {
  Badge,
  ErrorBox,
  Field,
  Loading,
  Modal,
  PageHead,
  Pager,
  SaveButton,
  Table,
} from '../components/UI';
import { date } from '../utils/format';

function StaffForm({ staff, onClose, onSaved }) {
  const [v, setV] = useState(
    staff
      ? {
          full_name: staff.full_name,
          role: staff.role,
          active: staff.active,
          phone: staff.profile?.phone || '',
          post_office: staff.profile?.post_office || '',
          agent_id: staff.profile?.agent_id || '',
        }
      : {
          username: '',
          full_name: '',
          role: 'staff',
          password: '',
          phone: '',
          post_office: '',
          agent_id: '',
        },
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  return (
    <Modal title={staff ? 'Update staff member' : 'Add staff member'} onClose={onClose}>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          const payload = { ...v };
          if (staff && !payload.password) delete payload.password;
          try {
            await api(staff ? `/users/${staff.id}` : '/users', {
              method: staff ? 'PATCH' : 'POST',
              body: payload,
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
        {!staff && (
          <Field
            label="Username"
            required
            minLength={3}
            pattern="[a-zA-Z0-9_.@-]+"
            value={v.username}
            onChange={(e) => setV({ ...v, username: e.target.value })}
          />
        )}
        <Field
          label="Full name"
          required
          minLength={2}
          value={v.full_name}
          onChange={(e) => setV({ ...v, full_name: e.target.value })}
        />
        <Field
          label={staff ? 'New password (optional)' : 'Initial password'}
          type="password"
          required={!staff}
          minLength={12}
          maxLength={128}
          autoComplete="new-password"
          value={v.password || ''}
          onChange={(e) => setV({ ...v, password: e.target.value })}
        />
        <div className="staff-role-note">
          <ShieldCheck size={19} />
          <div>
            <strong>Staff account</strong>
            <p>Access is limited to assigned customers and their records.</p>
          </div>
        </div>
        {['phone', 'post_office', 'agent_id'].map((key) => (
          <Field
            key={key}
            label={key.replaceAll('_', ' ')}
            value={v[key]}
            onChange={(e) => setV({ ...v, [key]: e.target.value })}
          />
        ))}
        {staff && (
          <Field label="Access status">
            <select
              value={v.active ? 'active' : 'inactive'}
              onChange={(e) => setV({ ...v, active: e.target.value === 'active' })}
            >
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </Field>
        )}
        <p className="muted">Changing access or resetting a password revokes existing sessions.</p>
        <ErrorBox error={error} />
        <div className="form-actions">
          <SaveButton busy={busy} />
        </div>
      </form>
    </Modal>
  );
}
export function Staff() {
  const [modal, setModal] = useState(null);
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [rev, setRev] = useState(0);
  const { data, loading, error } = useData('/users?' + params({ q, page_number: page }), rev);
  return (
    <>
      <PageHead
        title="Staff members"
        eyebrow="YOUR TEAM, CONNECTED"
        subtitle="Manage the people who keep your workspace moving."
      >
        <button className="btn primary" onClick={() => setModal({})}>
          <Plus size={17} />
          Add staff
        </button>
      </PageHead>
      <section className="panel">
        <div className="toolbar">
          <label className="search-input">
            <Search size={18} />
            <input
              aria-label="Search staff"
              placeholder="Find a staff member…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
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
              { label: 'STAFF MEMBER', key: 'full_name' },
              { label: 'USERNAME', key: 'username' },
              { label: 'ROLE', render: (s) => <Badge value={s.role} /> },
              { label: 'POST OFFICE', render: (s) => s.profile?.post_office || '—' },
              {
                label: 'STATUS',
                render: (s) => <Badge value={s.active ? 'active' : 'inactive'} />,
              },
              {
                label: 'ACTIONS',
                render: (s) =>
                  s.role === 'staff' ? (
                    <button
                      className="icon-button"
                      aria-label={`Edit ${s.full_name}`}
                      onClick={() => setModal(s)}
                    >
                      <Pencil size={17} />
                    </button>
                  ) : (
                    <span className="protected-admin">
                      <ShieldCheck size={14} />
                      Protected
                    </span>
                  ),
              },
            ]}
          />
        )}
        <Pager data={data} page={page} setPage={setPage} />
      </section>
      {modal && (
        <StaffForm
          staff={modal.id ? modal : null}
          onClose={() => setModal(null)}
          onSaved={() => setRev((r) => r + 1)}
        />
      )}
    </>
  );
}

function SchemeForm({ scheme, onClose, onSaved }) {
  const [v, setV] = useState(
    scheme
      ? {
          code: scheme.code,
          name: scheme.name,
          description: scheme.description,
          active: scheme.active,
          frequency_months: scheme.frequency_months,
          duration_months: scheme.duration_months,
          schedule_kind: scheme.schedule_kind,
          allow_partial: scheme.allow_partial,
          historical_only: scheme.historical_only,
          fields: scheme.fields.map(({ key, label, field_type, required }) => ({
            key,
            label,
            field_type,
            required,
          })),
        }
      : {
          code: '',
          name: '',
          description: '',
          active: true,
          frequency_months: 1,
          duration_months: null,
          schedule_kind: 'collection',
          allow_partial: false,
          historical_only: false,
          fields: [],
        },
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const update = (key, value) => setV({ ...v, [key]: value });
  return (
    <Modal title={scheme ? 'Configure scheme' : 'Create a scheme'} onClose={onClose} wide>
      <form
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          try {
            await api(scheme ? `/schemes/${scheme.id}` : '/schemes', {
              method: scheme ? 'PUT' : 'POST',
              body: {
                ...v,
                frequency_months: v.schedule_kind === 'discretionary' ? null : v.frequency_months,
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
        <div className="form-grid">
          <Field
            label="Scheme code"
            required
            pattern="[A-Z0-9_-]+"
            value={v.code}
            onChange={(e) => update('code', e.target.value)}
          />
          <Field
            label="Scheme name"
            required
            value={v.name}
            onChange={(e) => update('name', e.target.value)}
          />
          <Field
            label={
              v.schedule_kind === 'discretionary'
                ? 'Frequency: flexible / no fixed interval'
                : 'Frequency in months (0 = single deposit)'
            }
            type="number"
            min={0}
            max={120}
            value={v.schedule_kind === 'discretionary' ? '' : (v.frequency_months ?? '')}
            disabled={v.schedule_kind === 'discretionary'}
            placeholder={v.schedule_kind === 'discretionary' ? 'Any amount, any month' : ''}
            onChange={(e) =>
              update('frequency_months', e.target.value === '' ? null : Number(e.target.value))
            }
          />
          <Field
            label="Term in months (blank = account specific)"
            type="number"
            min={1}
            max={1200}
            value={v.duration_months ?? ''}
            onChange={(e) =>
              update('duration_months', e.target.value === '' ? null : Number(e.target.value))
            }
          />
          <Field label="Schedule rule">
            <select
              value={v.schedule_kind}
              onChange={(e) =>
                setV({
                  ...v,
                  schedule_kind: e.target.value,
                  frequency_months:
                    e.target.value === 'discretionary' ? null : e.target.value === 'income' ? 0 : 1,
                })
              }
            >
              <option value="collection">Scheduled collections</option>
              <option value="discretionary">
                Flexible deposits — no fixed schedule (SSA / PPF)
              </option>
              <option value="income">Income scheme (collect initial deposit)</option>
            </select>
          </Field>
          <Field
            label="Description / verified rules"
            value={v.description}
            onChange={(e) => update('description', e.target.value)}
          />
        </div>
        {v.schedule_kind === 'discretionary' && (
          <p className="info-note">
            Customers can deposit different amounts at irregular intervals. No automatic monthly
            dues are created. Each deposit is entered separately. Changing a scheme only affects new
            accounts; existing account schedules are retained.
          </p>
        )}
        <div className="checks">
          {[
            ['active', 'Active scheme'],
            ['allow_partial', 'Permit partial instalment payments'],
            ['historical_only', 'Historical records only'],
          ].map(([key, label]) => (
            <label className="check-field" key={key}>
              <input
                type="checkbox"
                checked={v[key]}
                onChange={(e) => update(key, e.target.checked)}
              />
              {label}
            </label>
          ))}
        </div>
        <h3>Account identifiers & custom fields</h3>
        <p className="muted">
          Use account_number, policy_number, cif_id or agent_id for common identifiers. Add other
          keys for custom account fields.
        </p>
        {v.fields.map((f, i) => (
          <div className="scheme-field-row" key={i}>
            <input
              aria-label={`Field ${i + 1} key`}
              required
              pattern="[a-z][a-z0-9_]*"
              placeholder="field_key"
              value={f.key}
              onChange={(e) =>
                update(
                  'fields',
                  v.fields.map((field, n) => (n === i ? { ...field, key: e.target.value } : field)),
                )
              }
            />
            <input
              aria-label={`Field ${i + 1} label`}
              required
              placeholder="Display label"
              value={f.label}
              onChange={(e) =>
                update(
                  'fields',
                  v.fields.map((field, n) =>
                    n === i ? { ...field, label: e.target.value } : field,
                  ),
                )
              }
            />
            <select
              aria-label={`Field ${i + 1} type`}
              value={f.field_type}
              onChange={(e) =>
                update(
                  'fields',
                  v.fields.map((field, n) =>
                    n === i ? { ...field, field_type: e.target.value } : field,
                  ),
                )
              }
            >
              {['text', 'number', 'date'].map((t) => (
                <option key={t}>{t}</option>
              ))}
            </select>
            <label className="check-field">
              <input
                type="checkbox"
                checked={f.required}
                onChange={(e) =>
                  update(
                    'fields',
                    v.fields.map((field, n) =>
                      n === i ? { ...field, required: e.target.checked } : field,
                    ),
                  )
                }
              />
              Required
            </label>
            <button
              className="text-link danger"
              type="button"
              onClick={() =>
                update(
                  'fields',
                  v.fields.filter((_, n) => n !== i),
                )
              }
            >
              Remove
            </button>
          </div>
        ))}
        <button
          className="btn small"
          type="button"
          onClick={() =>
            update('fields', [
              ...v.fields,
              { key: '', label: '', field_type: 'text', required: false },
            ])
          }
        >
          <Plus size={16} />
          Add field
        </button>
        <div className="info-note">
          Confirm rules against the relevant Post Office records. Changes apply to newly opened
          accounts; existing schedules and account rules are retained.
        </div>
        <ErrorBox error={error} />
        <div className="form-actions">
          <SaveButton busy={busy} text="Save scheme configuration" />
        </div>
      </form>
    </Modal>
  );
}

export function Schemes() {
  const [modal, setModal] = useState(null);
  const [rev, setRev] = useState(0);
  const { data, loading, error } = useData('/schemes', rev);
  return (
    <>
      <PageHead
        title="Scheme settings"
        eyebrow="FLEXIBLE BY DESIGN"
        subtitle="Configure account fields, terms, and collection rules."
      >
        <button className="btn primary" onClick={() => setModal({})}>
          <Plus size={17} />
          Create scheme
        </button>
      </PageHead>
      <ErrorBox error={error} />
      {loading ? (
        <Loading />
      ) : (
        <div className="scheme-grid">
          {data?.map((s) => (
            <section className="panel scheme-card" key={s.id}>
              <div>
                <span className="scheme-code">{s.code}</span>
                <Badge value={s.active ? 'active' : 'inactive'} />
              </div>
              <h2>{s.name}</h2>
              <p>{s.description}</p>
              <dl>
                <div>
                  <dt>Frequency</dt>
                  <dd>
                    {s.frequency_months === null
                      ? 'Manual deposits'
                      : s.frequency_months === 0
                        ? 'Single deposit'
                        : `Every ${s.frequency_months} month(s)`}
                  </dd>
                </div>
                <div>
                  <dt>Term</dt>
                  <dd>{s.duration_months ? `${s.duration_months} months` : 'Account specific'}</dd>
                </div>
                <div>
                  <dt>Required fields</dt>
                  <dd>
                    {s.fields
                      .filter((f) => f.required)
                      .map((f) => f.label)
                      .join(', ') || 'Configured at opening'}
                  </dd>
                </div>
              </dl>
              <button className="btn" onClick={() => setModal(s)}>
                <Pencil size={15} />
                Configure scheme
              </button>
            </section>
          ))}
        </div>
      )}
      {modal && (
        <SchemeForm
          scheme={modal.id ? modal : null}
          onClose={() => setModal(null)}
          onSaved={() => setRev((r) => r + 1)}
        />
      )}
    </>
  );
}
export function Audit() {
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const { data, loading, error } = useData('/audit-logs?' + params({ q, page_number: page }));
  return (
    <>
      <PageHead
        title="Audit trail"
        eyebrow="ACCOUNTABILITY, BUILT IN"
        subtitle="A traceable record of important workspace activity."
      />
      <section className="panel">
        <div className="toolbar">
          <label className="search-input">
            <Search size={18} />
            <input
              aria-label="Filter audit actions"
              placeholder="Filter by action, e.g. payment…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
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
              { label: 'WHEN', render: (r) => new Date(r.created_at).toLocaleString('en-IN') },
              { label: 'ACTION', key: 'action' },
              { label: 'ENTITY', key: 'entity_type' },
              { label: 'ACTOR ID', key: 'user_id' },
              { label: 'DETAILS', render: (r) => <code>{JSON.stringify(r.details)}</code> },
            ]}
          />
        )}
        <Pager data={data} page={page} setPage={setPage} />
      </section>
    </>
  );
}
