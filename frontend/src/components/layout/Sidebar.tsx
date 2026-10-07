import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  ListChecks,
  BarChart3,
  FileText,
  Plus,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  end?: boolean;
}

interface SidebarProps {
  projectId: string;
}

export function Sidebar({ projectId }: SidebarProps) {
  const items: NavItem[] = [
    { to: `/projects/${projectId}`, label: '脑图', icon: LayoutDashboard, end: true },
    { to: `/projects/${projectId}/cases`, label: '用例', icon: ListChecks },
    { to: `/projects/${projectId}/progress`, label: '进度', icon: BarChart3 },
    { to: `/projects/${projectId}/report`, label: '报告', icon: FileText },
    { to: '/projects/new', label: '新建项目', icon: Plus },
  ];

  return (
    <nav
      aria-label="Project navigation"
      className="flex w-full shrink-0 flex-row gap-1 overflow-x-auto border-b bg-card p-2 md:w-44 md:flex-col md:gap-0 md:overflow-visible md:border-b-0 md:border-r md:p-3"
    >
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) =>
            cn(
              'flex shrink-0 items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              'hover:bg-accent hover:text-accent-foreground',
              'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
              isActive && 'bg-accent text-accent-foreground',
            )
          }
        >
          <item.icon className="h-4 w-4" aria-hidden="true" />
          <span>{item.label}</span>
        </NavLink>
      ))}
    </nav>
  );
}
