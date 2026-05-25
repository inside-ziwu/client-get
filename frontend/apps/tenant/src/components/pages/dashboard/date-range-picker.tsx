'use client';

import { useState } from 'react';
import { Button } from '@shared/ui';

export type DatePreset = 'today' | 'yesterday' | 'last7' | 'last30';

interface DateRange {
  start_date: string;
  end_date: string;
}

interface DateRangePickerProps {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

function formatDate(d: Date): string {
  return d.toISOString().slice(0, 10);
}

function getPresetRange(preset: DatePreset): DateRange {
  const today = new Date();
  const end = formatDate(today);
  switch (preset) {
    case 'today':
      return { start_date: end, end_date: end };
    case 'yesterday': {
      const y = new Date(today);
      y.setDate(y.getDate() - 1);
      const yd = formatDate(y);
      return { start_date: yd, end_date: yd };
    }
    case 'last7': {
      const s = new Date(today);
      s.setDate(s.getDate() - 6);
      return { start_date: formatDate(s), end_date: end };
    }
    case 'last30': {
      const s = new Date(today);
      s.setDate(s.getDate() - 29);
      return { start_date: formatDate(s), end_date: end };
    }
  }
}

const presets: { key: DatePreset; label: string }[] = [
  { key: 'today', label: '今天' },
  { key: 'yesterday', label: '昨天' },
  { key: 'last7', label: '近7天' },
  { key: 'last30', label: '近30天' },
];

export function DateRangePicker({ value, onChange }: DateRangePickerProps) {
  const [activePreset, setActivePreset] = useState<DatePreset | null>('last30');

  const handlePreset = (preset: DatePreset) => {
    setActivePreset(preset);
    onChange(getPresetRange(preset));
  };

  const handleInputChange = (field: 'start_date' | 'end_date', v: string) => {
    setActivePreset(null);
    onChange({ ...value, [field]: v });
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      {presets.map((p) => (
        <Button
          key={p.key}
          variant={activePreset === p.key ? 'default' : 'outline'}
          size="sm"
          onClick={() => handlePreset(p.key)}
        >
          {p.label}
        </Button>
      ))}
      <div className="flex items-center gap-1 text-sm">
        <input
          type="date"
          className="h-8 rounded-md border border-input bg-background px-2 text-sm"
          value={value.start_date}
          onChange={(e) => handleInputChange('start_date', e.target.value)}
        />
        <span className="text-muted-foreground">~</span>
        <input
          type="date"
          className="h-8 rounded-md border border-input bg-background px-2 text-sm"
          value={value.end_date}
          onChange={(e) => handleInputChange('end_date', e.target.value)}
        />
      </div>
    </div>
  );
}

export { getPresetRange };
