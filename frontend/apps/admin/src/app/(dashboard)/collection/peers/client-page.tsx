'use client';

import type { LixiaoyunApiCompanyDetail, LixiaoyunRawCompanyRow } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Check, Copy, Search, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { Badge } from '@shared/ui';
import { Button } from '@shared/ui';
import { Card, CardContent } from '@shared/ui';
import { Checkbox } from '@shared/ui';
import { Input } from '@shared/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@shared/ui';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@shared/ui';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

const PAGE_SIZE_OPTIONS = [20, 50, 100, 500, 1000] as const;

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
  const [copiedEnglishName, setCopiedEnglishName] = useState(false);

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
  const detailQuery = useQuery({
    queryKey: ['admin', 'peers', 'raw-lixiaoyun', 'debug', selected?.id],
    queryFn: async () => {
      if (!selected) return null;
      return (await adminApi.collection.getLixiaoyunRawCompanyDebug(String(selected.id))).data.data;
    },
    enabled: Boolean(selected),
  });
  const detail = (detailQuery.data ?? selected) as LixiaoyunApiCompanyDetail;

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

  const copyEnglishName = async () => {
    if (!detail.entname_eng) return;
    await navigator.clipboard.writeText(detail.entname_eng);
    setCopiedEnglishName(true);
    window.setTimeout(() => setCopiedEnglishName(false), 1200);
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
                placeholder="全部搜索词"
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
            <div className="grid gap-3 lg:grid-cols-[150px_150px_auto_auto_1fr]">
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
                有官网
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
                  {['企业名称', '英文名', '员工规模', '注册资本', '成立时间', '通讯地址', '官网', '实缴资本', '年营业额', '搜索词', '采集时间', '操作'].map(
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
                      <td className="max-w-[210px] px-3 py-2 font-medium">{dash(row.entname)}</td>
                      <td className="max-w-[180px] px-3 py-2 text-muted-foreground">{dash(row.entname_eng)}</td>
                      <td className="px-3 py-2">{dash(row.scale)}</td>
                      <td className="px-3 py-2">{dash(row.reg_cap)}</td>
                      <td className="px-3 py-2">{dash(row.esdate)}</td>
                      <td className="max-w-[180px] truncate px-3 py-2 text-muted-foreground">
                        {dash(row.geo_address)}
                      </td>
                      <td className="max-w-[150px] truncate px-3 py-2 text-primary">{dash(row.official_website)}</td>
                      <td className="px-3 py-2">{dash(row.regccap)}</td>
                      <td className="px-3 py-2">{dash(row.annual_turnover)}</td>
                      <td className="px-3 py-2">
                        {row.keyword ? <Badge variant="outline">{row.keyword}</Badge> : '-'}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">{formatDateTime(row.collected_at)}</td>
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
            <SheetTitle>{selected?.entname || selected?.entname_eng || '详情'}</SheetTitle>
            <SheetDescription>励销云 API 工商数据详情</SheetDescription>
          </div>
          {selected && (
            <div className="space-y-5 p-5 text-sm">
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">工商信息</h2>
                <DescriptionGrid
                  rows={[
                    ['企业名称', dash(detail.entname)],
                    ['英文名', dash(detail.entname_eng)],
                    ['统一信用代码', dash(detail.uncid)],
                    ['官网', dash(detail.official_website)],
                    ['成立时间', dash(detail.esdate)],
                    ['经营期限', `${dash(detail.opfrom)} ~ ${dash(detail.opto)}`],
                    ['员工规模', dash(detail.scale)],
                    ['注册资本', dash(detail.reg_cap)],
                    ['实缴资本', dash(detail.regccap)],
                    ['年营业额', dash(detail.annual_turnover)],
                    ['法定代表人', dash(detail.legalperson)],
                    ['经营状态', dash(detail.entstatus)],
                    ['企业类型', dash(detail.enttype)],
                    ['登记机关', dash(detail.regorg)],
                    ['核准日期', dash(detail.apprdate)],
                    ['通讯地址', dash(detail.geo_address)],
                    ['注册地址', dash(detail.dom)],
                    ['经营场所', dash(detail.oploc)],
                    ['经营范围', dash(detail.opscope)],
                  ]}
                  englishName={detail.entname_eng}
                  copiedEnglishName={copiedEnglishName}
                  onCopyEnglishName={copyEnglishName}
                />
              </section>

              {detail.ent_introduction && (
                <section>
                  <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">企业简介</h2>
                  <p className="whitespace-pre-wrap rounded-md border p-3 text-muted-foreground">{detail.ent_introduction}</p>
                </section>
              )}

              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">行业分类</h2>
                <div className="flex flex-wrap gap-2">
                  <ClassificationBadge label="一级" value={detail.industryphy_desc} />
                  {toBadgeValues(detail.secindustry_desc).map((value) => (
                    <ClassificationBadge key={value} label="二级" value={value} />
                  ))}
                  <ClassificationBadge label="三级" value={detail.industry_l3_desc} />
                  <ClassificationBadge label="四级" value={detail.industry_l4_desc} />
                </div>
              </section>

              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">采集信息</h2>
                <DescriptionGrid
                  rows={[
                    ['励销云 PID', dash(detail.pid || detail.id)],
                    ['搜索词', dash(detail.keyword)],
                    ['采集时间', formatDateTime(detail.collected_at)],
                  ]}
                />
              </section>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function DescriptionGrid({
  rows,
  englishName,
  copiedEnglishName,
  onCopyEnglishName,
}: {
  rows: Array<[string, string]>;
  englishName?: string | null;
  copiedEnglishName?: boolean;
  onCopyEnglishName?: () => void;
}) {
  return (
    <dl className="overflow-hidden rounded-md border">
      {rows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[120px_1fr] border-b last:border-0">
          <dt className="bg-muted/60 px-3 py-2 text-muted-foreground">{label}</dt>
          <dd className="group flex min-w-0 items-center gap-2 px-3 py-2">
            <span className="min-w-0 break-words">{value || '-'}</span>
            {label === '英文名' && englishName ? (
              <Button
                type="button"
                size="icon"
                variant="ghost"
                className="h-7 w-7 opacity-0 transition-opacity group-hover:opacity-100"
                onClick={onCopyEnglishName}
                aria-label="复制英文名"
              >
                {copiedEnglishName ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              </Button>
            ) : null}
          </dd>
        </div>
      ))}
    </dl>
  );
}

function ClassificationBadge({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <Badge variant="secondary" className="gap-1">
      <span className="text-muted-foreground">{label}</span>
      {value}
    </Badge>
  );
}

function toBadgeValues(value: string[] | string | null | undefined) {
  if (!value) return [];
  if (Array.isArray(value)) return value.filter(Boolean);
  try {
    const parsed = JSON.parse(value) as unknown;
    if (Array.isArray(parsed)) return parsed.filter((item): item is string => typeof item === 'string' && Boolean(item));
  } catch {
    return [value];
  }
  return [value];
}
