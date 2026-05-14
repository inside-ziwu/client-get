'use client';

import type { LixiaoyunRawCompanyRow, LixiaoyunRawContactRow } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Search, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

const PAGE_SIZE_OPTIONS = [20, 50, 100] as const;

interface PageData {
  data: LixiaoyunRawCompanyRow[];
  pagination: { cursor: string | null; has_more: boolean; total?: number };
}

type FilterValues = {
  name: string;
  keyword_filter: string;
  found_from: string;
  found_to: string;
  reg_capital: string;
  employee_scale: string;
  contacts_count: string;
  has_name_en: boolean;
  has_domain: boolean;
};

const EMPTY_FILTERS: FilterValues = {
  name: '',
  keyword_filter: '',
  found_from: '',
  found_to: '',
  reg_capital: '',
  employee_scale: '',
  contacts_count: '',
  has_name_en: false,
  has_domain: false,
};

function dash(value: string | number | null | undefined) {
  return value === null || value === undefined || value === '' ? '-' : String(value);
}

function emptyPage(): PageData {
  return { data: [], pagination: { cursor: null, has_more: false, total: 0 } };
}

export function PeersDataPage() {
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [jumpPage, setJumpPage] = useState('');
  const [selected, setSelected] = useState<LixiaoyunRawCompanyRow | null>(null);

  const contactsQuery = useQuery({
    queryKey: ['admin', 'peers', 'raw-lixiaoyun', 'contacts', selected?.id],
    queryFn: async () => {
      if (!selected) return [];
      try {
        const res = await adminApi.collection.listLixiaoyunRawContacts(String(selected.id));
        return res.data.data as LixiaoyunRawContactRow[];
      } catch {
        return [];
      }
    },
    enabled: Boolean(selected),
  });

  const query = useQuery({
    queryKey: ['admin', 'peers', 'raw-lixiaoyun', page, pageSize, appliedFilters],
    queryFn: async () => {
      try {
        return (
          await adminApi.collection.listLixiaoyunRawCompanies({
            page,
            page_size: pageSize,
            keyword: appliedFilters.name.trim() || undefined,
            keyword_filter: appliedFilters.keyword_filter.trim() || undefined,
            found_date_start: appliedFilters.found_from || undefined,
            found_date_end: appliedFilters.found_to || undefined,
            reg_capital: appliedFilters.reg_capital || undefined,
            employee_scale: appliedFilters.employee_scale || undefined,
            contacts_filter: appliedFilters.contacts_count || undefined,
            has_name_en: appliedFilters.has_name_en || undefined,
            has_domain: appliedFilters.has_domain || undefined,
          })
        ).data;
      } catch {
        return emptyPage();
      }
    },
  });

  const pageData = query.data ?? emptyPage();
  const total = pageData.pagination.total ?? pageData.data.length;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  const onSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAppliedFilters(filters);
    setPage(1);
  };

  const onReset = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">同行公司</h1>
          <p className="admin-page-description">励销云采集的中国同行公司原始记录。</p>
        </div>
      </div>

      <Card>
        <CardContent className="p-4">
          <form className="space-y-3" onSubmit={onSearch}>
            <div className="grid gap-3 lg:grid-cols-[220px_160px_160px_160px_1fr]">
              <Input
                placeholder="公司名（中文/英文）搜索"
                value={filters.name}
                onChange={(event) => setFilters((current) => ({ ...current, name: event.target.value }))}
              />
              <Input
                placeholder="全部关键词"
                value={filters.keyword_filter}
                onChange={(event) => setFilters((current) => ({ ...current, keyword_filter: event.target.value }))}
              />
              <Input
                type="date"
                aria-label="成立时间开始"
                value={filters.found_from}
                onChange={(event) => setFilters((current) => ({ ...current, found_from: event.target.value }))}
              />
              <Input
                type="date"
                aria-label="成立时间结束"
                value={filters.found_to}
                onChange={(event) => setFilters((current) => ({ ...current, found_to: event.target.value }))}
              />
              <div className="flex items-center gap-2 text-sm text-muted-foreground">成立时间</div>
            </div>
            <div className="grid gap-3 lg:grid-cols-[150px_150px_150px_auto_auto_1fr]">
              <Select
                value={filters.reg_capital || 'all'}
                onValueChange={(value) => setFilters((current) => ({ ...current, reg_capital: value === 'all' ? '' : value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="注册资金（不限）" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">注册资金（不限）</SelectItem>
                  <SelectItem value="lt100">&lt; 100 万</SelectItem>
                  <SelectItem value="100_500">100 - 500 万</SelectItem>
                  <SelectItem value="500_2000">500 - 2000 万</SelectItem>
                  <SelectItem value="2000_1e">2000 万 - 1 亿</SelectItem>
                  <SelectItem value="gt1e">&gt; 1 亿</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={filters.employee_scale || 'all'}
                onValueChange={(value) => setFilters((current) => ({ ...current, employee_scale: value === 'all' ? '' : value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="员工规模（不限）" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">员工规模（不限）</SelectItem>
                  <SelectItem value="lt10">&lt; 10 人</SelectItem>
                  <SelectItem value="10_50">10 - 50 人</SelectItem>
                  <SelectItem value="50_200">50 - 200 人</SelectItem>
                  <SelectItem value="200_1000">200 - 1000 人</SelectItem>
                  <SelectItem value="gt1000">&gt; 1000 人</SelectItem>
                </SelectContent>
              </Select>
              <Select
                value={filters.contacts_count || 'all'}
                onValueChange={(value) => setFilters((current) => ({ ...current, contacts_count: value === 'all' ? '' : value }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="联系人数（不限）" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">联系人数（不限）</SelectItem>
                  <SelectItem value="0">0（无）</SelectItem>
                  <SelectItem value="1_3">1 - 3</SelectItem>
                  <SelectItem value="4_10">4 - 10</SelectItem>
                  <SelectItem value="gt10">&gt; 10</SelectItem>
                </SelectContent>
              </Select>
              <label className="flex h-9 items-center gap-2 text-sm">
                <Checkbox
                  checked={filters.has_name_en}
                  onCheckedChange={(checked) =>
                    setFilters((current) => ({ ...current, has_name_en: checked === true }))
                  }
                />
                有英文名
              </label>
              <label className="flex h-9 items-center gap-2 text-sm">
                <Checkbox
                  checked={filters.has_domain}
                  onCheckedChange={(checked) =>
                    setFilters((current) => ({ ...current, has_domain: checked === true }))
                  }
                />
                有域名
              </label>
              <div className="flex justify-end gap-2">
                <Button type="submit">
                  <Search className="h-4 w-4" />
                  查询
                </Button>
                <Button type="button" variant="outline" onClick={onReset}>
                  <X className="h-4 w-4" />
                  重置
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1320px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  {['中文名', '英文名', '员工规模', '注册资金', '成立时间', '注册地址', '网址', '联系人', '关键词', '采集时间', '操作'].map(
                    (label) => (
                      <th key={label} className="px-3 py-2">
                        {label}
                      </th>
                    ),
                  )}
                </tr>
              </thead>
              <tbody>
                {pageData.data.map((row) => {
                  return (
                    <tr key={row.id} className="cursor-pointer border-b hover:bg-muted/40" onClick={() => setSelected(row)}>
                      <td className="max-w-[210px] px-3 py-2 font-medium">{dash(row.name)}</td>
                      <td className="max-w-[180px] px-3 py-2 text-muted-foreground">{dash(row.english_name)}</td>
                      <td className="px-3 py-2">{dash(row.employee_scale)}</td>
                      <td className="px-3 py-2">{dash(row.reg_capital)}</td>
                      <td className="px-3 py-2">{dash(row.esdate)}</td>
                      <td className="max-w-[180px] truncate px-3 py-2 text-muted-foreground">
                        {dash(row.reg_address)}
                      </td>
                      <td className="max-w-[150px] truncate px-3 py-2 text-primary">{dash(row.domain)}</td>
                      <td className="px-3 py-2">
                        <Badge variant={row.contacts_count > 0 ? 'secondary' : 'outline'}>{row.contacts_count}</Badge>
                      </td>
                      <td className="px-3 py-2">
                        {row.keyword_normalized ? <Badge variant="outline">{row.keyword_normalized}</Badge> : '-'}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{formatDateTime(row.created_at)}</td>
                      <td className="px-3 py-2">
                        <Button size="sm" variant="outline" onClick={() => setSelected(row)}>
                          详情
                        </Button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {!pageData.data.length && (
              <div className="py-10 text-center text-sm text-muted-foreground">
                {query.isFetching ? '正在加载同行公司...' : '暂无同行公司记录'}
              </div>
            )}
          </div>
          <div className="flex items-center justify-between border-t px-4 py-3 text-sm">
            <div className="flex items-center gap-3">
              <span className="text-muted-foreground">共 {total} 条</span>
              <Select
                value={String(pageSize)}
                onValueChange={(v) => { setPageSize(Number(v)); setPage(1); }}
              >
                <SelectTrigger className="h-8 w-[100px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((n) => (
                    <SelectItem key={n} value={String(n)}>{n} 条/页</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
                上一页
              </Button>
              <span>第</span>
              <Input
                type="number"
                className="h-8 w-16 text-center"
                min={1}
                max={maxPage}
                value={jumpPage || page}
                onChange={(e) => setJumpPage(e.target.value)}
                onFocus={() => setJumpPage(String(page))}
                onBlur={() => {
                  if (jumpPage) {
                    const clamped = Math.max(1, Math.min(Number(jumpPage) || 1, maxPage));
                    setPage(clamped);
                  }
                  setJumpPage('');
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    const clamped = Math.max(1, Math.min(Number(jumpPage) || 1, maxPage));
                    setPage(clamped);
                    setJumpPage('');
                    (e.target as HTMLInputElement).blur();
                  }
                }}
              />
              <span>/ {maxPage} 页</span>
              <Button
                variant="outline"
                size="sm"
                disabled={page >= maxPage && !pageData.pagination.has_more}
                onClick={() => setPage((current) => current + 1)}
              >
                下一页
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Sheet open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="max-w-2xl overflow-y-auto p-0 sm:w-[620px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{selected?.name || selected?.english_name || '详情'}</SheetTitle>
            <SheetDescription>原始同行公司记录详情</SheetDescription>
          </div>
          {selected && (
            <div className="space-y-5 p-5 text-sm">
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">基本信息</h2>
                <DescriptionGrid
                  rows={[
                    ['中文名', dash(selected.name)],
                    ['英文名', dash(selected.english_name)],
                    ['网址', dash(selected.domain)],
                    ['成立时间', dash(selected.esdate)],
                    ['员工规模', dash(selected.employee_scale)],
                    ['注册资金', dash(selected.reg_capital)],
                    ['公司法人', dash(selected.legalperson)],
                    ['统一信用代码', dash(selected.uncid)],
                    ['注册地址', dash(selected.reg_address)],
                  ]}
                />
              </section>

              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">采集信息</h2>
                <DescriptionGrid
                  rows={[
                    ['励销云 ID', dash(selected.source_id || selected.id)],
                    ['关键词', dash(selected.keyword_normalized)],
                    ['联系人', dash(selected.contacts_count)],
                    ['采集时间', formatDateTime(selected.created_at)],
                  ]}
                />
              </section>

              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  联系人 ({contactsQuery.data?.length ?? 0})
                </h2>
                {contactsQuery.isFetching ? (
                  <p className="text-muted-foreground">加载中...</p>
                ) : contactsQuery.data?.length ? (
                  <div className="space-y-2">
                    {contactsQuery.data.map((c) => (
                      <div key={c.id} className="rounded-md border p-3">
                        <div className="flex items-center justify-between">
                          <span className="font-medium">{c.name || '-'}</span>
                          {c.position && <Badge variant="outline">{c.position}</Badge>}
                        </div>
                        <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                          {c.email && <span>邮箱: {c.email}</span>}
                          {c.phone && <span>电话: {c.phone}</span>}
                          {c.mobile && <span>手机: {c.mobile}</span>}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="text-muted-foreground">暂无联系人</p>
                )}
              </section>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function DescriptionGrid({ rows }: { rows: Array<[string, string]> }) {
  return (
    <dl className="overflow-hidden rounded-md border">
      {rows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[120px_1fr] border-b last:border-0">
          <dt className="bg-muted/60 px-3 py-2 text-muted-foreground">{label}</dt>
          <dd className="min-w-0 px-3 py-2 break-words">{value || '-'}</dd>
        </div>
      ))}
    </dl>
  );
}
