import * as React from 'react';
import { CaseNode } from './CaseNode';
import { Legend } from './Legend';
import { cn } from '@/lib/utils';
import type { GraphData } from '@/lib/types';

interface BrainMapProps {
  data: GraphData;
  typeFilter?: string;
  search?: string;
  selectedId?: string | null;
  onSelect?: (caseId: string) => void;
  className?: string;
}

const PADDING = 40;

export function BrainMap({
  data,
  typeFilter = 'all',
  search = '',
  selectedId,
  onSelect,
  className,
}: BrainMapProps) {
  const containerRef = React.useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = React.useState(1);
  const [pan, setPan] = React.useState({ x: 0, y: 0 });
  const [dragging, setDragging] = React.useState<{ x: number; y: number } | null>(null);

  const filteredNodes = React.useMemo(() => {
    const term = search.trim().toLowerCase();
    return data.graph.nodes.filter((n) => {
      if (typeFilter !== 'all' && n.type !== typeFilter) return false;
      if (term && !n.title.toLowerCase().includes(term)) return false;
      return true;
    });
  }, [data.graph.nodes, typeFilter, search]);

  const visibleIds = React.useMemo(
    () => new Set(filteredNodes.map((n) => n.id)),
    [filteredNodes],
  );

  const width = data.graph.width ?? 1200;
  const height = data.graph.height ?? 800;
  const minX = -PADDING;
  const minY = -PADDING;
  const viewW = width + PADDING * 2;
  const viewH = height + PADDING * 2;

  const onWheel = (e: React.WheelEvent) => {
    if (!e.ctrlKey && !e.metaKey) return;
    e.preventDefault();
    const delta = -e.deltaY * 0.001;
    setZoom((z) => Math.min(3, Math.max(0.3, z + delta)));
  };

  const onMouseDown = (e: React.MouseEvent) => {
    if ((e.target as SVGElement).closest('[data-node]')) return;
    setDragging({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const onMouseMove = (e: React.MouseEvent) => {
    if (!dragging) return;
    setPan({ x: e.clientX - dragging.x, y: e.clientY - dragging.y });
  };

  const onMouseUp = () => setDragging(null);

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <Legend />
      <div
        ref={containerRef}
        role="application"
        aria-label="Test case brain map. Use Ctrl+wheel to zoom; drag empty space to pan."
        tabIndex={0}
        onWheel={onWheel}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        className="relative h-[480px] w-full overflow-hidden rounded-md border bg-background focus:outline-none focus-visible:ring-2 focus-visible:ring-ring md:h-[640px]"
      >
        <svg
          width="100%"
          height="100%"
          viewBox={`${minX} ${minY} ${viewW} ${viewH}`}
          preserveAspectRatio="xMidYMid meet"
          className="cursor-grab active:cursor-grabbing"
          data-testid="brain-map-svg"
        >
          <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>
            {/* edges */}
            {data.graph.edges
              .filter((e) => visibleIds.has(e.from) && visibleIds.has(e.to))
              .map((e, i) => {
                const a = data.graph.nodes.find((n) => n.id === e.from);
                const b = data.graph.nodes.find((n) => n.id === e.to);
                if (!a || !b || a.x == null || b.x == null) return null;
                const ax = a.x + (a.width ?? 0);
                const ay = (a.y ?? 0) + (a.height ?? 0) / 2;
                const bx = b.x;
                const by = (b.y ?? 0) + (b.height ?? 0) / 2;
                return (
                  <path
                    key={i}
                    d={`M ${ax} ${ay} C ${ax + 40} ${ay}, ${bx - 40} ${by}, ${bx} ${by}`}
                    className="fill-none stroke-border"
                    strokeWidth={1}
                  />
                );
              })}
            {/* nodes */}
            {filteredNodes.map((n) => {
              const status = data.statuses[n.id]?.status ?? 'pending';
              return (
                <g key={n.id} data-node="true">
                  <CaseNode
                    node={n}
                    status={status}
                    selected={selectedId === n.id}
                    highlighted={!!search.trim()}
                    onClick={() => onSelect?.(n.id)}
                  />
                </g>
              );
            })}
          </g>
        </svg>

        <div className="absolute bottom-2 right-2 flex items-center gap-1 rounded-md border bg-card/90 p-1 text-xs shadow-sm">
          <button
            type="button"
            aria-label="Zoom out"
            className="rounded px-2 py-1 hover:bg-accent"
            onClick={() => setZoom((z) => Math.max(0.3, z - 0.1))}
          >
            −
          </button>
          <span className="min-w-[3ch] text-center tabular-nums">{Math.round(zoom * 100)}%</span>
          <button
            type="button"
            aria-label="Zoom in"
            className="rounded px-2 py-1 hover:bg-accent"
            onClick={() => setZoom((z) => Math.min(3, z + 0.1))}
          >
            +
          </button>
          <button
            type="button"
            aria-label="Reset view"
            className="rounded px-2 py-1 hover:bg-accent"
            onClick={() => {
              setZoom(1);
              setPan({ x: 0, y: 0 });
            }}
          >
            ⟲
          </button>
        </div>
      </div>
    </div>
  );
}
