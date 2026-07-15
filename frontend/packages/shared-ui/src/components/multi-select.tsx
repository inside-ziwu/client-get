'use client';

import * as PopoverPrimitive from '@radix-ui/react-popover';
import { Command } from 'cmdk';
import { Check, ChevronsUpDown, LoaderCircle, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import { cn } from '../lib/utils';
import { Badge } from './badge';
import { Button } from './button';

export interface MultiSelectOption {
  label: string;
  value: string;
}

export interface MultiSelectProps {
  value: readonly string[];
  options: readonly MultiSelectOption[];
  onChange: (value: string[]) => void;
  displayMode?: 'badges' | 'summary';
  placeholder?: string;
  searchPlaceholder?: string;
  optionState?: 'ready' | 'loading' | 'empty';
  allowCreate?: boolean;
  disabled?: boolean;
  className?: string;
}

export function MultiSelect({
  value,
  options,
  onChange,
  displayMode = 'badges',
  placeholder = '选择或输入',
  searchPlaceholder,
  optionState = 'ready',
  allowCreate = true,
  disabled = false,
  className,
}: MultiSelectProps) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const selected = new Set(value);
  const normalizedOptions = useMemo(() => {
    const map = new Map(options.map((item) => [item.value, item]));
    for (const item of value) {
      if (!map.has(item)) map.set(item, { label: item, value: item });
    }
    return Array.from(map.values());
  }, [options, value]);
  const visibleOptions = normalizedOptions.filter((item) =>
    `${item.label} ${item.value}`.toLowerCase().includes(query.toLowerCase()),
  );
  const canCreate =
    optionState === 'ready' && allowCreate && query.trim() && !selected.has(query.trim());
  const triggerPlaceholder =
    optionState === 'loading'
      ? '正在加载选项…'
      : optionState === 'empty'
        ? '暂无可选项'
        : placeholder;
  const selectedLabels = value.map(
    (item) => normalizedOptions.find((option) => option.value === item)?.label ?? item,
  );
  const selectedSummary =
    value.length === 1 ? selectedLabels[0] : `已选 ${value.length} 项`;

  const toggle = (item: string) => {
    if (disabled || optionState !== 'ready') return;
    onChange(selected.has(item) ? value.filter((current) => current !== item) : [...value, item]);
  };

  return (
    <PopoverPrimitive.Root
      open={disabled ? false : open}
      onOpenChange={(nextOpen) => {
        if (!disabled) setOpen(nextOpen);
      }}
    >
      <PopoverPrimitive.Trigger asChild>
        <Button
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn(
            displayMode === 'summary'
              ? 'h-10 min-h-10 overflow-hidden'
              : 'min-h-9 h-auto',
            'w-full justify-between',
            className,
          )}
        >
          <span
            className={cn(
              'min-w-0',
              displayMode === 'summary'
                ? 'flex-1 truncate text-left'
                : 'flex flex-wrap gap-1',
            )}
          >
            {value.length ? (
              displayMode === 'summary' ? (
                <span className="block truncate" title={selectedLabels.join('、')}>
                  {selectedSummary}
                </span>
              ) : (
                value.map((item) => (
                  <Badge key={item} variant="secondary" className="gap-1">
                    {normalizedOptions.find((option) => option.value === item)?.label ?? item}
                    {disabled ? null : (
                      <span
                        role="button"
                        tabIndex={0}
                        aria-label={`移除 ${item}`}
                        onClick={(event) => {
                          event.preventDefault();
                          event.stopPropagation();
                          onChange(value.filter((current) => current !== item));
                        }}
                        onKeyDown={(event) => {
                          if (event.key === 'Enter' || event.key === ' ') {
                            event.preventDefault();
                            event.stopPropagation();
                            onChange(value.filter((current) => current !== item));
                          }
                        }}
                      >
                        <X className="h-3 w-3" />
                      </span>
                    )}
                  </Badge>
                ))
              )
            ) : (
              <span className="text-muted-foreground">{triggerPlaceholder}</span>
            )}
          </span>
          {optionState === 'loading' ? (
            <LoaderCircle className="h-4 w-4 shrink-0 animate-spin opacity-60" aria-hidden="true" />
          ) : (
            <ChevronsUpDown className="h-4 w-4 shrink-0 opacity-50" />
          )}
        </Button>
      </PopoverPrimitive.Trigger>
      <PopoverPrimitive.Portal>
        <PopoverPrimitive.Content
          align="start"
          className="z-50 mt-1 w-[var(--radix-popover-trigger-width)] rounded-md border bg-card p-1 shadow-md"
        >
          <Command shouldFilter={false}>
            <Command.Input
              value={query}
              onValueChange={setQuery}
              placeholder={searchPlaceholder ?? placeholder}
              disabled={optionState !== 'ready'}
              className="h-9 w-full rounded-md bg-transparent px-2 text-sm outline-none placeholder:text-muted-foreground"
            />
            <Command.List className="max-h-56 overflow-auto py-1">
              {optionState === 'loading' ? (
                <div
                  role="status"
                  className="flex items-center justify-center gap-2 px-2 py-6 text-sm text-muted-foreground"
                >
                  <LoaderCircle className="h-4 w-4 animate-spin" aria-hidden="true" />
                  正在加载选项…
                </div>
              ) : optionState === 'empty' ? (
                <div role="status" className="px-2 py-6 text-center text-sm text-muted-foreground">
                  暂无可选项
                </div>
              ) : (
                <>
                  {visibleOptions.map((item) => (
                    <Command.Item
                      key={item.value}
                      value={item.value}
                      onSelect={() => toggle(item.value)}
                      className="flex cursor-pointer items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-muted"
                    >
                      <span className="flex h-4 w-4 shrink-0 items-center justify-center rounded-sm border border-input">
                        {selected.has(item.value) ? <Check className="h-3 w-3" /> : null}
                      </span>
                      <span className="min-w-0 flex-1 truncate">{item.label}</span>
                    </Command.Item>
                  ))}
                  {canCreate ? (
                    <Command.Item
                      value={query.trim()}
                      onSelect={() => {
                        onChange([...value, query.trim()]);
                        setQuery('');
                      }}
                      className="cursor-pointer rounded-sm px-2 py-1.5 text-sm text-primary hover:bg-muted"
                    >
                      新增 “{query.trim()}”
                    </Command.Item>
                  ) : null}
                  {!visibleOptions.length && !canCreate ? (
                    <div className="px-2 py-6 text-center text-sm text-muted-foreground">
                      没有匹配项
                    </div>
                  ) : null}
                </>
              )}
            </Command.List>
          </Command>
        </PopoverPrimitive.Content>
      </PopoverPrimitive.Portal>
    </PopoverPrimitive.Root>
  );
}
