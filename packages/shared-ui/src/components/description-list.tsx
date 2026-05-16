import * as React from 'react';
import { cn } from '../lib/utils';

export function DescriptionList({
  items,
  className,
}: {
  items: Array<{ label: string; value: React.ReactNode }>;
  className?: string;
}) {
  return (
    <dl className={cn('grid gap-3 text-sm sm:grid-cols-2', className)}>
      {items.map((item) => (
        <div key={item.label} className="min-w-0 rounded-md border border-border p-3">
          <dt className="text-xs text-muted-foreground">{item.label}</dt>
          <dd className="mt-1 min-w-0 break-words font-medium">{item.value || '-'}</dd>
        </div>
      ))}
    </dl>
  );
}
