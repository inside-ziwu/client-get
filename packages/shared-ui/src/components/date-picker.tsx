'use client';

import { CalendarIcon, X } from 'lucide-react';
import { useState } from 'react';
import { Button } from './button';
import { Calendar } from './calendar';

function formatDate(date?: Date) {
  if (!date) return '';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function parseDate(value?: string) {
  if (!value) return undefined;
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? undefined : date;
}

export function DatePicker({
  value,
  onChange,
  placeholder = '选择日期',
}: {
  value?: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  const [open, setOpen] = useState(false);
  const selected = parseDate(value);

  return (
    <div className="relative">
      <Button type="button" variant="outline" className="w-full justify-start font-normal" onClick={() => setOpen((v) => !v)}>
        <CalendarIcon className="h-4 w-4" />
        {value || <span className="text-muted-foreground">{placeholder}</span>}
      </Button>
      {value && (
        <Button
          type="button"
          size="icon"
          variant="ghost"
          className="absolute right-1 top-0 h-9 w-8"
          aria-label="清除日期"
          onClick={() => onChange('')}
        >
          <X className="h-3.5 w-3.5" />
        </Button>
      )}
      {open && (
        <div className="absolute z-40 mt-2">
          <Calendar
            mode="single"
            selected={selected}
            onSelect={(date) => {
              onChange(formatDate(date));
              setOpen(false);
            }}
          />
        </div>
      )}
    </div>
  );
}
