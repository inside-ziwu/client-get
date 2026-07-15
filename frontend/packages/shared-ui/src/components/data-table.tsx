'use client';

import * as React from 'react';
import { cn } from '../lib/utils';
import { Badge, type BadgeTone } from './badge';
import { Checkbox } from './checkbox';
import { Switch } from './switch';
import { TableState, type TableStateSpec } from './table-state';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './tooltip';

export type ColumnWidth = 'sm' | 'md' | 'lg' | 'xl';
export type StatusTone = BadgeTone;

interface BaseDataTableColumn {
  id: string;
  header: React.ReactNode;
  width: ColumnWidth;
}

type ValueColumn<T> = BaseDataTableColumn & {
  value: keyof T | ((row: T) => unknown);
};

export type DataTableColumn<T> =
  | (ValueColumn<T> & {
      type: 'text' | 'number';
      render?: (row: T) => React.ReactNode;
      format?: (value: unknown, row: T) => React.ReactNode;
    })
  | (ValueColumn<T> &
      {
        type: 'date';
      } & (
        | {
            format: (value: unknown, row: T) => React.ReactNode;
            render?: (row: T) => React.ReactNode;
          }
        | {
            render: (row: T) => React.ReactNode;
            format?: (value: unknown, row: T) => React.ReactNode;
          }
      ))
  | (ValueColumn<T> & {
      type: 'status';
      statusMap: Record<string, { label: string; tone: StatusTone }>;
      render?: (row: T) => React.ReactNode;
    })
  | (ValueColumn<T> &
      {
        type: 'boolean';
        getBooleanLabel: (row: T) => string;
      } & (
        | { booleanMode: 'readOnly' }
        | {
            booleanMode: 'interactive';
            onBooleanChange: (row: T, next: boolean) => void;
            isBooleanDisabled?: (row: T) => boolean;
          }
      ))
  | (BaseDataTableColumn & {
      type: 'actions';
      render: (row: T) => React.ReactNode;
    });

export interface DataTableSelection<T> {
  selectedKeys: ReadonlySet<string>;
  isRowDisabled?: (row: T) => boolean;
  onToggleRow: (row: T) => void;
  onTogglePage: (rows: readonly T[]) => void;
}

export interface DataTableProps<T> {
  data: readonly T[];
  columns: ReadonlyArray<DataTableColumn<T>>;
  getRowId: (row: T) => string;
  entityName: string;
  state?: TableStateSpec;
  isRefreshing?: boolean;
  stickyHeader?: boolean;
  selection?: DataTableSelection<T>;
  stickyActions?: boolean;
  className?: string;
}

const columnWidthClasses: Record<ColumnWidth, string> = {
  sm: 'w-ui-table-sm min-w-ui-table-sm max-w-ui-table-sm',
  md: 'w-ui-table-md min-w-ui-table-md max-w-ui-table-md',
  lg: 'w-ui-table-lg min-w-ui-table-lg max-w-ui-table-lg',
  xl: 'w-ui-table-xl min-w-ui-table-xl max-w-ui-table-xl',
};

function resolveValue<T>(column: ValueColumn<T>, row: T): unknown {
  return typeof column.value === 'function' ? column.value(row) : row[column.value];
}

function defaultValue(value: unknown): React.ReactNode {
  return value == null || value === '' ? '-' : String(value);
}

function TruncatedText({ children }: { children: React.ReactNode }) {
  const contentRef = React.useRef<HTMLSpanElement>(null);
  const [isOverflowing, setIsOverflowing] = React.useState(false);

  React.useLayoutEffect(() => {
    const content = contentRef.current;
    if (!content) return;

    const measure = () => setIsOverflowing(content.scrollWidth > content.clientWidth);
    measure();

    if (typeof ResizeObserver === 'undefined') {
      window.addEventListener('resize', measure);
      return () => window.removeEventListener('resize', measure);
    }

    const observer = new ResizeObserver(measure);
    observer.observe(content);
    return () => observer.disconnect();
  }, [children, isOverflowing]);

  const content = (
    <span ref={contentRef} className="block truncate">
      {children}
    </span>
  );

  if (!isOverflowing) return content;

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span ref={contentRef} className="block truncate" tabIndex={0}>
            {children}
          </span>
        </TooltipTrigger>
        <TooltipContent>{children}</TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function columnAlignment<T>(column: DataTableColumn<T>) {
  if (column.type === 'number' || column.type === 'actions') return 'text-right';
  return 'text-left';
}

function renderCell<T>(column: DataTableColumn<T>, row: T): React.ReactNode {
  if (column.type === 'actions') return column.render(row);

  const value = resolveValue(column, row);

  if ('render' in column && column.render) return column.render(row);
  if ('format' in column && column.format) return column.format(value, row);

  if (column.type === 'text') return <TruncatedText>{defaultValue(value)}</TruncatedText>;
  if (column.type === 'number') return defaultValue(value);
  if (column.type === 'status') {
    const key = value == null || value === '' ? '-' : String(value);
    const status = column.statusMap[key] ?? { label: key, tone: 'neutral' as const };
    return <Badge tone={status.tone}>{status.label}</Badge>;
  }
  if (column.type === 'boolean') {
    const checked = Boolean(value);
    const label = column.getBooleanLabel(row);

    if (column.booleanMode === 'interactive') {
      return (
        <Switch
          aria-label={label}
          className="focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas data-[state=checked]:bg-ui-primary"
          checked={checked}
          disabled={column.isBooleanDisabled?.(row)}
          onCheckedChange={(next) => column.onBooleanChange(row, next)}
        />
      );
    }

    return <Badge tone={checked ? 'success' : 'neutral'}>{label}</Badge>;
  }

  return defaultValue(value);
}

export function DataTable<T>({
  className,
  columns,
  data,
  entityName,
  getRowId,
  isRefreshing = false,
  selection,
  state,
  stickyActions = true,
  stickyHeader = true,
}: DataTableProps<T>) {
  const actionColumnCount = columns.filter((column) => column.type === 'actions').length;
  if (actionColumnCount > 1) throw new Error('DataTable 仅支持一个 actions 列');

  const selectableRows = selection
    ? data.filter((row) => !selection.isRowDisabled?.(row))
    : [];
  const selectedSelectableCount = selection
    ? selectableRows.filter((row) => selection.selectedKeys.has(getRowId(row))).length
    : 0;
  const allSelected = selectableRows.length > 0 && selectedSelectableCount === selectableRows.length;
  const partiallySelected = selectedSelectableCount > 0 && !allSelected;
  const colSpan = columns.length + (selection ? 1 : 0);

  return (
    <div
      className={cn(
        'relative overflow-x-auto rounded-ui-lg border border-ui-border bg-ui-canvas [container-type:inline-size]',
        className,
      )}
      data-data-table-scroll
    >
      {isRefreshing ? (
        <div className="sticky left-0 top-0 z-30 flex h-0 justify-end" role="status">
          <span className="m-ui-xs rounded-ui-pill bg-ui-surface-soft px-ui-sm py-ui-xxs text-ui-caption text-ui-muted-foreground">
            更新中…
          </span>
        </div>
      ) : null}
      <table
        aria-busy={isRefreshing}
        aria-label={`${entityName}列表`}
        className="w-max min-w-full table-fixed border-collapse text-ui-body"
      >
        <colgroup>
          {selection ? <col className="w-12 min-w-12 max-w-12" /> : null}
          {columns.map((column) => (
            <col className={columnWidthClasses[column.width]} key={column.id} />
          ))}
        </colgroup>
        <thead>
          <tr className="h-9 border-b border-ui-border bg-ui-surface-soft">
            {selection ? (
              <th
                className={cn(
                  'w-12 min-w-12 px-ui-sm py-ui-xs text-center',
                  stickyHeader && 'sticky top-0 z-20 bg-ui-surface-soft',
                )}
                scope="col"
              >
                <Checkbox
                  aria-label={`选择当前页${entityName}`}
                  className="border-ui-foreground focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas data-[state=checked]:bg-ui-primary data-[state=checked]:text-ui-on-primary"
                  checked={allSelected ? true : partiallySelected ? 'indeterminate' : false}
                  disabled={selectableRows.length === 0}
                  onCheckedChange={() => selection.onTogglePage(selectableRows)}
                />
              </th>
            ) : null}
            {columns.map((column) => {
              const stickyAction = column.type === 'actions' && stickyActions;
              return (
                <th
                  className={cn(
                    columnWidthClasses[column.width],
                    'px-ui-sm py-ui-xs text-ui-caption text-ui-muted-foreground',
                    columnAlignment(column),
                    stickyHeader && 'sticky top-0 z-10 bg-ui-surface-soft',
                    stickyAction &&
                      'sticky right-0 z-20 border-l border-ui-border bg-ui-surface-soft shadow-[-4px_0_8px_-6px_rgba(15,23,42,0.35)]',
                  )}
                  key={column.id}
                  scope="col"
                >
                  {column.header}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {state ? <TableState colSpan={colSpan} entityName={entityName} state={state} /> : null}
          {!state
            ? data.map((row) => {
                const rowId = getRowId(row);
                return (
                  <tr className="h-10 border-b border-ui-border-soft last:border-b-0" key={rowId}>
                    {selection ? (
                      <td className="w-12 min-w-12 px-ui-sm py-ui-xs text-center">
                        <Checkbox
                          aria-label={`选择${entityName} ${rowId}`}
                          className="border-ui-foreground focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas data-[state=checked]:bg-ui-primary data-[state=checked]:text-ui-on-primary"
                          checked={selection.selectedKeys.has(rowId)}
                          disabled={selection.isRowDisabled?.(row)}
                          onCheckedChange={() => selection.onToggleRow(row)}
                        />
                      </td>
                    ) : null}
                    {columns.map((column) => {
                      const stickyAction = column.type === 'actions' && stickyActions;
                      return (
                        <td
                          className={cn(
                            columnWidthClasses[column.width],
                            'px-ui-sm py-ui-xs align-middle text-ui-body',
                            columnAlignment(column),
                            column.type === 'number' && 'tabular-nums',
                            column.type === 'date' && 'whitespace-nowrap',
                            stickyAction &&
                              'sticky right-0 z-10 border-l border-ui-border bg-ui-canvas shadow-[-4px_0_8px_-6px_rgba(15,23,42,0.35)]',
                          )}
                          key={column.id}
                        >
                          {renderCell(column, row)}
                        </td>
                      );
                    })}
                  </tr>
                );
              })
            : null}
        </tbody>
      </table>
    </div>
  );
}
