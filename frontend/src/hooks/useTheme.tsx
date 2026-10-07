import * as React from 'react';

type Theme = 'light' | 'dark' | 'system';

interface ThemeContextValue {
  theme: Theme;
  setTheme: (t: Theme) => void;
  effective: 'light' | 'dark';
}

const ThemeContext = React.createContext<ThemeContextValue | null>(null);
const STORAGE_KEY = 'casemap-theme';

function readStoredTheme(): Theme {
  if (typeof window === 'undefined') return 'dark';
  const raw = window.localStorage.getItem(STORAGE_KEY);
  if (raw === 'light' || raw === 'dark' || raw === 'system') return raw;
  return 'dark';
}

function applyTheme(effective: 'light' | 'dark') {
  const root = document.documentElement;
  root.classList.toggle('dark', effective === 'dark');
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [theme, setThemeState] = React.useState<Theme>(readStoredTheme);
  const [system, setSystem] = React.useState<'light' | 'dark'>(() => {
    if (typeof window === 'undefined') return 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  });

  React.useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = (e: MediaQueryListEvent) => setSystem(e.matches ? 'dark' : 'light');
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);

  const effective: 'light' | 'dark' = theme === 'system' ? system : theme;

  React.useEffect(() => {
    applyTheme(effective);
    window.localStorage.setItem(STORAGE_KEY, theme);
  }, [theme, effective]);

  const value = React.useMemo<ThemeContextValue>(
    () => ({ theme, setTheme: setThemeState, effective }),
    [theme, effective],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = React.useContext(ThemeContext);
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider');
  return ctx;
}
