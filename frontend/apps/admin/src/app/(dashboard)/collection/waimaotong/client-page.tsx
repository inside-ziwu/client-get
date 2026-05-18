'use client';

import type { WaimaotongRawCompanyRow, WaimaotongRawContactRow } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Search, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { Button } from '@shared/ui';
import { Card, CardContent } from '@shared/ui';
import { Checkbox } from '@shared/ui';
import { Input } from '@shared/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@shared/ui';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@shared/ui';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

const PAGE_SIZE_OPTIONS = [20, 50, 100] as const;

interface PageData {
  data: WaimaotongRawCompanyRow[];
  pagination: { cursor: string | null; has_more: boolean; total?: number };
}

type FilterValues = {
  q: string;
  country: string;
  source_keyword: string;
  source_competitor: string;
  industry: string;
  size: string;
  year_min: string;
  year_max: string;
  has_contacts: boolean;
};

const EMPTY_FILTERS: FilterValues = {
  q: '',
  country: '',
  source_keyword: '',
  source_competitor: '',
  industry: '',
  size: '',
  year_min: '',
  year_max: '',
  has_contacts: false,
};

const COUNTRY_OPTIONS = [
  'Bangladesh', 'Brazil', 'Cambodia', 'Canada', 'Chile', 'China', 'Colombia',
  'Egypt', 'Germany', 'Hong Kong', 'India', 'Indonesia', 'Italy', 'Japan',
  'Malaysia', 'Mexico', 'Pakistan', 'Philippines', 'Poland', 'Singapore',
  'South Korea', 'Spain', 'Taiwan', 'Thailand', 'Turkey', 'United States',
  'Vietnam',
];

function dash(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'boolean') return value ? '是' : '否';
  return String(value);
}

function emptyPage(): PageData {
  return { data: [], pagination: { cursor: null, has_more: false, total: 0 } };
}

export function WaimaotongArchivePage() {
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [jumpPage, setJumpPage] = useState('');
  const [selected, setSelected] = useState<WaimaotongRawCompanyRow | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'waimaotong', 'raw-companies', page, pageSize, appliedFilters],
    queryFn: async () => {
      try {
        return (
          await adminApi.collection.listWaimaotongRawCompanies({
            page,
            page_size: pageSize,
            q: appliedFilters.q.trim() || undefined,
            country: appliedFilters.country || undefined,
            source_keyword: appliedFilters.source_keyword || undefined,
            source_competitor: appliedFilters.source_competitor.trim() || undefined,
            industry: appliedFilters.industry.trim() || undefined,
            size: appliedFilters.size || undefined,
            year_min: appliedFilters.year_min ? Number(appliedFilters.year_min) : undefined,
            year_max: appliedFilters.year_max ? Number(appliedFilters.year_max) : undefined,
            has_contacts: appliedFilters.has_contacts || undefined,
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
    queryKey: ['admin', 'waimaotong', 'debug', selected?.id],
    queryFn: async () => {
      if (!selected) return null;
      return (await adminApi.collection.getWaimaotongRawCompanyDebug(String(selected.id))).data.data;
    },
    enabled: Boolean(selected),
  });
  const detail = (detailQuery.data ?? selected) as Record<string, unknown> | null;

  const contactsQuery = useQuery({
    queryKey: ['admin', 'waimaotong', 'contacts', selected?.id],
    queryFn: async () => {
      if (!selected) return { data: [] as WaimaotongRawContactRow[] };
      return (await adminApi.collection.listWaimaotongRawCompanyContacts(String(selected.id))).data;
    },
    enabled: Boolean(selected),
  });
  const contacts = contactsQuery.data?.data ?? [];

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
          <h1 className="admin-page-title">外贸通数据</h1>
          <p className="admin-page-description">外贸通采集的海外买家公司原始记录。</p>
        </div>
      </div>

      {/* 筛选区 */}
      <Card>
        <CardContent className="p-4">
          <form className="space-y-3" onSubmit={onSearch}>
            <div className="grid gap-3 lg:grid-cols-[220px_160px_1fr_220px_160px]">
              <Input
                placeholder="公司名 / 域名搜索"
                value={filters.q}
                onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
              />
              <Select
                value={filters.country || 'all'}
                onValueChange={(v) => setFilters((f) => ({ ...f, country: v === 'all' ? '' : v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="国家（不限）" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">国家（不限）</SelectItem>
                  {COUNTRY_OPTIONS.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Select
                value={filters.source_keyword || 'all'}
                onValueChange={(v) => setFilters((f) => ({ ...f, source_keyword: v === 'all' ? '' : v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="采集关键词（不限）" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">采集关键词（不限）</SelectItem>
                  <SelectItem value="电路">电路</SelectItem>
                  <SelectItem value="线路">线路</SelectItem>
                </SelectContent>
              </Select>
              <Input
                placeholder="来源同行搜索"
                value={filters.source_competitor}
                onChange={(e) => setFilters((f) => ({ ...f, source_competitor: e.target.value }))}
              />
              <Input
                placeholder="行业搜索"
                value={filters.industry}
                onChange={(e) => setFilters((f) => ({ ...f, industry: e.target.value }))}
              />
            </div>
            <div className="grid gap-3 lg:grid-cols-[120px_120px_160px_auto_auto_1fr]">
              <Input
                type="number"
                placeholder="成立年份(起)"
                value={filters.year_min}
                onChange={(e) => setFilters((f) => ({ ...f, year_min: e.target.value }))}
              />
              <Input
                type="number"
                placeholder="成立年份(止)"
                value={filters.year_max}
                onChange={(e) => setFilters((f) => ({ ...f, year_max: e.target.value }))}
              />
              <Select
                value={filters.size || 'all'}
                onValueChange={(v) => setFilters((f) => ({ ...f, size: v === 'all' ? '' : v }))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="员工规模（不限）" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">员工规模（不限）</SelectItem>
                  <SelectItem value="tiny">&lt; 10 人</SelectItem>
                  <SelectItem value="small">10 - 49 人</SelectItem>
                  <SelectItem value="medium">50 - 199 人</SelectItem>
                  <SelectItem value="large">&ge; 200 人</SelectItem>
                </SelectContent>
              </Select>
              <label className="flex h-9 items-center gap-2 text-sm">
                <Checkbox
                  checked={filters.has_contacts}
                  onCheckedChange={(v) => setFilters((f) => ({ ...f, has_contacts: v === true }))}
                />
                有联系人
              </label>
              <div />
              <div className="flex items-center justify-end gap-2">
                <Button type="submit" size="sm">
                  <Search className="mr-1 h-3.5 w-3.5" /> 搜索
                </Button>
                <Button type="button" variant="outline" size="sm" onClick={onReset}>
                  <X className="mr-1 h-3.5 w-3.5" /> 重置
                </Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* 列表 */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1320px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  {['公司名', '国家', '域名', '行业', '员工规模', '成立日期', '注册地址', '采集关键词', '来源同行', '联系人数', '入库时间', '操作'].map((label) => (
                    <th key={label} className="whitespace-nowrap px-3 py-2">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageData.data.length === 0 && (
                  <tr>
                    <td colSpan={12} className="py-12 text-center text-muted-foreground">
                      {query.isLoading ? '加载中...' : '暂无数据'}
                    </td>
                  </tr>
                )}
                {pageData.data.map((row) => (
                  <tr
                    key={row.id}
                    className="cursor-pointer border-b hover:bg-muted/40"
                    onClick={() => setSelected(row)}
                  >
                    <td className="max-w-[200px] truncate px-3 py-2 font-medium">{dash(row.company_name)}</td>
                    <td className="px-3 py-2">{dash(row.country)}</td>
                    <td className="max-w-[150px] truncate px-3 py-2">{dash(row.domain)}</td>
                    <td className="max-w-[140px] truncate px-3 py-2">{dash(row.industry)}</td>
                    <td className="px-3 py-2">{dash(row.employee_size)}</td>
                    <td className="px-3 py-2">{dash(row.founded_year)}</td>
                    <td className="max-w-[150px] truncate px-3 py-2">{dash(row.full_address)}</td>
                    <td className="px-3 py-2">{dash(row.source_keyword)}</td>
                    <td className="max-w-[140px] truncate px-3 py-2">{dash(row.source_competitor)}</td>
                    <td className="px-3 py-2">{row.contacts_count ?? '-'}</td>
                    <td className="whitespace-nowrap px-3 py-2">{formatDateTime(row.created_at)}</td>
                    <td className="px-3 py-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => { e.stopPropagation(); setSelected(row); }}
                      >
                        详情
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          <div className="flex items-center justify-between border-t px-4 py-3 text-sm">
            <div className="flex items-center gap-3 text-muted-foreground">
              <span>共 {total} 条</span>
              <Select
                value={String(pageSize)}
                onValueChange={(v) => { setPageSize(Number(v)); setPage(1); }}
              >
                <SelectTrigger className="h-8 w-[72px]">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((s) => (
                    <SelectItem key={s} value={String(s)}>{s} 条/页</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
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
                onClick={() => setPage((p) => p + 1)}
              >
                下一页
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 详情 Sheet */}
      <Sheet open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="max-w-2xl overflow-y-auto p-0 sm:w-[640px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{selected?.company_name || '详情'}</SheetTitle>
            <SheetDescription>外贸通采集的公司详情及联系人</SheetDescription>
          </div>
          {selected && detail && (
            <div className="space-y-5 p-5 text-sm">
              {/* 基本信息 */}
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">基本信息</h2>
                <DescriptionGrid
                  rows={[
                    ['公司名', dash(detail.company_name as string)],
                    ['国家', dash(detail.country as string)],
                    ['网站', dash(detail.website as string)],
                    ['行业', dash(detail.industry as string)],
                    ['电话', dash(detail.phone as string)],
                    ['员工规模', dash(detail.employee_size as string)],
                    ['成立年份', dash(detail.founded_year as number)],
                    ['描述', dash(detail.description as string)],
                    ['注册地址', dash(detail.full_address as string)],
                  ]}
                  linkField="网站"
                  linkValue={detail.website as string}
                />
              </section>

              {/* 采集信息 */}
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">采集信息</h2>
                <DescriptionGrid
                  rows={[
                    ['采集关键词', dash(detail.source_keyword as string)],
                    ['来源同行', dash(detail.source_competitor as string)],
                    ['来源类型', dash(detail.source_type as string)],
                    ['已验证', dash(detail.id_verified as boolean)],
                    ['API ID', dash(detail.api_company_id as string)],
                  ]}
                />
              </section>

              {/* 联系人 */}
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  联系人 ({contacts.length})
                </h2>
                {contacts.length === 0 ? (
                  <p className="rounded-md border py-8 text-center text-muted-foreground">暂无联系人数据</p>
                ) : (
                  <div className="overflow-x-auto rounded-md border">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/60">
                          <th className="px-3 py-2 text-left font-medium">姓名</th>
                          <th className="px-3 py-2 text-left font-medium">职位</th>
                          <th className="px-3 py-2 text-left font-medium">部门</th>
                          <th className="px-3 py-2 text-left font-medium">邮箱</th>
                          <th className="px-3 py-2 text-left font-medium">邮箱状态</th>
                          <th className="px-3 py-2 text-left font-medium">电话</th>
                          <th className="px-3 py-2 text-left font-medium">LinkedIn</th>
                          <th className="px-3 py-2 text-left font-medium">来源</th>
                        </tr>
                      </thead>
                      <tbody>
                        {contacts.map((c) => (
                          <tr key={c.id} className="border-b last:border-0">
                            <td className="px-3 py-2">{dash(c.name)}</td>
                            <td className="px-3 py-2">{dash(c.position)}</td>
                            <td className="px-3 py-2">{dash(c.department)}</td>
                            <td className="px-3 py-2">{dash(c.email)}</td>
                            <td className="px-3 py-2">{dash(c.email_status)}</td>
                            <td className="px-3 py-2">{dash(c.phone)}</td>
                            <td className="max-w-[120px] truncate px-3 py-2">{dash(c.linkedin)}</td>
                            <td className="px-3 py-2">{dash(c.source)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
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
  linkField,
  linkValue,
}: {
  rows: Array<[string, string]>;
  linkField?: string;
  linkValue?: string | null;
}) {
  return (
    <dl className="overflow-hidden rounded-md border">
      {rows.map(([label, value]) => (
        <div key={label} className="grid grid-cols-[120px_1fr] border-b last:border-0">
          <dt className="bg-muted/60 px-3 py-2 text-muted-foreground">{label}</dt>
          <dd className="min-w-0 break-words px-3 py-2">
            {label === linkField && linkValue ? (
              <a
                href={linkValue.startsWith('http') ? linkValue : `https://${linkValue}`}
                target="_blank"
                rel="noopener noreferrer"
                className="text-primary underline"
              >
                {value}
              </a>
            ) : (
              value || '-'
            )}
          </dd>
        </div>
      ))}
    </dl>
  );
}
