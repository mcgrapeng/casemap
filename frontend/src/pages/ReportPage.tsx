import { useParams } from 'react-router-dom';
import { Printer, Download, Loader2 } from 'lucide-react';
import { Shell } from '@/components/layout/Shell';
import { Sidebar } from '@/components/layout/Sidebar';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { useProject } from '@/hooks/useProjects';
import { useSpecs } from '@/hooks/useGraph';
import { useAuth } from '@/components/providers/ApiProvider';
import { useToast } from '@/hooks/useToast';

export default function ReportPage() {
  const { id = '' } = useParams<{ id: string }>();
  const project = useProject(id);
  const specs = useSpecs(id);
  const { token } = useAuth();
  const { toast } = useToast();
  const latestSpec = specs.data?.[0];

  const reportUrl = latestSpec
    ? `/api/v1/projects/${id}/graphs/${latestSpec.graph_id ?? latestSpec.id}/report`
    : null;
  const fullUrl = reportUrl && token ? `${reportUrl}?_t=${encodeURIComponent(token.slice(0, 12))}` : reportUrl;

  const downloadMarkdown = async () => {
    if (!latestSpec) return;
    try {
      const res = await fetch(`/api/v1/projects/${id}/graphs/${latestSpec.graph_id ?? latestSpec.id}/report`, {
        headers: { Authorization: `Bearer ${token ?? ''}` },
      });
      const html = await res.text();
      // ponytail: very lightweight HTML→MD; good enough for "download markdown" stub.
      const md = html
        .replace(/<style[\s\S]*?<\/style>/gi, '')
        .replace(/<script[\s\S]*?<\/script>/gi, '')
        .replace(/<h1[^>]*>(.*?)<\/h1>/gi, '\n# $1\n')
        .replace(/<h2[^>]*>(.*?)<\/h2>/gi, '\n## $1\n')
        .replace(/<h3[^>]*>(.*?)<\/h3>/gi, '\n### $1\n')
        .replace(/<li[^>]*>(.*?)<\/li>/gi, '- $1\n')
        .replace(/<p[^>]*>(.*?)<\/p>/gi, '$1\n\n')
        .replace(/<[^>]+>/g, '')
        .replace(/\n{3,}/g, '\n\n');
      const blob = new Blob([md], { type: 'text/markdown' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `casemap-report-${id}.md`;
      a.click();
      URL.revokeObjectURL(a.href);
    } catch (e) {
      toast({ title: 'Download failed', description: e instanceof Error ? e.message : '', variant: 'destructive' });
    }
  };

  return (
    <Shell projectName={project.data?.name} sidebar={<Sidebar projectId={id} />}>
      <header className="mb-3 flex flex-wrap items-center gap-2 no-print">
        <h1 className="text-xl font-semibold tracking-tight">Report</h1>
        <Button variant="outline" size="sm" onClick={() => window.print()}>
          <Printer className="h-4 w-4" /> Print
        </Button>
        <Button variant="outline" size="sm" onClick={downloadMarkdown} disabled={!latestSpec}>
          <Download className="h-4 w-4" /> Download as Markdown
        </Button>
      </header>

      {!reportUrl ? (
        <Card>
          <CardContent className="flex h-48 items-center justify-center text-sm text-muted-foreground">
            {specs.isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
              </>
            ) : (
              'Upload a spec to generate a report.'
            )}
          </CardContent>
        </Card>
      ) : (
        <iframe
          title="casemap report"
          src={fullUrl ?? reportUrl}
          className="h-[70vh] w-full rounded-md border bg-card"
        />
      )}
    </Shell>
  );
}
