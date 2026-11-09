import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  ArrowUpRight,
  Bell,
  BookOpen,
  ChevronDown,
  CircleHelp,
  ClipboardList,
  FileChartColumn,
  LayoutDashboard,
  LogOut,
  Menu,
  Search,
  ShieldCheck,
  Users,
  Wallet,
  X,
} from 'lucide-react';
import { useAuth } from '../context/Auth';
import { useData } from '../hooks/useData';
import { ErrorBox } from '../components/UI';

export default function Shell() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');
  const [signingOut, setSigningOut] = useState(false);
  const { data: notifications } = useData('/notifications?page_size=1');
  const nav = [
    ['/', LayoutDashboard, 'Overview'],
    ['/customers', Users, 'Customers & schemes'],
    ['/dues', ClipboardList, 'Payment dues'],
    ['/payments', Wallet, 'Transactions'],
    ['/reports', FileChartColumn, 'Reports'],
  ];
  return (
    <div className="app-shell">
      <aside className={open ? 'sidebar mobile-open' : 'sidebar'}>
        <NavLink to="/" className="brand">
          <span className="brand-mark">
            P<span>↗</span>
          </span>
          <div>
            PostMate<small>EVERY SAVING COUNTS</small>
          </div>
        </NavLink>
        <button
          className="mobile-close icon-button"
          onClick={() => setOpen(false)}
          aria-label="Close navigation"
        >
          <X />
        </button>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {nav.map(([to, Icon, label]) => (
            <NavLink end={to === '/'} key={to} to={to} onClick={() => setOpen(false)}>
              <Icon size={19} />
              {label}
              {to === '/dues' && notifications?.total > 0 && (
                <span className="nav-count">{notifications.total}</span>
              )}
            </NavLink>
          ))}
        </nav>
        {user.role === 'super_admin' && (
          <>
            <div className="workspace-label">ADMINISTRATION</div>
            <nav aria-label="Administration">
              <NavLink to="/staff">
                <Users size={19} />
                Staff members
              </NavLink>
              <NavLink to="/schemes">
                <BookOpen size={19} />
                Scheme settings
              </NavLink>
              <NavLink to="/audit">
                <ShieldCheck size={19} />
                Audit trail
              </NavLink>
            </nav>
          </>
        )}
        <div className="sidebar-bottom">
          <div className="trust-card">
            <ShieldCheck size={22} />
            <strong>
              A little care.
              <br />A secure tomorrow.
            </strong>
            <p>
              Your postal savings,
              <br />
              all in one place.
            </p>
            <span>
              POSTMATE RECORD MANAGEMENT <ArrowUpRight size={14} />
            </span>
          </div>
        </div>
      </aside>
      {open && <div className="scrim" onClick={() => setOpen(false)} />}
      <div className="main-wrap">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="icon-button mobile-menu"
              aria-label="Open navigation"
              onClick={() => setOpen(true)}
            >
              <Menu />
            </button>
            <span>Workspace</span>
            <span className="slash">/</span>
            <strong>{user.role === 'super_admin' ? 'Super Admin' : 'Staff'}</strong>
          </div>
          <div className="top-actions">
            <span className="live-dot">Connected workspace</span>
            <button
              className="notification-button icon-button"
              aria-label={`Notifications, ${notifications?.total || 0} due payments`}
              onClick={() => navigate('/dues')}
            >
              <Bell size={20} />
              {notifications?.total > 0 && <i />}
            </button>
            <span className="top-divider" />
            <div className="avatar">{user.full_name.slice(0, 2).toUpperCase()}</div>
            <div className="profile-name">
              <strong>{user.full_name}</strong>
              <small>{user.role === 'super_admin' ? 'Super Administrator' : 'Staff member'}</small>
            </div>
            <button
              className="topbar-signout"
              disabled={signingOut}
              onClick={async () => {
                setSigningOut(true);
                setError('');
                try {
                  await logout();
                } catch (e) {
                  setError(e.message);
                  setSigningOut(false);
                }
              }}
            >
              <LogOut size={16} />
              <span>{signingOut ? 'Signing out…' : 'Sign out'}</span>
            </button>
          </div>
        </header>
        <main>
          <ErrorBox error={error} />
          <Outlet />
        </main>
        <footer>
          <span>© {new Date().getFullYear()} PostMate. Every saving counts.</span>
          <span>Internal record management · Not an official India Post service</span>
        </footer>
      </div>
    </div>
  );
}
