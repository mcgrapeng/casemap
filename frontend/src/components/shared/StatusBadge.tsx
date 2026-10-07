import { cn } from '@/lib/utils';
import type { CaseStatus } from '@/lib/types';

const STATUS_LABEL: Record<CaseStatus, string> = {
  pending: '⏸ 待测',
  in_progress: '🔄 进行中',
  passed: '✅ 通过',
  failed: '❌ 失败',
  blocked: '🚫 阻塞',
  skipped: '⏭ 跳过',
};

const STATUS_CLASS: Record<CaseStatus, string> = {
  pending: 'bg-status-pending/15 text-status-foreground border-status-pending/30',
  in_progress: 'bg-status-in-progress/15 text-status-in-progress border-status-in-progress/30',
  passed: 'bg-status-passed/15 text-status-passed border-status-passed/30',
  failed: 'bg-status-failed/15 text-status-failed border-status-failed/30',
  blocked: 'bg-status-blocked/15 text-status-blocked border-status-blocked/30',
  skipped: 'bg-status-skipped/15 text-status-skipped border-status-skipped/30',
};

export function StatusBadge({ status, className }: { status: CaseStatus; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium',
        STATUS_CLASS[status],
        className,
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}
