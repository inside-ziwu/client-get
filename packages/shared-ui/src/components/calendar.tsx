'use client';

import * as React from 'react';
import { DayPicker } from 'react-day-picker';
import { cn } from '../lib/utils';

export type CalendarProps = React.ComponentProps<typeof DayPicker>;

export function Calendar({ className, classNames, showOutsideDays = true, ...props }: CalendarProps) {
  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn('rounded-md border bg-card p-3 shadow-sm', className)}
      classNames={{
        months: 'flex flex-col gap-4',
        month: 'space-y-3',
        caption: 'flex justify-center pt-1 text-sm font-medium',
        nav: 'flex items-center gap-1',
        nav_button: 'h-7 w-7 rounded-md border border-input bg-background text-sm hover:bg-muted',
        nav_button_previous: 'absolute left-4',
        nav_button_next: 'absolute right-4',
        table: 'w-full border-collapse space-y-1',
        head_row: 'flex',
        head_cell: 'w-9 rounded-md text-xs font-normal text-muted-foreground',
        row: 'mt-2 flex w-full',
        cell: 'h-9 w-9 p-0 text-center text-sm',
        day: 'h-9 w-9 rounded-md p-0 text-sm hover:bg-muted focus:outline-none focus:ring-2 focus:ring-ring',
        day_selected: 'bg-primary text-primary-foreground hover:bg-primary hover:text-primary-foreground',
        day_today: 'bg-accent text-accent-foreground',
        day_outside: 'text-muted-foreground opacity-50',
        day_disabled: 'text-muted-foreground opacity-50',
        day_range_middle: 'bg-accent text-accent-foreground',
        day_hidden: 'invisible',
        ...classNames,
      }}
      {...props}
    />
  );
}
