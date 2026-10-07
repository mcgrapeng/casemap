import * as React from 'react';
import { getAdminToken, getAuthToken, setAdminToken, setAuthToken } from '@/lib/api';

interface AuthContextValue {
  token: string | null;
  setToken: (t: string | null) => void;
  adminToken: string | null;
  setAdminToken: (t: string | null) => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);
const STORAGE_KEY = 'casemap-token';
const ADMIN_STORAGE_KEY = 'casemap.admin_token';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = React.useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(STORAGE_KEY);
  });
  const [adminToken, setAdminTokenState] = React.useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(ADMIN_STORAGE_KEY);
  });

  React.useEffect(() => {
    setAuthToken(token);
    if (token) window.localStorage.setItem(STORAGE_KEY, token);
    else window.localStorage.removeItem(STORAGE_KEY);
  }, [token]);

  React.useEffect(() => {
    setAdminToken(adminToken);
    if (adminToken) window.localStorage.setItem(ADMIN_STORAGE_KEY, adminToken);
    else window.localStorage.removeItem(ADMIN_STORAGE_KEY);
  }, [adminToken]);

  // sync once on mount in case other tabs changed it
  React.useEffect(() => {
    const initial = getAuthToken();
    if (initial !== token) setTokenState(initial);
  }, [token]);

  React.useEffect(() => {
    const initial = getAdminToken();
    if (initial !== adminToken) setAdminTokenState(initial);
  }, [adminToken]);

  const value = React.useMemo<AuthContextValue>(
    () => ({
      token,
      setToken: setTokenState,
      adminToken,
      setAdminToken: setAdminTokenState,
    }),
    [token, adminToken],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
