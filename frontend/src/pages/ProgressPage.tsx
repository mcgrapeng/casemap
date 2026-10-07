import * as React from 'react';
import { useParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { Shell } from '@/components/layout/Shell';
import { Sidebar } from '@/components/layout/Sidebar';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { useCases } from '@/hooks/useCases';
import { useProgress } from '@/hooks/useProgress';
import { useProject } from '@/hooks/useProjects';
import { cn, formatPercent } from '@/lib/utils';
import type { CaseStatus, CaseRecord } from '@/lib/types';

const PALETTE: Record<CaseStatus, string> = {
  pending: 'bg-status-pending',
  in_progress: 'bg-status-in-progress',
  passed: 'bg-status-passed',
  failed: 'bg-status-failed',
  blocked: 'bg-status-blocked',
  skipped: 'bg-status-skipped',
};

export default function ProgressPage() {
  const { id = '' } = useParams<{ id: string }>();
  const project = useProject(id);
  const progress = useProgress(id);
  const cases = useCases(id);

  const stats = progress.data;
  const allCases = React.useMemo(() => cases.data ?? [], [cases.data]);

  const tagStats = React.useMemo(() => {
    const map = new Map<string, { total: number; passed: number }>();
    for (const c of allCases) {
      const tags = c.tags.length ? c.tags : ['(untagged)'];
      for (const t of tags) {
        const entry = map.get(t) ?? { total: 0, passed: 0 };
        entry.total += 1;
        if (c.status === 'passed') entry.passed += 1;
        map.set(t, entry);
      }
    }
    return [...map.entries()].sort((a, b) => b[1].total - a[1].total).slice(0, 12);
  }, [allCases]);

  const failedCases: CaseRecord[] = React.useMemo(
    () => allCases.filter((c) => c.status === 'failed'),
    [allCases],
  );

  const donut = React.useMemo(() => {
    if (!stats) return null;
    const total = stats.total || 1;
    const order: CaseStatus[] = ['passed', 'failed', 'in_progress', 'pending', 'blocked', 'skipped'];
    let offset = 0;
    const segs = order
      .map((s) => ({ status: s, value: stats[s] }))
      .filter((s) => s.value > 0)
      .map((s) => {
        const pct = s.value / total;
        const dash = `${pct * 100} ${100 - pct * 100}`;
        const seg = { ...s, dash, offset };
        offset += pct * 100;
        return seg;
      });
    return segs;
  }, [stats]);

  return (
    <Shell projectName={project.data?.name} sidebar={<Sidebar projectId={id} />}>
      <h1 className="mb-3 text-xl font-semibold tracking-tight">Progress</h1>

      {!stats ? (
        <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
          <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
        </div>
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {(
            [
              ['✅', 'Passed', stats.passed],
              ['❌', 'Failed', stats.failed],
              ['🔄', 'In progress', stats.in_progress],
              ['⏸', 'Pending', stats.pending],
              ['🚫', 'Blocked', stats.blocked],
              ['⏭', 'Skipped', stats.skipped],
            ] as Array<[string, string, number]>
          ).map(([emoji, label, value]) => (
            <Card key={label}>
              <CardHeader className="pb-2">
                <CardDescription>{label}</CardDescription>
                <CardTitle className="text-3xl">
                  {emoji} {value}
                </CardTitle>
              </CardHeader>
            </Card>
          ))}

          <Card className="md:col-span-1">
            <CardHeader>
              <CardTitle>Status mix</CardTitle>
              <CardDescription>{formatPercent(stats.completion_pct)} complete</CardDescription>
            </CardHeader>
            <CardContent>
              {donut && donut.length > 0 ? (
                <div className="flex items-center gap-4">
                  <svg viewBox="0 0 36 36" className="h-32 w-32 -rotate-90">
                    <circle
                      cx="18"
                      cy="18"
                      r="15.9155"
                      fill="transparent"
                      stroke="currentColor"
                      strokeWidth="6"
                      className="text-muted/30"
                    />
                    {donut.map((s) => (
                      <circle
                        key={s.status}
                        cx="18"
                        cy="18"
                        r="15.9155"
                        fill="transparent"
                        strokeWidth="6"
                        strokeDasharray={s.dash}
                        strokeDashoffset={-s.offset}
                        className={cn(PALETTE[s.status])}
                      />
                    ))}
                  </svg>
                  <ul className="space-y-1 text-xs">
                    {donut.map((s) => (
                      <li key={s.status} className="flex items-center gap-2">
                        <span className={cn('inline-block h-2 w-2 rounded-full', PALETTE[s.status])} aria-hidden="true" />
                        <StatusBadge status={s.status} />
                        <span className="tabular-nums text-muted-foreground">{s.value}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">No data yet.</p>
              )}
            </CardContent>
          </Card>

          <Card className="md:col-span-2">
            <CardHeader>
              <CardTitle>Per-tag progress</CardTitle>
              <CardDescription>Top {tagStats.length} tags</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {tagStats.length === 0 ? (
                <p className="text-sm text-muted-foreground">No tagged cases yet.</p>
              ) : (
                tagStats.map(([tag, s]) => {
                  const pct = s.total === 0 ? 0 : Math.round((s.passed / s.total) * 100);
                  return (
                    <div key={tag}>
                      <div className="mb-1 flex items-center justify-between text-xs">
                        <span className="font-medium">{tag}</span>
                        <span className="tabular-nums text-muted-foreground">
                          {s.passed}/{s.total} · {pct}%
                        </span>
                      </div>
                      <Progress value={pct} aria-label={`${tag} progress`} />
                    </div>
                  );
                })
              )}
            </CardContent>
          </Card>

          {failedCases.length > 0 && (
            <Card className="md:col-span-3">
              <CardHeader>
                <CardTitle>Failed cases ({failedCases.length})</CardTitle>
                <CardDescription>Latest failures with their notes</CardDescription>
              </CardHeader>
              <CardContent className="space-y-2">
                {failedCases.map((c) => (
                  <div key={c.id} className="rounded-md border p-2">
                    <div className="flex items-center gap-2">
                      <StatusBadge status={c.status} />
                      <span className="font-medium">{c.title}</span>
                    </div>
                    {c.note && (
                      <p className="mt-1 text-xs text-muted-foreground">{c.note}</p>
                    )}
                  </div>
                ))}
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </Shell>
  );
}
