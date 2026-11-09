import { useState } from 'react';
import {
  BadgeCheck,
  Building2,
  CircleUserRound,
  CreditCard,
  Fingerprint,
  Layers3,
  Plus,
  ShieldCheck,
  Trash2,
} from 'lucide-react';
import { useAuth } from '../context/Auth';
import { useData } from '../hooks/useData';
import { api } from '../services/api';
import { ErrorBox, Field, Modal, SaveButton } from './UI';
import SchemeFields, { accountPayload, newSchemeDraft } from './SchemeFields';

export default function CustomerForm({ customer, onClose, onSaved }) {
  const { user } = useAuth();
  const { data: staff } = useData(
    user.role === 'super_admin' ? '/users?page_size=100' : '/auth/me',
  );
  const { data: schemes, error: schemesError } = useData('/schemes');
  const [values, setValues] = useState(
    customer
      ? {
          full_name: customer.full_name,
          dob: customer.dob,
          phone: customer.phone,
          address: customer.address,
          post_office: customer.post_office,
          location: customer.location,
          staff_id: customer.staff_id,
          active: customer.active,
        }
      : {
          full_name: '',
          dob: '',
          phone: '',
          address: '',
          post_office: '',
          location: '',
          active: true,
        },
  );
  const [drafts, setDrafts] = useState(customer ? [] : [newSchemeDraft()]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const field = (key, label, type = 'text', required = true, extra = {}) => (
    <Field
      key={key}
      label={label}
      type={type}
      required={required}
      value={values[key] || ''}
      onChange={(e) => setValues({ ...values, [key]: e.target.value })}
      {...extra}
    />
  );
  const section = (Icon, title, subtitle) => (
    <div className="form-section-heading">
      <span>
        <Icon size={20} />
      </span>
      <div>
        <h3>{title}</h3>
        <p>{subtitle}</p>
      </div>
    </div>
  );
  return (
    <Modal
      title={customer ? 'Customer details & schemes' : 'Add customer & schemes'}
      onClose={onClose}
      wide
    >
      <form
        className="customer-onboarding"
        onSubmit={async (e) => {
          e.preventDefault();
          setBusy(true);
          setError('');
          const payload = { ...values };
          if (!payload.aadhaar) delete payload.aadhaar;
          if (!payload.pan) delete payload.pan;
          try {
            await api(customer ? `/customers/${customer.id}/registration` : '/customers/register', {
              method: customer ? 'PUT' : 'POST',
              body: {
                customer: payload,
                accounts: drafts.map((d) => accountPayload(d, values.post_office)),
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
        <div className="onboarding-intro">
          <span className="intro-icon">
            <CircleUserRound size={25} />
          </span>
          <div>
            <strong>One customer. All their savings.</strong>
            <p>Add personal details and scheme accounts together in one place.</p>
          </div>
          <span className="secure-pill">
            <ShieldCheck size={14} />
            Secure record
          </span>
        </div>
        {section(CircleUserRound, 'Personal details', 'The person behind every saving.')}
        <div className="form-grid">
          {field('full_name', 'Full name', 'text', true, { maxLength: 200 })}
          {field('dob', 'Date of birth', 'date')}
          {field('phone', 'Phone number', 'tel', true, { minLength: 10, maxLength: 20 })}
          {field('location', 'Location')}
          {field('address', 'Address', 'text', true, { minLength: 5 })}
          {field('post_office', 'Post office')}
          {user.role === 'super_admin' && (
            <Field label="Assigned staff">
              <select
                value={values.staff_id || ''}
                onChange={(e) => setValues({ ...values, staff_id: e.target.value || null })}
              >
                <option value="">Assign to me</option>
                {staff?.items
                  ?.filter((s) => s.active && s.role === 'staff')
                  .map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.full_name}
                    </option>
                  ))}
              </select>
            </Field>
          )}
          {customer && (
            <Field label="Customer status">
              <select
                value={values.active ? 'active' : 'inactive'}
                onChange={(e) => setValues({ ...values, active: e.target.value === 'active' })}
              >
                <option value="active">Active</option>
                <option value="inactive">Inactive</option>
              </select>
            </Field>
          )}
        </div>
        <details className="identity-section">
          <summary>
            <Fingerprint size={18} />
            Identity details <span>Optional · encrypted</span>
          </summary>
          <div className="form-grid">
            {field(
              'aadhaar',
              customer ? 'Replace Aadhaar (optional)' : 'Aadhaar number (optional)',
              'text',
              false,
              { pattern: '[0-9]{12}', maxLength: 12, inputMode: 'numeric' },
            )}
            {field(
              'pan',
              customer ? 'Replace PAN (optional)' : 'PAN number (optional)',
              'text',
              false,
              { pattern: '[A-Z]{5}[0-9]{4}[A-Z]', maxLength: 10 },
            )}
          </div>
        </details>
        {section(
          Layers3,
          'Savings & insurance schemes',
          customer
            ? 'Add another scheme to this customer. Existing accounts stay in their profile.'
            : 'Choose one or more schemes while registering this customer.',
        )}
        <ErrorBox error={schemesError} />
        {drafts.map((draft, index) => (
          <fieldset className="scheme-draft" key={draft.clientKey}>
            <legend>
              <CreditCard size={16} />
              Scheme {String(index + 1).padStart(2, '0')}
            </legend>
            <div className="draft-topline">
              <span>ACCOUNT DETAILS</span>
              <button
                className="icon-button"
                type="button"
                aria-label={`Remove scheme ${index + 1}`}
                disabled={!customer && drafts.length === 1}
                onClick={() =>
                  setDrafts((d) => d.filter((item) => item.clientKey !== draft.clientKey))
                }
              >
                <Trash2 size={16} />
              </button>
            </div>
            <SchemeFields
              value={draft}
              schemes={schemes}
              postOffice={values.post_office}
              onChange={(next) =>
                setDrafts((d) =>
                  d.map((item) => (item.clientKey === draft.clientKey ? next : item)),
                )
              }
            />
          </fieldset>
        ))}
        <button
          className="add-scheme-button"
          type="button"
          disabled={drafts.length >= 20 || busy}
          onClick={() => setDrafts((d) => [...d, newSchemeDraft()])}
        >
          <Plus size={18} />
          {drafts.length ? 'Add another scheme' : 'Add a scheme account'}
          <span>RD, PLI, RPLI & more</span>
        </button>
        <ErrorBox error={error} />
        <div className="form-actions">
          <span className="save-hint">
            <BadgeCheck size={15} />
            {drafts.length} new scheme{drafts.length === 1 ? '' : 's'}
          </span>
          <button className="btn" type="button" disabled={busy} onClick={onClose}>
            Cancel
          </button>
          <SaveButton
            busy={busy || !schemes}
            text={customer ? 'Save customer & schemes' : 'Create customer & schemes'}
          />
        </div>
      </form>
    </Modal>
  );
}
