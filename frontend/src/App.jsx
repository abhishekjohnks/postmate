import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/Auth';
import Shell from './layouts/Shell';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Customers from './pages/Customers';
import Payments from './pages/Payments';
import Reports from './pages/Reports';
import { Audit, Schemes, Staff } from './pages/Admin';
function Application() {
  const { user } = useAuth();
  if (!user) return <Login />;
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Dashboard />} />
        <Route path="customers" element={<Customers />} />
        <Route path="accounts" element={<Navigate to="/customers?view=accounts" replace />} />
        <Route path="dues" element={<Payments key="dues" dues />} />
        <Route path="payments" element={<Payments key="transactions" />} />
        <Route path="reports" element={<Reports />} />
        {user.role === 'super_admin' && (
          <>
            <Route path="staff" element={<Staff />} />
            <Route path="schemes" element={<Schemes />} />
            <Route path="audit" element={<Audit />} />
          </>
        )}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  );
}
export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Application />
      </AuthProvider>
    </BrowserRouter>
  );
}
