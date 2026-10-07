import * as React from 'react';
import { Link, useParams } from 'react-router-dom';
import { Upload, Loader2, Search, FileText } from 'lucide-react';
import { Shell } from '@/components/layout/Shell';
import { Sidebar } from '@/components/layout/Sidebar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { BrainMap } from '@/components/brain-map/BrainMap';
import { CaseDetail } from '@/components/brain-map/CaseDetail';
import { ProgressBar } from '@/components/brain-map/ProgressBar';
import { EmptyState } from '@/components/shared/EmptyState';
import { useProject } from '@/hooks/useProjects';
import { useCases } from '@/hooks/useCases';
import { useProgress } from '@/hooks/useProgress';
import { useSpecs, useGraph } from '@/hooks/useGraph';
import { useStatusStream } from '@/hooks/useStatusStream';
import { useToast } from '@/hooks/useToast';
import { api } from '@/lib/api';
import { useAuth } from '@/components/providers/ApiProvider';

export default function ProjectPage() {
  const { id = '' } = useParams<{ id: string }>();
  const { token } = useAuth();
  const project = useProject(id);
  const specs = useSpecs(id);
  const cases = useCases(id);
  const progress = useProgress(id);
  // ponytail: useStatusStream is a no-op when token is undefined (the hook
  // guards). Mounting it once here keeps one WebSocket per project page.
  useStatusStream(id, token ?? undefined);

  const latestSpec = specs.data?.[0];
  const graph = useGraph(id, latestSpec?.id);
  const { toast } = useToast();

  const [selectedCaseId, setSelectedCaseId] = React.useState<string | null>(null);
  const [typeFilter, setTypeFilter] = React.useState('all');
  const [search, setSearch] = React.useState('');
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const selectedCase = React.useMemo(
    () => cases.data?.find((c) => c.id === selectedCaseId) ?? null,
    [cases.data, selectedCaseId],
  );

  const onUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      await api.uploadSpec(id, file);
      toast({ title: 'Spec uploaded', description: 'Generating brain map…' });
      specs.refetch();
      cases.refetch();
    } catch (err) {
      toast({
        title: 'Upload failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const exportStatus = async () => {
    try {
      const data = await api.bulkExport(id);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `casemap-status-${id}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      toast({
        title: 'Export failed',
        description: err instanceof Error ? err.message : 'Unknown error',
        variant: 'destructive',
      });
    }
  };

  return (
    <Shell projectName={project.data?.name} sidebar={<Sidebar projectId={id} />}>
      <div className="flex flex-col gap-4 lg:flex-row">
        <section className="min-w-0 flex-1 space-y-4">
          <header className="flex flex-wrap items-center gap-2">
            <h1 className="text-xl font-semibold tracking-tight">
              {project.data?.name ?? 'Loading…'}
            </h1>
            <Button asChild variant="outline" size="sm">
              <Link to={`/projects/${id}/report`}>
                <FileText className="h-4 w-4" /> View Report
              </Link>
            </Button>
            <div className="ml-auto flex flex-wrap items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".json,.yaml,.yml,application/json"
                className="sr-only"
                onChange={onUpload}
                aria-label="Upload spec"
              />
              <Button
                size="sm"
                variant="outline"
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload className="h-4 w-4" /> Upload Spec
              </Button>
              <Button size="sm" variant="outline" onClick={exportStatus}>
                Export Status
              </Button>
            </div>
          </header>

          {progress.data && (
            <ProgressBar
              total={progress.data.total}
              passed={progress.data.passed}
              failed={progress.data.failed}
              pending={progress.data.pending}
              in_progress={progress.data.in_progress}
              blocked={progress.data.blocked}
              skipped={progress.data.skipped}
            />
          )}

          <Card>
            <CardContent className="space-y-3 p-3">
              <div className="flex flex-wrap items-center gap-2">
                <div className="relative min-w-[180px] flex-1">
                  <Search
                    className="pointer-events-none absolute left-2 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
                    aria-hidden="true"
                  />
                  <Input
                    placeholder="Search cases…"
                    value={search}
                    onChange={(e) => setSearch(e.target.value)}
                    className="pl-8"
                    aria-label="Search cases"
                  />
                </div>
                <Select value={typeFilter} onValueChange={setTypeFilter}>
                  <SelectTrigger className="w-36" aria-label="Filter by case type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All types</SelectItem>
                    <SelectItem value="positive">正向</SelectItem>
                    <SelectItem value="negative">逆向</SelectItem>
                    <SelectItem value="edge">边界</SelectItem>
                    <SelectItem value="security">安全</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {!token && (
                <EmptyState
                  title="Sign in to view this project"
                  description="Set your project API key from the home page."
                />
              )}

              {token && specs.isLoading && (
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 animate-spin" /> Loading specs…
                </div>
              )}

              {token && specs.data && specs.data.length === 0 && (
                <EmptyState
                  title="No specs uploaded yet"
                  description="Upload an OpenAPI / Postman / Apifox JSON to generate your brain map."
                  action={
                    <Button onClick={() => fileInputRef.current?.click()}>
                      <Upload className="h-4 w-4" /> Upload Spec
                    </Button>
                  }
                />
              )}

              {graph.data && graph.data.graph.nodes.length > 0 && (
                <BrainMap
                  data={graph.data}
                  typeFilter={typeFilter}
                  search={search}
                  selectedId={selectedCaseId}
                  onSelect={setSelectedCaseId}
                />
              )}

              {graph.isLoading && (
                <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading brain map…
                </div>
              )}
            </CardContent>
          </Card>
        </section>

        {selectedCase && (
          <CaseDetail projectId={id} caseData={selectedCase} onClose={() => setSelectedCaseId(null)} />
        )}
      </div>
    </Shell>
  );
}
