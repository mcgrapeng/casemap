import { Link, useNavigate } from 'react-router-dom';
import { Moon, Sun, LogOut, KeyRound, Server } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useTheme } from '@/hooks/useTheme';
import { useAuth } from '@/components/providers/ApiProvider';
import { cn } from '@/lib/utils';

interface HeaderProps {
  serverOnline?: boolean;
  projectName?: string;
}

export function Header({ serverOnline = true, projectName }: HeaderProps) {
  const { effective, setTheme, theme } = useTheme();
  const { token, setToken } = useAuth();
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center gap-3 border-b bg-card/80 px-4 backdrop-blur supports-[backdrop-filter]:bg-card/60">
      <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight" aria-label="casemap home">
        <span
          className="inline-flex h-7 w-7 items-center justify-center rounded-md bg-primary text-primary-foreground"
          aria-hidden="true"
        >
          C
        </span>
        <span className="hidden sm:inline">casemap</span>
      </Link>

      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <span
          aria-hidden="true"
          className={cn(
            'inline-block h-2 w-2 rounded-full',
            serverOnline ? 'bg-status-passed' : 'bg-status-failed',
          )}
        />
        <span className="sr-only">{serverOnline ? 'Server online' : 'Server offline'}</span>
        <Server className="h-3.5 w-3.5" aria-hidden="true" />
      </div>

      {projectName && (
        <span className="hidden truncate text-sm font-medium md:inline" title={projectName}>
          · {projectName}
        </span>
      )}

      <div className="ml-auto flex items-center gap-2">
        {token && (
          <Badge variant="secondary" className="hidden gap-1 sm:inline-flex">
            <KeyRound className="h-3 w-3" /> token
          </Badge>
        )}
        <Button
          variant="ghost"
          size="icon"
          aria-label={effective === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
          onClick={() => setTheme(effective === 'dark' ? 'light' : 'dark')}
        >
          {effective === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        {theme === 'system' && <span className="sr-only">System theme</span>}
        {token && (
          <Button
            variant="ghost"
            size="icon"
            aria-label="Sign out"
            onClick={() => {
              setToken(null);
              navigate('/');
            }}
          >
            <LogOut className="h-4 w-4" />
          </Button>
        )}
      </div>
    </header>
  );
}
