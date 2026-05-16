import * as React from 'react';
import { cn } from '../lib/utils';
import { Card, CardContent } from './card';

export function StatCard({
  label,
  value,
  helper,
  icon,
  className,
}: {
  label: string;
  value: React.ReactNode;
  helper?: React.ReactNode;
  icon?: React.ReactNode;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardContent className="flex items-start justify-between gap-4 p-4">
        <div className="min-w-0">
          <div className="text-sm text-muted-foreground">{label}</div>
          <div className="mt-2 truncate text-2xl font-semibold tracking-normal">{value}</div>
          {helper ? <div className="mt-1 text-xs text-muted-foreground">{helper}</div> : null}
        </div>
        {icon ? <div className={cn('rounded-md bg-muted p-2 text-muted-foreground')}>{icon}</div> : null}
      </CardContent>
    </Card>
  );
}
