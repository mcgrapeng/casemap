import * as React from 'react';
import { useParams } from 'react-router-dom';
import { Loader2 } from 'lucide-react';
import { Shell } from '@/components/layout/Shell';
import { Sidebar } from '@/components/layout/Sidebar';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Card, CardContent } from '@/components/ui/card';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { CaseDetail } from '@/components/brain-map/CaseDetail';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { TypeBadge } from '@/components/shared/TypeBadge';
import { useCases } from '@/hooks/useCases';
import { useProject } from '@/hooks/useProjects';
import { formatDate, truncate } from '@/lib/utils';
import type { CaseRecord, CaseStatus } from '@/lib/types';

const STATUSES: CaseStatus[] = ['pending', 'in_progress', 'passed', 'failed', 'blocked', 'skipped'];
type SortKey = 'id' | 'type' | 'title' | 'endpoint_ref' | 'status' | 'updated_at';

export default function CasesPage() {
  const { id = '' } = useParams<{ id: string }>();
  const project = useProject(id);
  const cases = useCases(id);
  const [search, setSearch] = React.useState('');
  const [statusFilter, setStatusFilter] = React.useState<'all' | CaseStatus>('all');
  const [typeFilter, setTypeFilter] = React.useState<'all' | string>('all');
  const [sortKey, setSortKey] = React.useState<SortKey>('updated_at');
  const [sortDir, setSortDir] = React.useState<'asc' | 'desc'>('desc');
  const [selected, setSelected] = React.useState<CaseRecord | null>(null);

  const rows = React.useMemo(() => {
    const term = search.trim().toLowerCase();
    const filtered = (cases.data ?? []).filter((c) => {
      if (statusFilter !== 'all' && c.status !== statusFilter) return false;
      if (typeFilter !== 'all' && c.type !== typeFilter) return false;
      if (term && !`${c.title} ${c.endpoint_ref ?? ''} ${c.id}`.toLowerCase().includes(term))
        return false;
      return true;
    });
    return [...filtered].sort((a, b) => {
      const av = (a[sortKey] ?? '') as string;
      const bv = (b[sortKey] ?? '') as string;
      return sortDir === 'asc' ? av.localeCompare(bv) : bv.localeCompare(av);
    });
  }, [cases.data, search, statusFilter, typeFilter, sortKey, sortDir]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  return (
    <Shell projectName={project.data?.name} sidebar={<Sidebar projectId={id} />}>
      <h1 className="mb-3 text-xl font-semibold tracking-tight">Cases</h1>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <Input
          placeholder="Search by title / endpoint / id"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
          aria-label="Search cases"
        />
        <Select value={statusFilter} onValueChange={(v) => setStatusFilter(v as 'all' | CaseStatus)}>
          <SelectTrigger className="w-32" aria-label="Filter by status">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All status</SelectItem>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={typeFilter} onValueChange={(v) => setTypeFilter(v as string)}>
          <SelectTrigger className="w-32" aria-label="Filter by type">
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
        <span className="ml-auto text-xs text-muted-foreground">
          {rows.length} case{rows.length === 1 ? '' : 's'}
        </span>
      </div>

      <Card>
        <CardContent className="p-0">
          {cases.isLoading ? (
            <div className="flex h-32 items-center justify-center text-sm text-muted-foreground">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Loading…
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/50 text-left text-xs uppercase text-muted-foreground">
                    {(
                      [
                        ['id', 'ID'],
                        ['type', 'Type'],
                        ['title', 'Title'],
                        ['endpoint_ref', 'Endpoint'],
                        ['status', 'Status'],
                        ['updated_at', 'Updated'],
                      ] as Array<[SortKey, string]>
                    ).map(([key, label]) => (
                      <th key={key} className="px-3 py-2 font-medium">
                        <button
                          type="button"
                          onClick={() => toggleSort(key)}
                          className="inline-flex items-center gap-1 hover:text-foreground"
                          aria-label={`Sort by ${label}`}
                        >
                          {label}
                          {sortKey === key && (
                            <span aria-hidden="true">{sortDir === 'asc' ? '▲' : '▼'}</span>
                          )}
                        </button>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {rows.map((c) => (
                    <tr
                      key={c.id}
                      tabIndex={0}
                      onClick={() => setSelected(c)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') setSelected(c);
                      }}
                      className="cursor-pointer border-b transition-colors hover:bg-accent/40 focus:bg-accent/40 focus:outline-none"
                    >
                      <td className="px-3 py-2 font-mono text-xs">{truncate(c.id, 12)}</td>
                      <td className="px-3 py-2">
                        <TypeBadge type={c.type} />
                      </td>
                      <td className="px-3 py-2">{truncate(c.title, 80)}</td>
                      <td className="px-3 py-2 font-mono text-xs text-muted-foreground">
                        {c.endpoint_ref ? truncate(c.endpoint_ref, 40) : '—'}
                      </td>
                      <td className="px-3 py-2">
                        <StatusBadge status={c.status} />
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {formatDate(c.updated_at)}
                      </td>
                    </tr>
                  ))}
                  {rows.length === 0 && (
                    <tr>
                      <td colSpan={6} className="px-3 py-10 text-center text-sm text-muted-foreground">
                        No cases match your filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {rows.some((r) => r.tags.length > 0) && (
        <div className="mt-3 flex flex-wrap gap-1">
          {Array.from(new Set(rows.flatMap((r) => r.tags))).map((t) => (
            <Badge key={t} variant="outline" className="text-[10px]">
              {t}
            </Badge>
          ))}
        </div>
      )}

      <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="sr-only">Case detail</DialogTitle>
          </DialogHeader>
          {selected && <CaseDetail projectId={id} caseData={selected} onClose={() => setSelected(null)} />}
        </DialogContent>
      </Dialog>
    </Shell>
  );
}
