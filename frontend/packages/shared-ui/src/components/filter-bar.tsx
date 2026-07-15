'use client';

import { useId, useState } from 'react';
import { cn } from '../lib/utils';
import { Button } from './button';
import { Input } from './input';
import { Label } from './label';
import { MultiSelect } from './multi-select';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './select';

export type FilterDraftValue = string | readonly string[];
export type FilterDraft = Record<string, FilterDraftValue>;

export type KeysMatching<T, V> = {
  [K in keyof T]-?: T[K] extends V ? Extract<K, string> : never;
}[keyof T];

type FilterDraftShape<T extends object> = Record<keyof T, FilterDraftValue>;

const uiControlClasses =
  'h-10 rounded-ui-md border-ui-border bg-ui-canvas text-ui-body focus-visible:border-ui-foreground focus-visible:ring-2 focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas disabled:bg-ui-surface-soft';

export interface FilterFieldRenderContext<T extends FilterDraftShape<T>> {
  values: T;
  setValue: <K extends keyof T>(name: K, value: T[K]) => void;
  disabled: boolean;
}

interface BaseFilterField {
  label: string;
  placeholder?: string;
  advanced?: boolean;
}

interface FilterOption {
  label: string;
  value: string;
}

export type FilterField<T extends FilterDraftShape<T>> =
  | (BaseFilterField & {
      name: KeysMatching<T, string>;
      kind: 'text' | 'number' | 'date';
    })
  | (BaseFilterField & {
      name: KeysMatching<T, string>;
      kind: 'select';
      options: ReadonlyArray<FilterOption>;
      optionState?: 'ready' | 'loading' | 'empty';
    })
  | (BaseFilterField & {
      name: KeysMatching<T, readonly string[]>;
      kind: 'multiSelect';
      options: ReadonlyArray<FilterOption>;
      optionState?: 'ready' | 'loading' | 'empty';
    })
  | (BaseFilterField & {
      name: Extract<keyof T, string>;
      kind: 'custom';
      render: (context: FilterFieldRenderContext<T>) => React.ReactNode;
    });

export interface FilterBarProps<T extends FilterDraftShape<T>> {
  values: T;
  fields: ReadonlyArray<FilterField<T>>;
  onChange: (next: T) => void;
  onSubmit: (draft: T) => void;
  onReset: () => void;
  isSubmitting?: boolean;
  appliedCount?: number;
}

function optionPlaceholder(
  state: 'ready' | 'loading' | 'empty',
  placeholder: string | undefined,
) {
  if (state === 'loading') return '正在加载选项…';
  if (state === 'empty') return '暂无可选项';
  return placeholder ?? '请选择';
}

function FilterControl<T extends FilterDraftShape<T>>({
  field,
  values,
  setValue,
  disabled,
  id,
}: {
  field: FilterField<T>;
  values: T;
  setValue: FilterFieldRenderContext<T>['setValue'];
  disabled: boolean;
  id: string;
}) {
  const labelId = `${id}-label`;

  if (field.kind === 'custom') {
    return (
      <div className="space-y-2" role="group" aria-labelledby={labelId}>
        <Label id={labelId}>{field.label}</Label>
        {field.render({ values, setValue, disabled })}
      </div>
    );
  }

  if (field.kind === 'multiSelect') {
    const state = field.optionState ?? 'ready';
    const value = values[field.name] as readonly string[];

    return (
      <div className="space-y-2" role="group" aria-labelledby={labelId}>
        <Label id={labelId}>{field.label}</Label>
        <MultiSelect
          className={uiControlClasses}
          value={value}
          options={field.options}
          onChange={(next) =>
            setValue(field.name, next as unknown as T[typeof field.name])
          }
          placeholder={optionPlaceholder(state, field.placeholder)}
          allowCreate={false}
          disabled={disabled || state !== 'ready'}
        />
      </div>
    );
  }

  const value = values[field.name] as string;

  if (field.kind === 'select') {
    const state = field.optionState ?? 'ready';

    return (
      <div className="space-y-2">
        <Label htmlFor={id}>{field.label}</Label>
        <Select
          value={value}
          onValueChange={(next) => setValue(field.name, next as T[typeof field.name])}
          disabled={disabled || state !== 'ready'}
        >
          <SelectTrigger className={uiControlClasses} id={id}>
            <SelectValue placeholder={optionPlaceholder(state, field.placeholder)} />
          </SelectTrigger>
          <SelectContent>
            {field.options.map((option) => (
              <SelectItem key={option.value} value={option.value}>
                {option.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{field.label}</Label>
      <Input
        className={uiControlClasses}
        id={id}
        type={field.kind}
        value={value}
        placeholder={field.placeholder}
        disabled={disabled}
        onChange={(event) =>
          setValue(field.name, event.target.value as T[typeof field.name])
        }
      />
    </div>
  );
}

export function FilterBar<T extends FilterDraftShape<T>>({
  values,
  fields,
  onChange,
  onSubmit,
  onReset,
  isSubmitting = false,
  appliedCount = 0,
}: FilterBarProps<T>) {
  const id = useId();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const basicFields = fields.filter((field) => !field.advanced);
  const advancedFields = fields.filter((field) => field.advanced);
  const advancedId = `${id}-advanced`;
  const setValue: FilterFieldRenderContext<T>['setValue'] = (name, value) => {
    onChange({ ...values, [name]: value });
  };
  const renderFields = (items: ReadonlyArray<FilterField<T>>) =>
    items.map((field) => (
      <FilterControl
        key={`${field.kind}-${field.name}`}
        field={field}
        values={values}
        setValue={setValue}
        disabled={isSubmitting}
        id={`${id}-${field.name}`}
      />
    ));

  return (
    <form
      className="rounded-ui-lg border border-ui-border bg-ui-surface-soft p-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit(values);
      }}
    >
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {renderFields(basicFields)}
      </div>

      {advancedFields.length > 0 ? (
        <>
          <Button
            type="button"
            variant="ghost"
            className="mt-3 h-10 rounded-ui-md focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas sm:hidden"
            aria-controls={advancedId}
            aria-expanded={advancedOpen}
            onClick={() => setAdvancedOpen((current) => !current)}
            disabled={isSubmitting}
          >
            {advancedOpen ? '收起更多条件' : '更多条件'}
            {appliedCount > 0 ? `（${appliedCount}）` : null}
          </Button>
          <div
            id={advancedId}
            data-testid="filter-bar-advanced-fields"
            className={cn(
              'mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4',
              !advancedOpen && 'hidden sm:grid',
            )}
          >
            {renderFields(advancedFields)}
          </div>
        </>
      ) : null}

      <div className="mt-4 flex flex-wrap justify-end gap-2">
        <Button
          type="button"
          variant="outline"
          className="h-10 rounded-ui-md border-ui-border bg-ui-canvas px-ui-md text-ui-body-strong hover:bg-ui-surface-card focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas"
          onClick={onReset}
          disabled={isSubmitting}
        >
          重置
        </Button>
        <Button
          type="submit"
          className="h-10 rounded-ui-md bg-ui-primary px-ui-md text-ui-body-strong text-ui-on-primary hover:bg-ui-primary-active focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas disabled:bg-ui-primary-disabled disabled:text-ui-body disabled:opacity-100"
          disabled={isSubmitting}
        >
          {isSubmitting ? '查询中…' : '查询'}
        </Button>
      </div>
    </form>
  );
}
