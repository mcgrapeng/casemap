import { cn } from '@/lib/utils';

const TYPE_LABEL: Record<string, string> = {
  positive: '正向',
  negative: '逆向',
  edge: '边界',
  security: '安全',
};

const TYPE_CLASS: Record<string, string> = {
  positive: 'bg-case-positive/15 text-case-positive border-case-positive/40',
  negative: 'bg-case-negative/15 text-case-negative border-case-negative/40',
  edge: 'bg-case-edge/15 text-case-edge border-case-edge/40',
  security: 'bg-case-security/15 text-case-security border-case-security/40',
};

export function TypeBadge({ type, className }: { type: string; className?: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide',
        TYPE_CLASS[type] ?? 'border-border text-muted-foreground',
        className,
      )}
      aria-label={`Type: ${TYPE_LABEL[type] ?? type}`}
    >
      {TYPE_LABEL[type] ?? type}
    </span>
  );
}
