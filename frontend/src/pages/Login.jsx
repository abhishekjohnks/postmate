import { useState } from 'react';
import { ArrowRight, LockKeyhole, ShieldCheck } from 'lucide-react';
import { useAuth } from '../context/Auth';
import { ErrorBox, Field } from '../components/UI';

export default function Login() {
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  return (
    <div className="login-screen">
      <section className="login-story">
        <div className="brand">
          <span className="brand-mark">
            P<span>↗</span>
          </span>
          <div>
            PostMate<small>EVERY SAVING COUNTS</small>
          </div>
        </div>
        <div className="login-story-content">
          <span className="outline-label">BUILT AROUND PEOPLE</span>
          <h1>
            Small savings.
            <br />
            Life’s big
            <br />
            <em>possibilities.</em>
          </h1>
          <p>
            A thoughtful workspace for the people who help
            <br />
            their communities save for tomorrow.
          </p>
          <div className="postal-art" aria-hidden="true">
            <div className="art-stamp">
              PM
              <br />
              <small>SAVING FOR TOMORROW</small>
            </div>
            <div className="art-lines">
              <i />
              <i />
              <i />
            </div>
            <span>POSTMATE / RECORDS WITH CARE</span>
          </div>
        </div>
        <small>POSTAL SAVINGS & INSURANCE MANAGEMENT</small>
      </section>
      <section className="login-form-wrap">
        <div className="login-form">
          <div className="login-icon">
            <LockKeyhole />
          </div>
          <div className="eyebrow">YOUR WORKSPACE AWAITS</div>
          <h2>Welcome back.</h2>
          <p>Sign in to keep good things growing.</p>
          <form
            onSubmit={async (e) => {
              e.preventDefault();
              setBusy(true);
              setError('');
              try {
                await login(username, password);
              } catch (e) {
                setError(e.message);
              } finally {
                setBusy(false);
              }
            }}
          >
            <Field
              label="Username"
              autoComplete="username"
              required
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Enter your username"
            />
            <Field
              label="Password"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Enter your password"
            />
            <ErrorBox error={error} />
            <button className="btn primary login-submit" disabled={busy}>
              {busy ? 'Signing in…' : 'Sign in to PostMate'}
              <ArrowRight size={18} />
            </button>
          </form>
          <div className="login-security">
            <ShieldCheck size={18} /> Secure access for authorized staff only
          </div>
          <p className="login-help">Need access? Contact your Super Admin.</p>
        </div>
      </section>
    </div>
  );
}
