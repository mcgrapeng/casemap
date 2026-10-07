import { cn } from '@/lib/utils';
import type { CaseStatus, GraphNode } from '@/lib/types';

interface CaseNodeProps {
  node: GraphNode;
  status: CaseStatus;
  selected?: boolean;
  highlighted?: boolean;
  onClick?: () => void;
}

const STATUS_STROKE: Record<CaseStatus, string> = {
  pending: 'stroke-status-pending',
  in_progress: 'stroke-status-in-progress',
  passed: 'stroke-status-passed',
  failed: 'stroke-status-failed',
  blocked: 'stroke-status-blocked',
  skipped: 'stroke-status-skipped',
};

const TYPE_FILL: Record<string, string> = {
  positive: 'fill-case-positive/15',
  negative: 'fill-case-negative/15',
  edge: 'fill-case-edge/15',
  security: 'fill-case-security/15',
};

export function CaseNode({ node, status, selected, highlighted, onClick }: CaseNodeProps) {
  const x = node.x ?? 0;
  const y = node.y ?? 0;
  const w = node.width ?? 160;
  const h = node.height ?? 48;

  return (
    <g
      tabIndex={0}
      role="button"
      aria-label={`${node.title} — ${status}`}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick?.();
        }
      }}
      className="cursor-pointer focus:outline-none"
    >
      <title>{node.title}</title>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        rx={8}
        className={cn(
          TYPE_FILL[node.type] ?? 'fill-muted',
          STATUS_STROKE[status],
          selected ? 'stroke-2' : 'stroke-1',
          highlighted ? 'opacity-100' : '',
        )}
        strokeWidth={selected ? 2.5 : 1.5}
      />
      <text
        x={x + 10}
        y={y + h / 2 + 4}
        className="pointer-events-none fill-foreground text-[11px] font-medium"
      >
        {node.title.length > 22 ? `${node.title.slice(0, 21)}…` : node.title}
      </text>
      {highlighted && (
        <rect
          x={x - 2}
          y={y - 2}
          width={w + 4}
          height={h + 4}
          rx={10}
          className="fill-none stroke-primary"
          strokeWidth={1}
          strokeDasharray="3 3"
        />
      )}
    </g>
  );
}
