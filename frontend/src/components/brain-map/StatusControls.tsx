import * as React from 'react';
import { Check, X, Ban, SkipForward, Pause } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { CaseStatus } from '@/lib/types';

interface StatusControlsProps {
  value: CaseStatus;
  onChange: (next: CaseStatus) => void;
  disabled?: boolean;
  className?: string;
}

const BUTTONS: Array<{
  status: CaseStatus;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  activeClass: string;
}> = [
  {
    status: 'passed',
    label: '通过',
    icon: Check,
    activeClass: 'bg-status-passed text-white hover:bg-status-passed/90',
  },
  {
    status: 'failed',
    label: '失败',
    icon: X,
    activeClass: 'bg-status-failed text-white hover:bg-status-failed/90',
  },
  {
    status: 'blocked',
    label: '阻塞',
    icon: Ban,
    activeClass: 'bg-status-blocked text-white hover:bg-status-blocked/90',
  },
  {
    status: 'skipped',
    label: '跳过',
    icon: SkipForward,
    activeClass: 'bg-status-skipped text-white hover:bg-status-skipped/90',
  },
  {
    status: 'pending',
    label: '待测',
    icon: Pause,
    activeClass: 'bg-status-pending text-white hover:bg-status-pending/90',
  },
];

export function StatusControls({ value, onChange, disabled, className }: StatusControlsProps) {
  return (
    <div
      role="group"
      aria-label="Test status"
      className={cn('flex flex-wrap gap-2', className)}
    >
      {BUTTONS.map((b) => {
        const Icon = b.icon;
        const active = value === b.status;
        return (
          <Button
            key={b.status}
            type="button"
            variant={active ? 'default' : 'outline'}
            size="sm"
            disabled={disabled}
            onClick={() => onChange(b.status)}
            aria-pressed={active}
            aria-label={`Mark as ${b.label}`}
            className={cn(active && b.activeClass)}
          >
            <Icon className="h-4 w-4" />
            <span>{b.label}</span>
          </Button>
        );
      })}
    </div>
  );
}
