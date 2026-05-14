'use client';

import type { PeerCompanyRow } from '@shared/api';
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

const PAGE_SIZE = 20;

type FilterValues = {
  name: string;
  keyword_filter: string;
  found_date_start: string;
  found_date_end: string;
  reg_capital: string;
  employee_scale: string;
  contacts_count: string;
  has_name_en: boolean;
  has_domain: boolean;
};

const EMPTY_FILTERS: FilterValues = {
  name: '',
  keyword_filter: '',
  found_date_start: '',
  found_date_end: '',
  reg_capital: '',
  employee_scale: '',
  contacts_count: '',
  has_name_en: false,
  has_domain: false,
};

function dash(value: string | number | null | undefined) {
  return value === null || value === undefined || value === '' ? '-' : String(value);
}

function emptyPage() {
  return { data: [] as PeerCompanyRow[], pagination: { cursor: null, has_more: false, total: 0 } };
}

export function PeersCleanedPage() {
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<PeerCompanyRow | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'peer-companies', page, appliedFilters],
    queryFn: async () => {
      try {
        return (
          await adminApi.collection.listPeerCompanies({
            page,
            page_size: PAGE_SIZE,
            keyword: appliedFilters.name.trim() || undefined,
            keyword_filter: appliedFilters.keyword_filter.trim() || undefined,
            found_date_start: appliedFilters.found_date_start || undefined,
            found_date_end: appliedFilters.found_date_end || undefined,
            reg_capital: appliedFilters.reg_capital || undefined,
            employee_scale: appliedFilters.employee_scale || undefined,
            contacts_count: appliedFilters.contacts_count || undefined,
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
  const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));

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
          <h1 className="admin-page-title">同行数据（清洗）</h1>
          <p className="admin-page-description">按官网或励销云 source_id 去重后的同行公司池。</p>
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
                placeholder="关键词搜索"
                value={filters.keyword_filter}
                onChange={(event) => setFilters((current) => ({ ...current, keyword_filter: event.target.value }))}
              />
              <Input
                type="date"
                aria-label="成立时间开始"
                value={filters.found_date_start}
                onChange={(event) => setFilters((current) => ({ ...current, found_date_start: event.target.value }))}
              />
              <Input
                type="date"
                aria-label="成立时间结束"
                value={filters.found_date_end}
                onChange={(event) => setFilters((current) => ({ ...current, found_date_end: event.target.value }))}
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
                  onCheckedChange={(checked) => setFilters((current) => ({ ...current, has_name_en: checked === true }))}
                />
                有英文名
              </label>
              <label className="flex h-9 items-center gap-2 text-sm">
                <Checkbox
                  checked={filters.has_domain}
                  onCheckedChange={(checked) => setFilters((current) => ({ ...current, has_domain: checked === true }))}
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
            <table className="w-full min-w-[1380px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  {['中文名', '英文名', '员工规模', '注册资金', '成立时间', '注册地址', '网址', '联系人', '关键词', '采集时间', '操作'].map((label) => (
                    <th key={label} className="px-3 py-2">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageData.data.map((row) => (
                  <tr key={row.id} className="cursor-pointer border-b hover:bg-muted/40" onClick={() => setSelected(row)}>
                    <td className="max-w-[210px] px-3 py-2 font-medium">{dash(row.name)}</td>
                    <td className="max-w-[180px] px-3 py-2 text-muted-foreground">{dash(row.english_name)}</td>
                    <td className="px-3 py-2">{dash(row.employee_scale)}</td>
                    <td className="px-3 py-2">{dash(row.reg_capital)}</td>
                    <td className="px-3 py-2">{dash(row.esdate)}</td>
                    <td className="max-w-[180px] truncate px-3 py-2 text-muted-foreground">{dash(row.reg_address)}</td>
                    <td className="max-w-[150px] truncate px-3 py-2 text-primary">{dash(row.domain || row.website_host)}</td>
                    <td className="px-3 py-2"><Badge variant={row.contact_count > 0 ? 'secondary' : 'outline'}>{row.contact_count}</Badge></td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {row.keywords.slice(0, 3).map((item) => (
                          <Badge key={item.keyword_master_id} variant="outline">{item.keyword}</Badge>
                        ))}
                        {row.keywords.length > 3 ? <Badge variant="secondary">+{row.keywords.length - 3}</Badge> : null}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">{formatDateTime(row.last_seen_at)}</td>
                    <td className="px-3 py-2">
                      <Button size="sm" variant="outline" onClick={() => setSelected(row)}>详情</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!pageData.data.length && (
              <div className="py-10 text-center text-sm text-muted-foreground">
                {query.isFetching ? '正在加载同行数据（清洗）...' : '暂无清洗后的同行公司'}
              </div>
            )}
          </div>
          <div className="flex items-center justify-between border-t px-4 py-3 text-sm">
            <span className="text-muted-foreground">共 {total} 条</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
                上一页
              </Button>
              <span>第 {page} / {maxPage} 页</span>
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
            <SheetTitle>{selected?.name || selected?.english_name || '同行公司详情'}</SheetTitle>
            <SheetDescription>清洗去重后的同行公司记录详情</SheetDescription>
          </div>
          {selected && (
            <div className="space-y-5 p-5 text-sm">
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">基本信息</h2>
                <DescriptionGrid
                  rows={[
                    ['中文名', dash(selected.name)],
                    ['英文名', dash(selected.english_name)],
                    ['是否有英文名', selected.has_english_name ? '是' : '否'],
                    ['网址', dash(selected.domain || selected.website_host)],
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
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">清洗信息</h2>
                <DescriptionGrid
                  rows={[
                    ['Raw 数', dash(selected.raw_count)],
                    ['关键词数', dash(selected.keyword_count)],
                    ['联系人', dash(selected.contact_count)],
                    ['身份类型', dash(selected.identity_type)],
                    ['身份值', dash(selected.identity_value)],
                    ['合并原因', dash(selected.merge_reason)],
                    ['冲突数', dash(selected.conflict_count)],
                    ['励销云 source_id', selected.source_ids.length ? selected.source_ids.join(', ') : dash(selected.source_id)],
                    ['首次采集', formatDateTime(selected.first_seen_at)],
                    ['最近采集', formatDateTime(selected.last_seen_at)],
                  ]}
                />
              </section>
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">关键词</h2>
                <div className="flex flex-wrap gap-1">
                  {selected.keywords.length
                    ? selected.keywords.map((item) => <Badge key={item.keyword_master_id} variant="outline">{item.keyword}</Badge>)
                    : <span className="text-muted-foreground">-</span>}
                </div>
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
        <div key={label} className="grid grid-cols-[130px_1fr] border-b last:border-0">
          <dt className="bg-muted/60 px-3 py-2 text-muted-foreground">{label}</dt>
          <dd className="min-w-0 px-3 py-2 break-words">{value || '-'}</dd>
        </div>
      ))}
    </dl>
  );
}
