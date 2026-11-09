import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import {
  ArrowUpRight,
  BookOpen,
  Building2,
  CalendarClock,
  CreditCard,
  Download,
  Eye,
  EyeOff,
  FileUp,
  Layers3,
  Pencil,
  Plus,
  Search,
  ShieldCheck,
  Sparkles,
  Users,
  Trash2,
  UserRound,
} from 'lucide-react';
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
import { date } from '../utils/format';
import CustomerAccountCard from '../components/CustomerAccountCard';
import CustomerForm from '../components/CustomerForm';
import Accounts, { EditAccount } from './Accounts';
import DocumentPreview from '../components/DocumentPreview';
import { PaymentForm } from './Payments';

function CustomerDetail({ customer, onClose }) {
  const { user } = useAuth();
  const canDelete = user.role === 'super_admin';
  const [preview, setPreview] = useState(null);
  const [revision, setRevision] = useState(0);
  const [manage, setManage] = useState(false);
  const [editAccount, setEditAccount] = useState(null);
  const [depositAccount, setDepositAccount] = useState(null);
  const [deleteAccount, setDeleteAccount] = useState(null);
  const [kind, setKind] = useState('aadhaar');
  const [error, setError] = useState('');
  const [identity, setIdentity] = useState(null);
  const [visibleIdentity, setVisibleIdentity] = useState({ aadhaar: false, pan: false });
  const [identityBusy, setIdentityBusy] = useState(false);
  const [remove, setRemove] = useState(null);
  const [busy, setBusy] = useState(false);
  const { data: docs } = useData(`/customers/${customer.id}/documents`, revision);
  const [accountPage, setAccountPage] = useState(1);
  const { data: accounts, error: accountsError } = useData(
    `/accounts?customer_id=${customer.id}&page_number=${accountPage}`,
    revision,
  );
  async function toggleIdentity(kind) {
    if (visibleIdentity[kind]) {
      setVisibleIdentity((v) => ({ ...v, [kind]: false }));
      return;
    }
    setIdentityBusy(true);
    setError('');
    try {
      setIdentity(await api(`/customers/${customer.id}/identity`, { method: 'POST' }));
      setVisibleIdentity((v) => ({ ...v, [kind]: true }));
    } catch (e) {
      setError(e.message);
    } finally {
      setIdentityBusy(false);
    }
  }
  return (
    <Modal title={customer.full_name} onClose={onClose} wide>
      <div className="detail-grid">
        <div>
          <small>Phone</small>
          <strong>{customer.phone}</strong>
        </div>
        <div>
          <small>Date of birth</small>
          <strong>{date(customer.dob)}</strong>
        </div>
        <div>
          <small>Post office</small>
          <strong>{customer.post_office}</strong>
        </div>
        <div>
          <small>Aadhaar</small>
          <div className="identity-value">
            <strong>
              {visibleIdentity.aadhaar ? identity?.aadhaar || '—' : customer.aadhaar || '—'}
            </strong>
            <button
              className="icon-button"
              disabled={identityBusy || !customer.aadhaar}
              aria-label={visibleIdentity.aadhaar ? 'Hide Aadhaar number' : 'Show Aadhaar number'}
              aria-pressed={visibleIdentity.aadhaar}
              onClick={() => toggleIdentity('aadhaar')}
            >
              {visibleIdentity.aadhaar ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>
        <div>
          <small>PAN</small>
          <div className="identity-value">
            <strong>{visibleIdentity.pan ? identity?.pan || '—' : customer.pan || '—'}</strong>
            <button
              className="icon-button"
              disabled={identityBusy || !customer.pan}
              aria-label={visibleIdentity.pan ? 'Hide PAN number' : 'Show PAN number'}
              aria-pressed={visibleIdentity.pan}
              onClick={() => toggleIdentity('pan')}
            >
              {visibleIdentity.pan ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>
        <div>
          <small>Address</small>
          <strong>{customer.address}</strong>
        </div>
      </div>
      <div className="profile-schemes-heading">
        <h3>
          <Layers3 size={18} />
          Scheme accounts
        </h3>
        <button className="btn small" onClick={() => setManage(true)}>
          <Plus size={15} />
          Add scheme
        </button>
      </div>
      <div className="profile-account-list">
        {accounts?.items.map((account) => (
          <CustomerAccountCard
            key={account.id}
            account={account}
            onEdit={setEditAccount}
            onDeposit={setDepositAccount}
            onDelete={setDeleteAccount}
            onNavigate={onClose}
            canDelete={canDelete}
          />
        ))}
      </div>
      <ErrorBox error={accountsError} />
      <Pager data={accounts} page={accountPage} setPage={setAccountPage} />
      <h3>Private documents</h3>
      <form
        className="upload-form"
        onSubmit={async (e) => {
          e.preventDefault();
          const form = e.currentTarget;
          const body = new FormData();
          body.append('file', form.elements.document.files[0]);
          setBusy(true);
          setError('');
          try {
            await api(`/customers/${customer.id}/documents?kind=${kind}`, { method: 'POST', body });
            setRevision((r) => r + 1);
            form.reset();
          } catch (e) {
            setError(e.message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <select aria-label="Document type" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="aadhaar">Aadhaar</option>
          <option value="pan">PAN</option>
          <option value="other">Other</option>
        </select>
        <input
          aria-label="Document file"
          name="document"
          type="file"
          accept="application/pdf,image/png,image/jpeg"
          required
        />
        <button className="btn" disabled={busy}>
          <FileUp size={16} />
          {busy ? 'Uploading…' : 'Upload'}
        </button>
      </form>
      <p className="muted">PDF, PNG or JPEG · Maximum 5 MB · Encrypted private storage</p>
      <ErrorBox error={error} />
      {docs?.map((doc) => (
        <div className="document-row" key={doc.id}>
          <strong>{doc.kind.toUpperCase()}</strong>
          <span>{Math.ceil(doc.size / 1024)} KB</span>
          <button className="text-link" onClick={() => setPreview(doc)}>
            <Eye size={15} />
            Preview
          </button>
          <button
            className="text-link"
            onClick={async () => {
              try {
                await download(
                  `/documents/${doc.id}`,
                  `${doc.kind}.${doc.content_type === 'application/pdf' ? 'pdf' : doc.content_type === 'image/png' ? 'png' : 'jpg'}`,
                );
              } catch (e) {
                setError(e.message);
              }
            }}
          >
            Download
          </button>
          {canDelete && (
            <button className="text-link danger" onClick={() => setRemove(doc)}>
              Delete
            </button>
          )}
        </div>
      ))}
      {canDelete && remove && (
        <Confirm
          title="Delete document"
          description="The uploaded document will be permanently removed. The deletion remains in the audit trail."
          action={async (reason) => {
            await api(`/documents/${remove.id}`, { method: 'DELETE', body: { reason } });
            setRevision((r) => r + 1);
          }}
          onClose={() => setRemove(null)}
        />
      )}
      {manage && (
        <CustomerForm
          customer={customer}
          onClose={() => setManage(false)}
          onSaved={() => setRevision((r) => r + 1)}
        />
      )}
      {depositAccount && (
        <PaymentForm
          account={depositAccount}
          onClose={() => setDepositAccount(null)}
          onSaved={() => setRevision((r) => r + 1)}
        />
      )}
      {editAccount && (
        <EditAccount
          account={editAccount}
          onClose={() => setEditAccount(null)}
          onSaved={() => setRevision((r) => r + 1)}
        />
      )}
      {canDelete && deleteAccount && (
        <Confirm
          title="Delete scheme account?"
          description="This account and its payment dues will be removed from your workspace. Existing payments and receipts remain in financial history."
          requireReason={false}
          confirmText="Delete account"
          action={async () => {
            await api(`/accounts/${deleteAccount.id}`, { method: 'DELETE' });
            setRevision((r) => r + 1);
          }}
          onClose={() => setDeleteAccount(null)}
        />
      )}
      {preview && <DocumentPreview document={preview} onClose={() => setPreview(null)} />}
    </Modal>
  );
}

export default function Customers() {
  const { user } = useAuth();
  const canDelete = user.role === 'super_admin';
  const [searchParams, setSearchParams] = useSearchParams();
  const [edit, setEdit] = useState(null);
  const [deleteCustomer, setDeleteCustomer] = useState(null);
  const [detail, setDetail] = useState(null);
  const [q, setQ] = useState('');
  const [sort, setSort] = useState('name');
  const [page, setPage] = useState(1);
  const [revision, setRevision] = useState(0);
  const adding = searchParams.has('add');
  const accountView = searchParams.get('view') === 'accounts';
  const { data: overview } = useData('/dashboard', revision);
  const { data, loading, error } = useData(
    '/customers?' + params({ q, sort, page_number: page }),
    revision,
  );
  const close = () => {
    setSearchParams(accountView ? { view: 'accounts' } : {});
    setEdit(null);
  };
  return (
    <>
      <PageHead
        title="Customers & schemes"
        eyebrow="PEOPLE & THEIR POSSIBILITIES"
        subtitle="One place for customer details, savings accounts and insurance policies."
      >
        <button className="btn primary" onClick={() => setSearchParams({ add: '1' })}>
          <Plus size={17} />
          Add customer
        </button>
      </PageHead>
      <div className="customer-hub-banner">
        <div className="hub-banner-copy">
          <span className="hub-kicker">
            <Sparkles size={14} />A MORE CONNECTED WORKSPACE
          </span>
          <h2>
            Every customer. Every scheme.
            <br />
            One complete picture.
          </h2>
          <p>
            Register a customer and their savings together. Keep every account connected to the
            person behind it.
          </p>
          <div className="hub-benefits">
            <span>
              <Users size={14} />
              Customer profiles
            </span>
            <span>
              <Layers3 size={14} />
              Multiple schemes
            </span>
            <span>
              <ShieldCheck size={14} />
              Private records
            </span>
          </div>
        </div>
        <div className="hub-illustration" aria-hidden="true">
          <div className="hub-orbit" />
          <div className="hub-person">
            <UserRound size={42} />
          </div>
          <span className="floating-scheme rd">
            <Building2 size={18} />
            RD
          </span>
          <span className="floating-scheme pli">
            <ShieldCheck size={18} />
            PLI
          </span>
          <span className="floating-scheme savings">
            <CreditCard size={18} />
            Savings
          </span>
        </div>
      </div>
      <div className="hub-stat-grid">
        {[
          [Users, 'Customers', overview?.total_customers, 'rose'],
          [Layers3, 'Scheme accounts', overview?.total_accounts, 'gold'],
          [ShieldCheck, 'Active accounts', overview?.active_accounts, 'sage'],
          [CalendarClock, 'Maturing in 30 days', overview?.maturing, 'blue'],
        ].map(([Icon, label, value, color]) => (
          <div className="hub-stat" key={label}>
            <span className={`hub-stat-icon ${color}`}>
              <Icon size={21} />
            </span>
            <div>
              <span>{label}</span>
              <strong>{value ?? '—'}</strong>
            </div>
            <ArrowUpRight size={16} />
          </div>
        ))}
      </div>
      <div className="hub-tabs" aria-label="Customer workspace views">
        <button className={!accountView ? 'selected' : ''} onClick={() => setSearchParams({})}>
          <Users size={17} />
          Customers<span>{overview?.total_customers ?? '—'}</span>
        </button>
        <button
          className={accountView ? 'selected' : ''}
          onClick={() => setSearchParams({ view: 'accounts' })}
        >
          <Layers3 size={17} />
          All scheme accounts<span>{overview?.total_accounts ?? '—'}</span>
        </button>
        <span className="hub-tab-note">
          <ShieldCheck size={14} />
          Linked to customer profiles
        </span>
      </div>
      {accountView ? (
        <Accounts embedded />
      ) : (
        <section className="panel customer-table-panel">
          <div className="toolbar">
            <label className="search-input">
              <Search size={18} />
              <input
                aria-label="Search customers"
                placeholder="Search name, phone or customer ID…"
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setPage(1);
                }}
              />
            </label>
            <select
              aria-label="Sort customers"
              value={sort}
              onChange={(e) => {
                setSort(e.target.value);
                setPage(1);
              }}
            >
              <option value="name">Name A–Z</option>
              <option value="newest">Newest first</option>
            </select>
            <span className="muted">{data?.total || 0} customers</span>
          </div>
          <ErrorBox error={error} />
          {loading ? (
            <Loading />
          ) : (
            <Table
              rows={data?.items}
              columns={[
                {
                  label: 'CUSTOMER',
                  render: (c) => (
                    <div className="person-cell">
                      <span className="mini-avatar">{c.full_name.slice(0, 2).toUpperCase()}</span>
                      <div>
                        <button className="text-link" onClick={() => setDetail(c)}>
                          {c.full_name}
                        </button>
                        <small>{c.customer_code}</small>
                      </div>
                    </div>
                  ),
                },
                { label: 'PHONE', key: 'phone' },
                { label: 'POST OFFICE', key: 'post_office' },
                {
                  label: 'SCHEMES',
                  render: (c) => (
                    <div className="customer-scheme-chips">
                      {c.schemes?.length ? (
                        c.schemes.map((code) => (
                          <span key={code}>
                            <BookOpen size={12} />
                            {code}
                          </span>
                        ))
                      ) : (
                        <span className="no-scheme">No scheme yet</span>
                      )}
                      <small>
                        {c.account_count || 0} account{c.account_count === 1 ? '' : 's'}
                      </small>
                    </div>
                  ),
                },
                {
                  label: 'STATUS',
                  render: (c) => <Badge value={c.active ? 'active' : 'inactive'} />,
                },
                {
                  label: 'ACTIONS',
                  render: (c) => (
                    <div className="row-actions">
                      {canDelete && (
                        <button
                          className="icon-button danger"
                          aria-label={`Delete ${c.full_name}`}
                          onClick={() => setDeleteCustomer(c)}
                        >
                          <Trash2 size={16} />
                        </button>
                      )}
                      <button
                        className="icon-button"
                        aria-label={`Edit ${c.full_name}`}
                        onClick={() => setEdit(c)}
                      >
                        <Pencil size={16} />
                      </button>
                      <button
                        className="icon-button"
                        aria-label={`View ${c.full_name}`}
                        onClick={() => setDetail(c)}
                      >
                        <Eye size={16} />
                      </button>
                    </div>
                  ),
                },
              ]}
            />
          )}
          <Pager data={data} page={page} setPage={setPage} />
        </section>
      )}
      {(adding || edit) && (
        <CustomerForm customer={edit} onClose={close} onSaved={() => setRevision((r) => r + 1)} />
      )}{' '}
      {detail && <CustomerDetail customer={detail} onClose={() => setDetail(null)} />}
      {canDelete && deleteCustomer && (
        <Confirm
          title="Delete customer?"
          description={`Remove ${deleteCustomer.full_name} and their scheme accounts from the workspace? Existing payments and receipts remain in financial history.`}
          requireReason={false}
          confirmText="Delete customer"
          action={async () => {
            await api(`/customers/${deleteCustomer.id}`, { method: 'DELETE' });
            setRevision((r) => r + 1);
          }}
          onClose={() => setDeleteCustomer(null)}
        />
      )}
    </>
  );
}
