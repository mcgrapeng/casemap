import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/utils';

interface ProgressBarProps {
  total: number;
  passed: number;
  failed: number;
  pending: number;
  in_progress?: number;
  blocked?: number;
  skipped?: number;
  showLabel?: boolean;
  className?: string;
}

export function ProgressBar({
  total,
  passed,
  failed,
  pending,
  in_progress = 0,
  blocked = 0,
  skipped = 0,
  showLabel = true,
  className,
}: ProgressBarProps) {
  const pct = total === 0 ? 0 : Math.round((passed / total) * 100);
  return (
    <div className={cn('w-full', className)} role="region" aria-label="Test progress">
      <div className="mb-1 flex items-center justify-between text-xs">
        <span className="text-muted-foreground">进度</span>
        {showLabel && (
          <span className="font-medium tabular-nums" aria-live="polite">
            {passed}/{total} ({pct}%)
          </span>
        )}
      </div>
      <Progress value={pct} aria-valuenow={pct} aria-valuemin={0} aria-valuemax={100} />
      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        <span>✅ {passed}</span>
        <span>❌ {failed}</span>
        <span>🔄 {in_progress}</span>
        <span>⏸ {pending}</span>
        <span>🚫 {blocked}</span>
        <span>⏭ {skipped}</span>
      </div>
    </div>
  );
}
