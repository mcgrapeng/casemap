import * as React from 'react';
import { X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { StatusControls } from './StatusControls';
import { StatusBadge } from '@/components/shared/StatusBadge';
import { TypeBadge } from '@/components/shared/TypeBadge';
import { usePatchStatus } from '@/hooks/useStatus';
import { useToast } from '@/hooks/useToast';
import type { CaseRecord, CaseStatus } from '@/lib/types';

interface CaseDetailProps {
  projectId: string;
  caseData: CaseRecord;
  onClose: () => void;
}

export function CaseDetail({ projectId, caseData, onClose }: CaseDetailProps) {
  const [status, setStatus] = React.useState<CaseStatus>(caseData.status);
  const [note, setNote] = React.useState(caseData.note ?? '');
  const [savedNote, setSavedNote] = React.useState(caseData.note ?? '');
  const patch = usePatchStatus(projectId);
  const { toast } = useToast();

  React.useEffect(() => {
    setStatus(caseData.status);
    setNote(caseData.note ?? '');
    setSavedNote(caseData.note ?? '');
  }, [caseData.id, caseData.status, caseData.note]);

  const dirty = status !== caseData.status || note !== savedNote;

  const save = React.useCallback(async () => {
    try {
      await patch.mutateAsync({
        caseId: caseData.id,
        body: { status, note },
      });
      setSavedNote(note);
      toast({ title: '已保存', description: caseData.title });
    } catch (e) {
      toast({
        title: '保存失败',
        description: e instanceof Error ? e.message : '未知错误',
        variant: 'destructive',
      });
    }
  }, [patch, caseData.id, caseData.title, status, note, toast]);

  return (
    <aside
      aria-label="Case details"
      className="flex h-full w-full flex-col gap-4 border-l bg-card p-4 md:w-[360px]"
    >
      <header className="flex items-start justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <TypeBadge type={caseData.type} />
          <StatusBadge status={status} />
        </div>
        <Button
          variant="ghost"
          size="icon"
          aria-label="Close case detail"
          onClick={onClose}
        >
          <X className="h-4 w-4" />
        </Button>
      </header>

      <div>
        <h2 className="text-lg font-semibold leading-tight">{caseData.title}</h2>
        {caseData.endpoint_ref && (
          <code className="mt-1 inline-block rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
            {caseData.endpoint_ref}
          </code>
        )}
      </div>

      {caseData.description && (
        <p className="text-sm text-muted-foreground">{caseData.description}</p>
      )}

      {caseData.tags.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {caseData.tags.map((t) => (
            <Badge key={t} variant="outline" className="text-[10px]">
              {t}
            </Badge>
          ))}
        </div>
      )}

      {caseData.steps.length > 0 && (
        <section aria-label="Test steps">
          <h3 className="mb-2 text-sm font-medium">步骤</h3>
          <ol className="space-y-1.5 text-sm">
            {caseData.steps.map((s, i) => (
              <li key={i} className="flex gap-2">
                <span className="mt-0.5 inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-muted text-[10px] font-medium">
                  {i + 1}
                </span>
                <span className="flex-1">
                  {typeof s === 'string' ? s : (s.step ?? JSON.stringify(s))}
                  {typeof s === 'object' && s.expected && (
                    <span className="mt-0.5 block text-xs text-muted-foreground">
                      期望: {String(s.expected)}
                    </span>
                  )}
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}

      <section aria-label="Status">
        <h3 className="mb-2 text-sm font-medium">状态</h3>
        <StatusControls value={status} onChange={setStatus} disabled={patch.isPending} />
      </section>

      <section>
        <Label htmlFor="case-note" className="text-sm font-medium">
          备注
        </Label>
        <Textarea
          id="case-note"
          value={note}
          onChange={(e) => setNote(e.target.value)}
          placeholder="测试中遇到的问题 / 备注…"
          className="mt-1.5"
          rows={4}
        />
      </section>

      <div className="mt-auto flex justify-end gap-2 border-t pt-3">
        <Button variant="ghost" size="sm" onClick={onClose}>
          关闭
        </Button>
        <Button size="sm" onClick={save} disabled={!dirty || patch.isPending}>
          {patch.isPending ? '保存中…' : '保存'}
        </Button>
      </div>
    </aside>
  );
}
