'use client';

import type { TimeSegment } from '@shared/api';
import { Button, Checkbox, Input, Label, Badge } from '@shared/ui';
import { Plus, Trash2 } from 'lucide-react';

export const WEEKDAYS = ['周一', '周二', '周三', '周四', '周五', '周六', '周日'];

export function WeekdayBadges({ days }: { days: number[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {days.map((day) => (
        <Badge key={day} variant="secondary">
          {WEEKDAYS[day]}
        </Badge>
      ))}
    </div>
  );
}

export function SegmentBadges({ segments }: { segments: TimeSegment[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {segments.map((segment, index) => (
        <Badge key={`${segment.start}-${segment.end}-${index}`} variant="outline">
          {segment.start}-{segment.end}
        </Badge>
      ))}
    </div>
  );
}

export function WeekdayPicker({
  value,
  onChange,
}: {
  value: number[];
  onChange: (days: number[]) => void;
}) {
  const toggle = (day: number, checked: boolean) => {
    const next = checked ? [...value, day] : value.filter((item) => item !== day);
    onChange([...new Set(next)].sort((a, b) => a - b));
  };

  return (
    <div className="flex flex-wrap gap-2">
      {WEEKDAYS.map((label, day) => (
        <label
          key={label}
          className="flex h-9 min-w-[88px] items-center gap-2 whitespace-nowrap rounded-md border border-border px-3 text-sm"
        >
          <Checkbox checked={value.includes(day)} onCheckedChange={(checked) => toggle(day, checked === true)} />
          <span>{label}</span>
        </label>
      ))}
    </div>
  );
}

export function TimeSegmentsEditor({
  value,
  onChange,
  error,
}: {
  value: TimeSegment[];
  onChange: (segments: TimeSegment[]) => void;
  error?: string | null;
}) {
  const update = (index: number, key: keyof TimeSegment, nextValue: string) => {
    onChange(value.map((segment, current) => (current === index ? { ...segment, [key]: nextValue } : segment)));
  };
  const remove = (index: number) => {
    onChange(value.filter((_, current) => current !== index));
  };

  return (
    <div className="space-y-2">
      <div className="space-y-2">
        {value.map((segment, index) => (
          <div key={index} className="grid grid-cols-[1fr_1fr_36px] items-end gap-2">
            <div className="space-y-1">
              <Label htmlFor={`segment-start-${index}`}>开始</Label>
              <Input
                id={`segment-start-${index}`}
                type="time"
                value={segment.start}
                onChange={(event) => update(index, 'start', event.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label htmlFor={`segment-end-${index}`}>结束</Label>
              <Input
                id={`segment-end-${index}`}
                type="time"
                value={segment.end}
                onChange={(event) => update(index, 'end', event.target.value)}
              />
            </div>
            <Button type="button" variant="ghost" size="icon" aria-label="删除时段" onClick={() => remove(index)}>
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
        ))}
      </div>
      {error && <p className="text-sm text-destructive">{error}</p>}
      <Button
        type="button"
        variant="outline"
        onClick={() => onChange([...value, { start: '09:00', end: '17:00' }])}
      >
        <Plus className="h-4 w-4" />
        添加时段
      </Button>
    </div>
  );
}

export function validateSegments(segments: TimeSegment[]) {
  const ranges: Array<[number, number]> = segments.flatMap((segment) => {
    const start = toMinute(segment.start);
    const end = toMinute(segment.end);
    if (start === end) return [[0, 24 * 60] as [number, number]];
    return start < end ? [[start, end] as [number, number]] : [[start, 24 * 60] as [number, number], [0, end] as [number, number]];
  });
  ranges.sort((a, b) => a[0] - b[0]);
  for (let index = 1; index < ranges.length; index += 1) {
    const current = ranges[index];
    const previous = ranges[index - 1];
    if (current && previous && current[0] < previous[1]) {
      return '发送时段不能重叠';
    }
  }
  return null;
}

function toMinute(value: string) {
  const [hour = 0, minute = 0] = value.split(':').map(Number);
  return hour * 60 + minute;
}
