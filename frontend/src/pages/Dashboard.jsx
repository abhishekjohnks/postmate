import DateInput from '../components/DateInput';
import { Link } from 'react-router-dom';
import {
  ArrowDownLeft,
  ArrowRight,
  ArrowUpRight,
  CalendarDays,
  Clock3,
  Plus,
  Users,
  Wallet,
  BookOpen,
  CircleCheck,
  AlertTriangle,
  Sprout,
} from 'lucide-react';
import { useState } from 'react';
import { useAuth } from '../context/Auth';
import { useData } from '../hooks/useData';
import { params } from '../services/api';
import { Badge, Empty, ErrorBox, Loading, PageHead, Table } from '../components/UI';
import { date, localToday, money } from '../utils/format';
import SchemePieChart from '../components/SchemePieChart';

function Bars({ items, currency = false }) {
  const max = Math.max(1, ...items.map((i) => Number(i.value)));
  return items.length ? (
    <div className="horizontal-bars">
      {items.map((item, i) => (
        <div key={item.name}>
          <div>
            <span>
              <i style={{ background: ['#C62828', '#FBC02D', '#da7966', '#779486'][i % 4] }} />
              {item.name}
            </span>
            <strong>{currency ? money(item.value) : item.value}</strong>
          </div>
          <div className="bar-track">
            <div
              style={{
                width: `${(Number(item.value) / max) * 100}%`,
                background: ['#C62828', '#FBC02D', '#da7966', '#779486'][i % 4],
              }}
            />
          </div>
        </div>
      ))}
    </div>
  ) : (
    <Empty text="Charts appear as you add records." />
  );
}
export default function Dashboard() {
  const { user } = useAuth();
  const [portfolioView, setPortfolioView] = useState('accounts');
  const [filters, setFilters] = useState({});
  const { data: schemes } = useData('/schemes');
  const { data: staff } = useData(
    user.role === 'super_admin' ? '/users?page_size=100' : '/auth/me',
  );
  const { data: d, loading, error } = useData('/dashboard?' + params(filters));
  const cards = d
    ? [
        ['Total customers', d.total_customers, Users, 'Assigned customer records', 'red'],
        [
          'Scheme accounts',
          d.total_accounts,
          BookOpen,
          `${d.active_accounts} active accounts`,
          'yellow',
        ],
        [
          'Collected this month',
          money(d.month_collections),
          Wallet,
          `${money(d.today_collections)} collected today`,
          'green',
        ],
        ['Payments overdue', d.overdue, Clock3, `${d.upcoming} upcoming in 7 days`, 'orange'],
        ['Active accounts', d.active_accounts, CircleCheck, 'Currently open accounts', 'green'],
        ['Collected today', money(d.today_collections), Wallet, 'Payments dated today', 'red'],
        ['Upcoming dues', d.upcoming, CalendarDays, 'Today through the next 7 days', 'yellow'],
        ['Maturing soon', d.maturing, Sprout, 'Within the next 30 days', 'green'],
        ...(d.total_staff !== null
          ? [['Staff members', d.total_staff, Users, 'Across your workspace', 'red']]
          : []),
      ]
    : [];
  return (
    <>
      <PageHead
        eyebrow="YOUR DAY, AT A GLANCE"
        title={`Good ${new Date().getHours() < 12 ? 'morning' : new Date().getHours() < 17 ? 'afternoon' : 'evening'}, ${user.role === 'super_admin' ? 'Admin' : user.full_name.split(' ')[0]}..`}
        subtitle="Here’s what’s happening with your postal savings today."
      >
        <span className="date-pill">
          <CalendarDays size={16} />
          {date(localToday())}
        </span>
        <Link className="btn primary" to="/payments?record=1">
          <Plus size={17} />
          Record payment
        </Link>
      </PageHead>
      <div className="welcome-banner">
        <div>
          <span className="banner-label">A LITTLE CLARITY GOES A LONG WAY</span>
          <h2>Every account is someone’s tomorrow.</h2>
          <p>Keep collections on track and your customers a step closer to their goals.</p>
          <Link to="/dues">
            Review payment dues <ArrowRight size={16} />
          </Link>
        </div>
        <div className="banner-art" aria-hidden="true">
          <span className="art-circle" />
          <BookOpen size={88} strokeWidth={1} />
          <Sprout size={45} />
          <i />
          <i />
        </div>
      </div>
      <details className="dashboard-filter-panel">
        <summary>More dashboard filters</summary>
        <div className="toolbar">
          <select
            aria-label="Dashboard payment status"
            value={filters.status || ''}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">Outstanding dues</option>
            {['due', 'upcoming', 'overdue', 'partially_paid', 'paid', 'cancelled'].map((s) => (
              <option key={s} value={s}>
                {s.replace('_', ' ')}
              </option>
            ))}
          </select>
          <label className="inline-field">
            Report from
            <DateInput
              aria-label="Dashboard date from"
              type="date"
              value={filters.date_from || ''}
              onChange={(e) => setFilters({ ...filters, date_from: e.target.value })}
            />
          </label>
          <label className="inline-field">
            Report to
            <DateInput
              aria-label="Dashboard date to"
              type="date"
              value={filters.date_to || ''}
              onChange={(e) => setFilters({ ...filters, date_to: e.target.value })}
            />
          </label>
          <input
            aria-label="Dashboard post office"
            placeholder="Filter by post office"
            value={filters.post_office || ''}
            onChange={(e) => setFilters({ ...filters, post_office: e.target.value })}
          />
          <button className="text-link" onClick={() => setFilters({})}>
            Clear filters
          </button>
        </div>
      </details>
      <div className="section-heading">
        <h2>
          Workspace overview <span className="subtle">/ Live records</span>
        </h2>
        <div className="compact-filters">
          <select
            aria-label="Filter dashboard by scheme"
            value={filters.scheme_id || ''}
            onChange={(e) => setFilters({ ...filters, scheme_id: e.target.value })}
          >
            <option value="">All schemes</option>
            {schemes?.map((s) => (
              <option key={s.id} value={s.id}>
                {s.code}
              </option>
            ))}
          </select>
          {user.role === 'super_admin' && (
            <select
              aria-label="Filter dashboard by staff"
              value={filters.staff_id || ''}
              onChange={(e) => setFilters({ ...filters, staff_id: e.target.value })}
            >
              <option value="">All staff</option>
              {staff?.items?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.full_name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>
      <ErrorBox error={error} />
      {loading ? (
        <Loading />
      ) : (
        d && (
          <>
            <div className="stat-grid">
              {cards.slice(0, 4).map(([label, value, Icon, hint, color]) => (
                <div className="stat-card" key={label}>
                  <div>
                    <span>{label}</span>
                    <div className={`stat-icon ${color}`}>
                      <Icon size={19} />
                    </div>
                  </div>
                  <strong>{value}</strong>
                  <small>{hint}</small>
                </div>
              ))}
            </div>
            <div className="stat-extra-grid">
              {cards.slice(4).map(([label, value, Icon, hint, color]) => (
                <div className="stat-extra-card" key={label}>
                  <span className={`stat-icon ${color}`}>
                    <Icon size={16} />
                  </span>
                  <div>
                    <small>{label}</small>
                    <strong>{value}</strong>
                    <span>{hint}</span>
                  </div>
                </div>
              ))}
            </div>
            <div className="dashboard-grid">
              <section className="panel trends-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Collection overview</h2>
                    <p>Your last six months of payment collections</p>
                  </div>
                  <span className="legend">
                    <i />
                    Collections
                  </span>
                </div>
                {d.monthly_trends.length ? (
                  <div className="trend-chart">
                    {d.monthly_trends.map((item) => (
                      <div className="trend-column" key={item.name}>
                        <span>{money(item.value)}</span>
                        <div
                          style={{
                            height: Math.max(
                              5,
                              (Number(item.value) /
                                Math.max(1, ...d.monthly_trends.map((i) => Number(i.value)))) *
                                145,
                            ),
                          }}
                        />
                        <small>{item.name}</small>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty text="Record your first collection to see the trend." />
                )}
                <div className="panel-foot">
                  <span>
                    <CircleCheck size={15} />
                    Based on recorded payments, excluding reversals
                  </span>
                  <Link to="/reports">
                    View reports <ArrowUpRight size={15} />
                  </Link>
                </div>
              </section>
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>Scheme portfolio</h2>
                    <p>A snapshot of your savings portfolio</p>
                  </div>
                  <select
                    className="portfolio-select"
                    aria-label="Scheme portfolio measure"
                    value={portfolioView}
                    onChange={(e) => setPortfolioView(e.target.value)}
                  >
                    <option value="accounts">Accounts</option>
                    <option value="collections">Collections</option>
                  </select>
                </div>
                <SchemePieChart
                  items={
                    portfolioView === 'accounts' ? d.scheme_distribution : d.scheme_collections
                  }
                  currency={portfolioView === 'collections'}
                />
              </section>
            </div>
            <div className="dashboard-grid">
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>
                      Payment schedule snapshot{' '}
                      <span className="number-badge">{d.overdue + d.upcoming}</span>
                    </h2>
                    <p>A timely reminder makes all the difference</p>
                  </div>
                  <Link to="/dues" className="text-link">
                    View all <ArrowRight size={16} />
                  </Link>
                </div>
                <Table
                  rows={d.dues}
                  columns={[
                    {
                      label: 'CUSTOMER',
                      render: (r) => (
                        <div className="person-cell">
                          <span className="mini-avatar">
                            {r.customer_name.slice(0, 2).toUpperCase()}
                          </span>
                          <div>
                            <strong>{r.customer_name}</strong>
                            <small>{r.scheme_name}</small>
                          </div>
                        </div>
                      ),
                    },
                    { label: 'DUE DATE', render: (r) => date(r.due_date) },
                    { label: 'AMOUNT', render: (r) => money(r.outstanding) },
                    { label: 'STATUS', render: (r) => <Badge value={r.status} /> },
                  ]}
                />
              </section>
              <section className="panel quick-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Ahead of the curve</h2>
                    <p>Keep your next steps in sight</p>
                  </div>
                </div>
                <div className="maturity-highlight">
                  <span className="stat-icon yellow">
                    <CalendarDays size={22} />
                  </span>
                  <div>
                    <strong>{d.maturing} accounts maturing soon</strong>
                    <p>Within the next 30 days</p>
                  </div>
                </div>
                {d.maturing_accounts.slice(0, 3).map((a) => (
                  <div className="maturity-item" key={a.id}>
                    <strong>{a.customer_name}</strong>
                    <small>
                      {a.scheme_name} · {date(a.maturity_date)}
                    </small>
                  </div>
                ))}
                <div className="quick-links">
                  <Link to="/customers?add=1">
                    <Users size={18} />
                    Add a customer
                    <Plus size={16} />
                  </Link>
                  <Link to="/customers?view=accounts">
                    <BookOpen size={18} />
                    Browse customer accounts
                    <Plus size={16} />
                  </Link>
                  <Link to="/payments">
                    <Wallet size={18} />
                    Payment history
                    <ArrowRight size={16} />
                  </Link>
                </div>
                <div className="small-note">
                  <ShieldCheckIcon />
                  Records that care for tomorrow.
                </div>
              </section>
            </div>
            {user.role === 'super_admin' && (
              <div className="dashboard-grid">
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Staff collections</h2>
                      <p>Current month or selected reporting period</p>
                    </div>
                    <strong>{d.total_staff} staff members</strong>
                  </div>
                  <Bars items={d.staff_collections} currency />
                </section>
                <section className="panel">
                  <div className="panel-heading">
                    <div>
                      <h2>Customers by staff</h2>
                      <p>Customer assignments across your team</p>
                    </div>
                  </div>
                  <Bars items={d.staff_distribution} />
                </section>
              </div>
            )}
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h2>Recent transactions</h2>
                  <p>The latest additions to your payment records</p>
                </div>
                <Link to="/payments" className="text-link">
                  View history <ArrowRight size={16} />
                </Link>
              </div>
              <Table
                rows={d.recent_payments}
                columns={[
                  { label: 'CUSTOMER', key: 'customer_name' },
                  { label: 'SCHEME', key: 'scheme_name' },
                  { label: 'PAYMENT DATE', render: (r) => date(r.payment_date) },
                  { label: 'AMOUNT', render: (r) => money(r.amount) },
                  { label: 'COLLECTED BY', key: 'staff_name' },
                ]}
              />
            </section>
          </>
        )
      )}
    </>
  );
}
function ShieldCheckIcon() {
  return <CircleCheck size={15} />;
}
