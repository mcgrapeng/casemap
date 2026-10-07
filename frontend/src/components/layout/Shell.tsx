import * as React from 'react';
import { Header } from './Header';
import { cn } from '@/lib/utils';

interface ShellProps {
  children: React.ReactNode;
  projectName?: string;
  serverOnline?: boolean;
  sidebar?: React.ReactNode;
  className?: string;
}

export function Shell({
  children,
  projectName,
  serverOnline = true,
  sidebar,
  className,
}: ShellProps) {
  return (
    <div className="flex h-full min-h-screen flex-col">
      <Header serverOnline={serverOnline} projectName={projectName} />
      <div className={cn('flex flex-1 flex-col md:flex-row', className)}>
        {sidebar}
        <main className="flex-1 overflow-x-hidden p-4 md:p-6">{children}</main>
      </div>
    </div>
  );
}
