import { Link, useNavigate } from 'react-router-dom';
import { Plus, FolderOpen, Loader2, AlertTriangle, KeyRound } from 'lucide-react';
import { Shell } from '@/components/layout/Shell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';
import { useProjects } from '@/hooks/useProjects';
import { useAuth } from '@/components/providers/ApiProvider';
import { formatDate } from '@/lib/utils';
import { ApiError } from '@/lib/api';

export default function HomePage() {
  const navigate = useNavigate();
  const { token, setToken } = useAuth();
  const projects = useProjects();

  const isAdminRequired =
    projects.error instanceof ApiError && projects.error.status === 403;

  return (
    <Shell>
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Visualize API specs as interactive test-case brain maps.
          </p>
        </div>
        <Button asChild>
          <Link to="/projects/new" aria-label="Create new project">
            <Plus className="h-4 w-4" /> New Project
          </Link>
        </Button>
      </header>

      <ErrorBoundary>
        {!token ? (
          <Card>
            <CardHeader>
              <CardTitle>Sign in</CardTitle>
              <CardDescription>
                Enter an existing project API key to load it, or create a new project.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                onClick={() => {
                  const value = window.prompt('Paste your project API key');
                  if (value) setToken(value.trim());
                }}
              >
                <KeyRound className="h-4 w-4" /> Use existing key
              </Button>
            </CardContent>
          </Card>
        ) : isAdminRequired ? (
          <Card className="border-destructive/30">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-destructive">
                <AlertTriangle className="h-5 w-5" /> Admin token required
              </CardTitle>
              <CardDescription>
                Listing all projects needs the server&apos;s admin token. Sign out
                and re-enter your project key, or ask the server admin to set
                CASEMAP_SERVER_ADMIN_TOKEN.
              </CardDescription>
            </CardHeader>
          </Card>
        ) : projects.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading projects…
          </div>
        ) : projects.isError ? (
          <Card className="border-destructive/30">
            <CardHeader>
              <CardTitle>Failed to load</CardTitle>
              <CardDescription>
                {projects.error instanceof Error ? projects.error.message : 'Unknown error'}
              </CardDescription>
            </CardHeader>
          </Card>
        ) : (projects.data?.length ?? 0) === 0 ? (
          <EmptyState
            title="No projects yet"
            description="Create your first project to start generating test cases."
            action={
              <Button asChild>
                <Link to="/projects/new">
                  <Plus className="h-4 w-4" /> New Project
                </Link>
              </Button>
            }
          />
        ) : (
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" role="list">
            {(projects.data ?? []).map((p) => (
              <li key={p.id}>
                <Card className="h-full">
                  <CardHeader>
                    <CardTitle className="line-clamp-1">{p.name}</CardTitle>
                    <CardDescription>Created {formatDate(p.created_at)}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-muted-foreground">
                        {p.llm_provider ?? 'heuristic'} {p.llm_model ? `· ${p.llm_model}` : ''}
                      </span>
                      <Button size="sm" onClick={() => navigate(`/projects/${p.id}`)}>
                        <FolderOpen className="h-4 w-4" /> Open
                      </Button>
                    </div>
                    <Progress className="mt-3" value={0} aria-label="Progress (not yet loaded)" />
                  </CardContent>
                </Card>
              </li>
            ))}
          </ul>
        )}
      </ErrorBoundary>
    </Shell>
  );
}
