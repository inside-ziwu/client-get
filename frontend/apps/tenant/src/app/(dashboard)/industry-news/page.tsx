'use client';

import type { IndustryNewsFilters, IndustryNewsItem } from '@shared/types';
import { queryKeys } from '@shared/api';
import { keepPreviousData, useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import {
  Badge,
  Button,
  DataTable,
  type DataTableColumn,
  FilterBar,
  type FilterField,
  ListPage,
  Pagination,
  Switch,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

// FilterBar 的 draft 值只能是 string / string[]，「只看未读」用 '' | '1' 表达
type NewsFilterValues = {
  categories: string[];
  sources: string[];
  lang: string;
  unread_only: string;
};

const EMPTY_FILTERS: NewsFilterValues = { categories: [], sources: [], lang: '', unread_only: '' };

const LANG_LABELS: Record<string, string> = {
  en: '英文',
  'zh-CN': '简体中文',
  'zh-TW': '繁体中文',
};

function langLabel(lang: string) {
  return LANG_LABELS[lang] ?? lang;
}

function buildListParams(applied: NewsFilterValues, page: number, pageSize: number): IndustryNewsFilters {
  return {
    ...(applied.categories.length > 0 ? { 'category[]': [...applied.categories] } : {}),
    ...(applied.sources.length > 0 ? { 'source_id[]': [...applied.sources] } : {}),
    ...(applied.lang ? { lang: applied.lang } : {}),
    ...(applied.unread_only === '1' ? { unread_only: true } : {}),
    page,
    page_size: pageSize,
  };
}

function countAppliedFilters(filters: NewsFilterValues) {
  let count = 0;
  if (filters.categories.length > 0) count += 1;
  if (filters.sources.length > 0) count += 1;
  if (filters.lang !== '') count += 1;
  if (filters.unread_only === '1') count += 1;
  return count;
}

export default function IndustryNewsPage() {
  const [draftFilters, setDraftFilters] = useState<NewsFilterValues>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<NewsFilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  // 本会话内点击过的动态 id：点击标题后即时呈现已读态，不手改查询缓存
  const [clickedIds, setClickedIds] = useState<ReadonlySet<string>>(() => new Set());

  const filtersQuery = useQuery({
    queryKey: queryKeys.industryNews.filters(),
    queryFn: async () => (await tenantApi.industryNews.filters()).data.data,
  });

  const listParams = buildListParams(appliedFilters, page, pageSize);
  const listQuery = useQuery({
    queryKey: queryKeys.industryNews.list({ ...listParams }),
    queryFn: async () => (await tenantApi.industryNews.list(listParams)).data,
    placeholderData: keepPreviousData,
  });

  // 点击标题新窗口打开原文并置当前用户已读；成功后不 invalidate 列表，点过的行保持可见
  const markReadMutation = useMutation({
    mutationFn: async (id: string) => tenantApi.industryNews.markRead(id),
  });

  const markClicked = (id: string) => {
    setClickedIds((current) => new Set(current).add(id));
    markReadMutation.mutate(id);
  };

  const optionState = filtersQuery.isLoading ? ('loading' as const) : filtersQuery.data ? ('ready' as const) : ('empty' as const);
  const filterOptions = filtersQuery.data;

  const fields: ReadonlyArray<FilterField<NewsFilterValues>> = [
    {
      name: 'categories',
      kind: 'multiSelect',
      label: '类别',
      placeholder: '不限',
      options: (filterOptions?.categories ?? []).map((category) => ({ label: category, value: category })),
      optionState,
      searchPlaceholder: '搜索类别',
    },
    {
      name: 'sources',
      kind: 'multiSelect',
      label: '来源',
      placeholder: '不限',
      options: (filterOptions?.sources ?? []).map((source) => ({ label: source.name, value: source.id })),
      optionState,
      searchPlaceholder: '搜索来源',
    },
    {
      name: 'lang',
      kind: 'select',
      label: '语种',
      placeholder: '不限',
      options: (filterOptions?.langs ?? []).map((lang) => ({ label: langLabel(lang), value: lang })),
      optionState,
    },
    {
      name: 'unread_only',
      kind: 'custom',
      label: '只看未读',
      render: ({ values, setValue, disabled }) => (
        <div className="flex h-10 items-center">
          <Switch
            aria-label="只看未读"
            className="focus-visible:ring-ui-foreground focus-visible:ring-offset-2 focus-visible:ring-offset-ui-canvas data-[state=checked]:bg-ui-primary"
            checked={values.unread_only === '1'}
            disabled={disabled}
            onCheckedChange={(checked) => setValue('unread_only', checked ? '1' : '')}
          />
        </div>
      ),
    },
  ];

  const columns: ReadonlyArray<DataTableColumn<IndustryNewsItem>> = [
    {
      id: 'title',
      header: '标题',
      width: 'large',
      type: 'text',
      value: 'title',
      render: (row) => {
        const isRead = row.is_read || clickedIds.has(row.id);
        return (
          <div className="flex min-w-0 items-baseline gap-ui-xs">
            <a
              href={row.url}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => markClicked(row.id)}
              className={`min-w-0 truncate ${isRead ? 'text-ui-muted-foreground' : 'text-ui-body-strong text-ui-foreground'}`}
            >
              {row.title}
            </a>
            {row.is_external ? (
              <span className="shrink-0 text-ui-caption text-ui-muted-foreground">{row.target_domain}</span>
            ) : null}
          </div>
        );
      },
    },
    { id: 'source', header: '来源', width: 'medium', type: 'text', value: 'source_name' },
    {
      id: 'category',
      header: '类别',
      width: 'small',
      type: 'text',
      value: 'category',
      render: (row) => <Badge tone="neutral">{row.category}</Badge>,
    },
    {
      id: 'lang',
      header: '语种',
      width: 'small',
      type: 'text',
      value: 'lang',
      format: (value) => langLabel(value as string),
    },
    {
      id: 'time',
      header: '时间',
      width: 'medium',
      type: 'date',
      value: 'time',
      format: (value) => formatDateTime(value as string | undefined, 'YYYY-MM-DD'),
    },
  ];

  const items = listQuery.data?.data ?? [];
  const total = listQuery.data?.pagination?.total ?? 0;
  const appliedCount = countAppliedFilters(appliedFilters);
  // 本实例没有该租户行业的启用动态源时，用说明块替换表格（TableState 空态文案不可定制）
  const noSources = filtersQuery.data?.has_sources === false;

  const handleApplyFilters = (filters: NewsFilterValues) => {
    setAppliedFilters(filters);
    setPage(1);
  };

  const handleResetFilters = () => {
    setDraftFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
  };

  const tableState = listQuery.isLoading
    ? { kind: 'loading' as const }
    : listQuery.isError
      ? { kind: 'error' as const, description: '请检查网络后重试', onRetry: () => void listQuery.refetch() }
      : items.length === 0
        ? { kind: 'empty' as const, filtered: appliedCount > 0, onResetFilters: appliedCount > 0 ? handleResetFilters : undefined }
        : undefined;

  return (
    <ListPage
      className="tenant-page"
      title="行业动态"
      description="本实例行业动态源每日抓取的行业动态"
      filters={(
        <div className="flex flex-col gap-ui-sm">
          <FilterBar
            values={draftFilters}
            fields={fields}
            appliedCount={appliedCount}
            isSubmitting={listQuery.isFetching}
            onChange={setDraftFilters}
            onSubmit={handleApplyFilters}
            onReset={handleResetFilters}
          />
          {filtersQuery.isError ? (
            <div className="flex items-center justify-between gap-ui-sm rounded-ui-md border border-ui-danger-foreground/20 bg-ui-danger-surface px-ui-md py-ui-sm text-ui-body text-ui-danger-foreground" role="alert">
              <span>筛选选项加载失败，列表仍可浏览。</span>
              <Button size="sm" variant="outline" onClick={() => void filtersQuery.refetch()}>重试</Button>
            </div>
          ) : null}
        </div>
      )}
      pagination={(
        <Pagination
          mode="total"
          total={total}
          value={{ page, pageSize }}
          isDisabled={listQuery.isLoading}
          onChange={(next) => {
            setPage(next.page);
            setPageSize(next.pageSize);
          }}
        />
      )}
    >
      {noSources ? (
        <div className="rounded-ui-md border border-ui-border bg-ui-surface-soft px-ui-md py-ui-sm text-ui-body text-ui-muted-foreground">
          本实例尚未配置动态源
        </div>
      ) : (
        <DataTable
          columns={columns}
          data={items}
          entityName="动态"
          getRowId={(row) => row.id}
          state={tableState}
          isRefreshing={listQuery.isFetching && !listQuery.isLoading}
        />
      )}
    </ListPage>
  );
}
