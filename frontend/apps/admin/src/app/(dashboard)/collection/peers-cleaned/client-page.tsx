'use client';

import type { LixiaoyunCleanCompanyDetail, LixiaoyunCleanCompanyRow } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Search, X } from 'lucide-react';
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

type FilterValues = {
  name: string;
  keyword_filter: string;
  industry_tag: string;
  found_date_start: string;
  found_date_end: string;
  reg_capital: string;
  employee_scale: string;
  has_name_en: boolean;
  has_domain: boolean;
};

const EMPTY_FILTERS: FilterValues = {
  name: '',
  keyword_filter: '',
  industry_tag: '',
  found_date_start: '',
  found_date_end: '',
  reg_capital: '',
  employee_scale: '',
  has_name_en: false,
  has_domain: false,
};

function dash(value: string | number | null | undefined) {
  return value === null || value === undefined || value === '' ? '-' : String(value);
}

function emptyPage() {
  return { data: [] as LixiaoyunCleanCompanyRow[], pagination: { cursor: null, has_more: false, total: 0 } };
}

export function PeersCleanedPage() {
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [jumpPage, setJumpPage] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'lixiaoyun-clean-companies', page, pageSize, appliedFilters],
    queryFn: async () => {
      try {
        return (
          await adminApi.collection.listLixiaoyunCleanCompanies({
            page,
            page_size: pageSize,
            keyword: appliedFilters.name.trim() || undefined,
            keyword_filter: appliedFilters.keyword_filter.trim() || undefined,
            industry_tag: appliedFilters.industry_tag.trim() || undefined,
            found_date_start: appliedFilters.found_date_start || undefined,
            found_date_end: appliedFilters.found_date_end || undefined,
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
          <p className="admin-page-description">按 pid 去重聚合后的清洗公司池。</p>
        </div>
      </div>

      <Card>
        <CardContent className="p-4">
          <form className="space-y-3" onSubmit={onSearch}>
            <div className="grid gap-3 lg:grid-cols-[220px_160px_160px_160px_160px_1fr]">
              <Input
                placeholder="公司名（中文/英文/官网/pid）"
                value={filters.name}
                onChange={(event) => setFilters((current) => ({ ...current, name: event.target.value }))}
              />
              <Input
                placeholder="搜索词筛选"
                value={filters.keyword_filter}
                onChange={(event) => setFilters((current) => ({ ...current, keyword_filter: event.target.value }))}
              />
              <Input
                placeholder="标签（精确匹配）"
                value={filters.industry_tag}
                onChange={(event) => setFilters((current) => ({ ...current, industry_tag: event.target.value }))}
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
                  onCheckedChange={(checked) => setFilters((current) => ({ ...current, has_name_en: checked === true }))}
                />
                有英文名
              </label>
              <label className="flex h-9 items-center gap-2 text-sm">
                <Checkbox
                  checked={filters.has_domain}
                  onCheckedChange={(checked) => setFilters((current) => ({ ...current, has_domain: checked === true }))}
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
            <table className="w-full min-w-[1380px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  {['中文名', '英文名', '员工规模', '注册资金', '成立时间', '注册地址', '官网', '标签', '搜索词', '创建时间', '操作'].map((label) => (
                    <th key={label} className="px-3 py-2">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageData.data.map((row) => (
                  <tr key={row.id} className="cursor-pointer border-b hover:bg-muted/40" onClick={() => setSelectedId(Number(row.id))}>
                    <td className="max-w-[210px] px-3 py-2 font-medium">{dash(row.entname)}</td>
                    <td className="max-w-[180px] px-3 py-2 text-muted-foreground">{dash(row.entname_eng)}</td>
                    <td className="px-3 py-2">{dash(row.scale)}</td>
                    <td className="px-3 py-2">{dash(row.reg_cap)}</td>
                    <td className="px-3 py-2">{dash(row.esdate)}</td>
                    <td className="max-w-[180px] truncate px-3 py-2 text-muted-foreground">{dash(row.geo_address)}</td>
                    <td className="max-w-[150px] truncate px-3 py-2 text-primary">{dash(row.official_website)}</td>
                    <td className="px-3 py-2">
                      {row.industry_tag ? <Badge variant="secondary">{row.industry_tag}</Badge> : '-'}
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {row.keyword_master.slice(0, 3).map((item) => (
                          <Badge key={item.keyword_master_id} variant="outline">{item.keyword}</Badge>
                        ))}
                        {row.keyword_master.length > 3 ? <Badge variant="secondary">+{row.keyword_master.length - 3}</Badge> : null}
                      </div>
                    </td>
                    <td className="px-3 py-2 text-xs text-muted-foreground">{formatDateTime(row.created_at)}</td>
                    <td className="px-3 py-2">
                      <Button size="sm" variant="outline" onClick={(e) => { e.stopPropagation(); setSelectedId(Number(row.id)); }}>详情</Button>
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
            <div className="flex items-center gap-3">
              <span className="text-muted-foreground">共 {total} 条</span>
              <Select
                value={String(pageSize)}
                onValueChange={(v) => { setPageSize(Number(v)); setPage(1); }}
              >
                <SelectTrigger className="h-8 w-[120px]">
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

      <Sheet open={selectedId !== null} onOpenChange={(open) => !open && setSelectedId(null)}>
        <SheetContent className="max-w-2xl overflow-y-auto p-0 sm:w-[620px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>清洗公司详情</SheetTitle>
            <SheetDescription>清洗去重后的公司记录详情</SheetDescription>
          </div>
          {selectedId !== null && <CleanDetailContent companyId={selectedId} />}
        </SheetContent>
      </Sheet>
    </div>
  );
}

function CleanDetailContent({ companyId }: { companyId: number }) {
  const detailQuery = useQuery({
    queryKey: ['admin', 'lixiaoyun-clean-company-detail', companyId],
    queryFn: async () => {
      const res = await adminApi.collection.getLixiaoyunCleanCompanyDetail(companyId);
      return res.data.data as LixiaoyunCleanCompanyDetail;
    },
  });

  if (detailQuery.isLoading) return <div className="p-5 text-sm text-muted-foreground">加载中...</div>;
  if (detailQuery.error || !detailQuery.data) return <div className="p-5 text-sm text-destructive">加载失败</div>;

  const d = detailQuery.data;

  return (
    <div className="space-y-5 p-5 text-sm">
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">基本信息</h2>
        <DescriptionGrid
          rows={[
            ['中文名', dash(d.entname)],
            ['英文名', dash(d.entname_eng)],
            ['PID', dash(d.pid)],
            ['官网', dash(d.official_website)],
            ['成立日期', dash(d.esdate)],
            ['注册资金', dash(d.reg_cap)],
            ['实缴资金', dash(d.regccap)],
            ['员工规模', dash(d.scale)],
            ['年营业额', dash(d.annual_turnover)],
            ['法人', dash(d.legalperson)],
            ['标签', dash(d.industry_tag)],
          ]}
        />
      </section>
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">工商信息</h2>
        <DescriptionGrid
          rows={[
            ['统一信用代码', dash(d.uncid)],
            ['经营状态', dash(d.entstatus)],
            ['企业类型', dash(d.enttype)],
            ['注册号', dash(d.regno)],
            ['组织机构代码', dash(d.organizational_code)],
            ['登记机关', dash(d.regorg)],
            ['注册地址', dash(d.dom)],
            ['经营地址', dash(d.oploc)],
            ['地理地址', dash(d.geo_address)],
            ['行业门类', dash(d.industryphy_desc)],
            ['经营范围', dash(d.opscope)],
          ]}
        />
      </section>
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">搜索词</h2>
        <div className="flex flex-wrap gap-1">
          {d.keyword_master.length
            ? d.keyword_master.map((item) => <Badge key={item.keyword_master_id} variant="outline">{item.keyword}</Badge>)
            : <span className="text-muted-foreground">-</span>}
        </div>
      </section>
      <section>
        <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">时间</h2>
        <DescriptionGrid
          rows={[
            ['创建时间', formatDateTime(d.created_at) || '-'],
            ['更新时间', formatDateTime(d.updated_at) || '-'],
          ]}
        />
      </section>
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
