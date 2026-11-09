import { createContext, useContext, useState } from 'react';
import { api, setSession } from '../services/api';
const Context = createContext();
export const useAuth = () => useContext(Context);
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  async function login(username, password) {
    const data = await api('/auth/login', {
      method: 'POST',
      body: new URLSearchParams({ username, password }),
    });
    setSession(data.access_token, () => {
      setUser(null);
      setSession(null);
    });
    setUser(data.user);
  }
  async function logout() {
    await api('/auth/logout', { method: 'POST' });
    setSession(null);
    setUser(null);
  }
  return <Context.Provider value={{ user, login, logout }}>{children}</Context.Provider>;
}
