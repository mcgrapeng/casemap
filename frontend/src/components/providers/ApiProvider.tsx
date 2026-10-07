import * as React from 'react';
import { getAuthToken, setAuthToken } from '@/lib/api';

interface AuthContextValue {
  token: string | null;
  setToken: (t: string | null) => void;
}

const AuthContext = React.createContext<AuthContextValue | null>(null);
const STORAGE_KEY = 'casemap-token';

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = React.useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    return window.localStorage.getItem(STORAGE_KEY);
  });

  React.useEffect(() => {
    setAuthToken(token);
    if (token) window.localStorage.setItem(STORAGE_KEY, token);
    else window.localStorage.removeItem(STORAGE_KEY);
  }, [token]);

  // sync once on mount in case other tabs changed it
  React.useEffect(() => {
    const initial = getAuthToken();
    if (initial !== token) setTokenState(initial);
  }, [token]);

  const value = React.useMemo<AuthContextValue>(
    () => ({ token, setToken: setTokenState }),
    [token],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = React.useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
