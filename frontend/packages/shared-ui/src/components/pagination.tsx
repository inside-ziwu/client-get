'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from './button';
import { Input } from './input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './select';

export interface PaginationValue {
  page: number;
  pageSize: number;
}

interface PaginationBaseProps {
  value: PaginationValue;
  onChange: (next: PaginationValue) => void;
  pageSizeOptions?: readonly number[];
  isDisabled?: boolean;
}

export type PaginationProps = PaginationBaseProps &
  (
    | {
        mode: 'total';
        total: number;
        showPageJump?: boolean;
      }
    | {
        mode: 'unknownTotal';
        hasNextPage: boolean;
      }
  );

const DEFAULT_PAGE_SIZE_OPTIONS = [20, 50, 100] as const;

export function Pagination(props: PaginationProps) {
  const { value, onChange, pageSizeOptions = DEFAULT_PAGE_SIZE_OPTIONS, isDisabled = false } = props;
  const pageCount =
    props.mode === 'total' ? Math.max(1, Math.ceil(Math.max(0, props.total) / value.pageSize)) : null;
  const options = useMemo(
    () => [...new Set([...pageSizeOptions, value.pageSize])].sort((left, right) => left - right),
    [pageSizeOptions, value.pageSize],
  );
  const [jumpValue, setJumpValue] = useState(String(value.page));
  const lastCommittedPage = useRef<number | null>(null);

  useEffect(() => {
    setJumpValue(String(value.page));
    lastCommittedPage.current = null;
  }, [value.page]);

  const commitJump = () => {
    if (pageCount === null) return;

    const parsedPage = Number(jumpValue.trim());
    if (jumpValue.trim() === '' || !Number.isFinite(parsedPage)) {
      setJumpValue(String(value.page));
      return;
    }

    const nextPage = Math.min(pageCount, Math.max(1, Math.trunc(parsedPage)));
    setJumpValue(String(nextPage));
    if (nextPage === value.page || lastCommittedPage.current === nextPage) return;

    lastCommittedPage.current = nextPage;
    onChange({ page: nextPage, pageSize: value.pageSize });
  };

  const previousDisabled = isDisabled || value.page <= 1;
  const nextDisabled =
    isDisabled ||
    (props.mode === 'total' ? value.page >= pageCount! : !props.hasNextPage);

  return (
    <nav
      aria-label="分页"
      className="flex min-h-14 flex-col gap-ui-sm rounded-ui-lg border border-ui-border bg-ui-canvas px-ui-md py-ui-sm text-ui-body text-ui-muted-foreground sm:flex-row sm:items-center sm:justify-between"
    >
      <div className="flex flex-wrap items-center gap-ui-sm">
        {props.mode === 'total' ? <span>共 {Math.max(0, props.total)} 条</span> : null}
        <Select
          value={String(value.pageSize)}
          disabled={isDisabled}
          onValueChange={(nextPageSize) =>
            onChange({ page: 1, pageSize: Number(nextPageSize) })
          }
        >
          <SelectTrigger
            className="h-10 w-auto min-w-28 rounded-ui-md border-ui-border bg-ui-canvas focus:ring-ui-foreground focus:ring-offset-2 focus:ring-offset-ui-canvas"
            aria-label="每页条数"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {options.map((option) => (
              <SelectItem key={option} value={String(option)}>
                {option} 条/页
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div className="flex flex-wrap items-center gap-ui-xs">
        {props.mode === 'total' && (props.showPageJump ?? true) ? (
          <label className="flex items-center gap-ui-xs">
            <span>跳至</span>
            <Input
              aria-label="跳转页码"
              className="h-10 w-16 rounded-ui-md border-ui-border bg-ui-canvas text-center tabular-nums focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas"
              disabled={isDisabled}
              inputMode="numeric"
              value={jumpValue}
              onChange={(event) => {
                lastCommittedPage.current = null;
                setJumpValue(event.target.value);
              }}
              onBlur={commitJump}
              onKeyDown={(event) => {
                if (event.key !== 'Enter') return;
                event.preventDefault();
                commitJump();
                event.currentTarget.blur();
              }}
            />
            <span>页</span>
          </label>
        ) : null}

        <span className="min-w-20 text-center tabular-nums" aria-live="polite">
          {props.mode === 'total' ? `第 ${value.page}/${pageCount} 页` : `第 ${value.page} 页`}
        </span>
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="h-10 w-10 rounded-ui-md border-ui-border bg-ui-canvas hover:bg-ui-surface-card focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas"
          aria-label="上一页"
          disabled={previousDisabled}
          onClick={() => onChange({ page: value.page - 1, pageSize: value.pageSize })}
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </Button>
        <Button
          type="button"
          variant="outline"
          size="icon"
          className="h-10 w-10 rounded-ui-md border-ui-border bg-ui-canvas hover:bg-ui-surface-card focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas"
          aria-label="下一页"
          disabled={nextDisabled}
          onClick={() => onChange({ page: value.page + 1, pageSize: value.pageSize })}
        >
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </nav>
  );
}
