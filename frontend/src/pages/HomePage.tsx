import { useNavigate } from 'react-router-dom';
import * as React from 'react';
import { Plus, FolderOpen, Loader2, AlertTriangle, KeyRound, ShieldCheck } from 'lucide-react';
import { Shell } from '@/components/layout/Shell';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Progress } from '@/components/ui/progress';
import { EmptyState } from '@/components/shared/EmptyState';
import { ErrorBoundary } from '@/components/shared/ErrorBoundary';
import { useProjects } from '@/hooks/useProjects';
import { useAuth } from '@/components/providers/ApiProvider';
import { useToast } from '@/hooks/useToast';
import { formatDate } from '@/lib/utils';
import { ApiError } from '@/lib/api';

export default function HomePage() {
  const navigate = useNavigate();
  const { token, setToken, adminToken, setAdminToken } = useAuth();
  const projects = useProjects();
  const { toast } = useToast();
  const [adminDraft, setAdminDraft] = React.useState('');
  const [adminEditing, setAdminEditing] = React.useState(false);

  const isAdminRequired =
    projects.error instanceof ApiError && projects.error.status === 403;

  const handleNewProject = () => {
    if (!adminToken) {
      toast({
        title: '请先输入管理员令牌',
        description: '创建新项目需要服务器管理员令牌 (CASEMAP_SERVER_ADMIN_TOKEN)。',
        variant: 'destructive',
      });
      setAdminEditing(true);
      return;
    }
    navigate('/projects/new');
  };

  const submitAdmin = () => {
    const v = adminDraft.trim();
    if (!v) return;
    setAdminToken(v);
    setAdminDraft('');
    setAdminEditing(false);
  };

  return (
    <Shell>
      <header className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-muted-foreground">
            Visualize API specs as interactive test-case brain maps.
          </p>
        </div>
        <Button onClick={handleNewProject} aria-label="Create new project">
          <Plus className="h-4 w-4" /> New Project
        </Button>
      </header>

      <Card className="mb-4">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base">
            {adminToken ? (
              <ShieldCheck className="h-4 w-4 text-status-passed" aria-hidden="true" />
            ) : (
              <KeyRound className="h-4 w-4" aria-hidden="true" />
            )}
            Admin token
          </CardTitle>
          <CardDescription>
            {adminToken
              ? '已配置。仅用于列出与创建项目。不会随项目请求一起发送。'
              : '需要服务器管理员令牌 (CASEMAP_SERVER_ADMIN_TOKEN) 才能列出与创建项目。'}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {adminToken && !adminEditing ? (
            <div className="flex items-center gap-2">
              <code className="rounded bg-muted px-2 py-1 font-mono text-xs">
                ••••••••••••••••
              </code>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setAdminEditing(true)}
                aria-label="Replace admin token"
              >
                替换
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setAdminToken(null)}
                aria-label="Clear admin token"
              >
                清除
              </Button>
            </div>
          ) : (
            <form
              className="flex items-end gap-2"
              onSubmit={(e) => {
                e.preventDefault();
                submitAdmin();
              }}
            >
              <div className="flex-1 space-y-1.5">
                <Label htmlFor="admin-token" className="sr-only">
                  Admin token
                </Label>
                <Input
                  id="admin-token"
                  type="password"
                  autoComplete="off"
                  placeholder="粘贴管理员令牌"
                  value={adminDraft}
                  onChange={(e) => setAdminDraft(e.target.value)}
                />
              </div>
              <Button type="submit" disabled={!adminDraft.trim()}>
                保存
              </Button>
              {adminToken && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => {
                    setAdminEditing(false);
                    setAdminDraft('');
                  }}
                >
                  取消
                </Button>
              )}
            </form>
          )}
        </CardContent>
      </Card>

      <ErrorBoundary>
        {!token && !adminToken ? (
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
                Listing all projects needs the server's admin token. Configure it above,
                then refresh.
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
              <Button onClick={handleNewProject}>
                <Plus className="h-4 w-4" /> New Project
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
