import { cn } from '@/lib/utils';
import type { CaseStatus } from '@/lib/types';

const ROWS: Array<{ status: CaseStatus; emoji: string; label: string; bg: string }> = [
  { status: 'pending', emoji: '⏸', label: '待测', bg: 'bg-status-pending' },
  { status: 'in_progress', emoji: '🔄', label: '进行中', bg: 'bg-status-in-progress' },
  { status: 'passed', emoji: '✅', label: '通过', bg: 'bg-status-passed' },
  { status: 'failed', emoji: '❌', label: '失败', bg: 'bg-status-failed' },
  { status: 'blocked', emoji: '🚫', label: '阻塞', bg: 'bg-status-blocked' },
  { status: 'skipped', emoji: '⏭', label: '跳过', bg: 'bg-status-skipped' },
];

const TYPES: Array<{ key: string; label: string; dot: string }> = [
  { key: 'positive', label: '正向', dot: 'bg-case-positive' },
  { key: 'negative', label: '逆向', dot: 'bg-case-negative' },
  { key: 'edge', label: '边界', dot: 'bg-case-edge' },
  { key: 'security', label: '安全', dot: 'bg-case-security' },
];

export function Legend({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'flex flex-wrap items-center gap-x-4 gap-y-2 rounded-md border bg-card/50 p-2 text-xs text-muted-foreground',
        className,
      )}
      aria-label="Legend"
    >
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {ROWS.map((r) => (
          <span key={r.status} className="flex items-center gap-1">
            <span aria-hidden="true">{r.emoji}</span>
            <span>{r.label}</span>
          </span>
        ))}
      </div>
      <span className="hidden h-3 w-px bg-border sm:inline-block" aria-hidden="true" />
      <div className="flex flex-wrap gap-x-3 gap-y-1">
        {TYPES.map((t) => (
          <span key={t.key} className="flex items-center gap-1">
            <span className={cn('inline-block h-2 w-2 rounded-full', t.dot)} aria-hidden="true" />
            <span>{t.label}</span>
          </span>
        ))}
      </div>
    </div>
  );
}
