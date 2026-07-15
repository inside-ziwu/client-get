import type { ReactNode } from 'react';
import { cn } from '../lib/utils';

export interface ListPageProps {
  title: string;
  description?: string;
  primaryAction?: ReactNode;
  filters?: ReactNode;
  selectionToolbar?: ReactNode;
  children: ReactNode;
  pagination?: ReactNode;
  className?: string;
}

export function ListPage({
  title,
  description,
  primaryAction,
  filters,
  selectionToolbar,
  children,
  pagination,
  className,
}: ListPageProps) {
  return (
    <div className={cn('flex flex-col gap-ui-lg text-ui-foreground', className)}>
      <header className="flex flex-col gap-ui-sm sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <h1 className="text-ui-page-title">{title}</h1>
          {description ? (
            <p className="mt-ui-xxs text-ui-body text-ui-muted-foreground">{description}</p>
          ) : null}
        </div>
        {primaryAction ? <div className="shrink-0 sm:pt-0.5">{primaryAction}</div> : null}
      </header>
      {filters}
      {selectionToolbar ? (
        <div className="animate-in fade-in slide-in-from-top-1 duration-150">{selectionToolbar}</div>
      ) : null}
      {children}
      {pagination}
    </div>
  );
}
