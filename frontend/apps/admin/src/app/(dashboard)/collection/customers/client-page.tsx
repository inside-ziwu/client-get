'use client';

import type { WmtCleanCompanyRow, WmtCleanCompanyDetail, WmtCleanContactRow } from '@shared/api';
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

const PAGE_SIZE_OPTIONS = [20, 50, 100] as const;

type FilterValues = {
  q: string;
  country: string;
  industry: string;
  size: string;
  year_min: string;
  year_max: string;
  has_contacts: boolean;
};

const EMPTY_FILTERS: FilterValues = {
  q: '',
  country: '',
  industry: '',
  size: '',
  year_min: '',
  year_max: '',
  has_contacts: false,
};

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800',
  B: 'bg-blue-100 text-blue-800',
  C: 'bg-orange-100 text-orange-800',
  X: 'bg-red-100 text-red-800',
};

function dash(value: string | number | boolean | null | undefined) {
  if (value === null || value === undefined || value === '') return '-';
  if (typeof value === 'boolean') return value ? '是' : '否';
  return String(value);
}

interface PageData {
  data: WmtCleanCompanyRow[];
  pagination: { cursor: string | null; has_more: boolean; total?: number };
}

function emptyPage(): PageData {
  return { data: [], pagination: { cursor: null, has_more: false, total: 0 } };
}

export function CustomerArchivePage() {
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [jumpPage, setJumpPage] = useState('');
  const [selectedId, setSelectedId] = useState<number | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'wmt-clean-companies', page, pageSize, appliedFilters],
    queryFn: async () => {
      try {
        return (
          await adminApi.collection.listWmtCleanCompanies({
            page,
            page_size: pageSize,
            q: appliedFilters.q.trim() || undefined,
            country: appliedFilters.country.trim() || undefined,
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
    queryKey: ['admin', 'wmt-clean-company', selectedId],
    queryFn: async () => {
      if (!selectedId) return null;
      return (await adminApi.collection.getWmtCleanCompany(selectedId)).data.data;
    },
    enabled: selectedId !== null,
  });
  const detail = detailQuery.data as WmtCleanCompanyDetail | null;

  const contactsQuery = useQuery({
    queryKey: ['admin', 'wmt-clean-company-contacts', selectedId],
    queryFn: async () => {
      if (!selectedId) return { data: [] as WmtCleanContactRow[] };
      return (await adminApi.collection.listWmtCleanCompanyContacts(selectedId)).data;
    },
    enabled: selectedId !== null,
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

  const showAiSection = detail && (detail.grade != null || detail.score != null);
  const showTradeSection = detail && (detail.has_trade_data === true || detail.trade_summary != null);

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">外贸通客户数据</h1>
          <p className="admin-page-description">waimaotong_clean_companies 清洗后的公司数据及联系人。</p>
        </div>
      </div>

      {/* 筛选区 */}
      <Card>
        <CardContent className="p-4">
          <form className="space-y-3" onSubmit={onSearch}>
            <div className="grid gap-3 lg:grid-cols-[1fr_160px_160px_160px]">
              <Input
                placeholder="公司名 / 域名搜索"
                value={filters.q}
                onChange={(e) => setFilters((f) => ({ ...f, q: e.target.value }))}
              />
              <Input
                placeholder="国家"
                value={filters.country}
                onChange={(e) => setFilters((f) => ({ ...f, country: e.target.value }))}
              />
              <Input
                placeholder="行业"
                value={filters.industry}
                onChange={(e) => setFilters((f) => ({ ...f, industry: e.target.value }))}
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
            </div>
            <div className="grid gap-3 lg:grid-cols-[120px_120px_auto_1fr]">
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
              <label className="flex h-9 items-center gap-2 text-sm">
                <Checkbox
                  checked={filters.has_contacts}
                  onCheckedChange={(v) => setFilters((f) => ({ ...f, has_contacts: v === true }))}
                />
                有联系人
              </label>
              <div className="flex items-center justify-end gap-2">
                <Button type="submit" size="sm">
                  <Search className="mr-1 h-3.5 w-3.5" /> 查询
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
            <table className="w-full min-w-[1400px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  {[
                    '公司名', '国家', '域名', '行业', '员工规模', '成立',
                    '电话', '评级', '评分', '细分行业', '联系人数', '操作', '入库时间',
                  ].map((label) => (
                    <th key={label} className="whitespace-nowrap px-3 py-2">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {pageData.data.length === 0 && (
                  <tr>
                    <td colSpan={13} className="py-12 text-center text-muted-foreground">
                      {query.isLoading ? '加载中...' : '暂无数据'}
                    </td>
                  </tr>
                )}
                {pageData.data.map((row) => (
                  <tr key={row.id} className="border-b hover:bg-muted/40">
                    <td className="max-w-[180px] truncate px-3 py-2">
                      <button
                        className="text-left font-medium text-primary hover:underline"
                        onClick={() => setSelectedId(Number(row.id))}
                      >
                        {dash(row.company_name)}
                      </button>
                    </td>
                    <td className="px-3 py-2">{dash(row.country)}</td>
                    <td className="max-w-[150px] truncate px-3 py-2">{dash(row.domain)}</td>
                    <td className="max-w-[140px] truncate px-3 py-2">{dash(row.industry)}</td>
                    <td className="px-3 py-2">{dash(row.employee_size)}</td>
                    <td className="px-3 py-2">{dash(row.founded_year)}</td>
                    <td className="px-3 py-2">{dash(row.phone)}</td>
                    <td className="px-3 py-2">
                      {row.grade ? (
                        <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${GRADE_COLORS[row.grade] ?? ''}`}>
                          {row.grade}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-3 py-2">{row.score != null ? row.score : '-'}</td>
                    <td className="max-w-[120px] truncate px-3 py-2">{dash(row.sub_industry)}</td>
                    <td className="px-3 py-2">{row.contacts_count ?? '-'}</td>
                    <td className="px-3 py-2">
                      <Button variant="link" size="sm" className="h-auto p-0" onClick={() => setSelectedId(Number(row.id))}>
                        查看详情
                      </Button>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">{formatDateTime(row.created_at)}</td>
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
                <SelectTrigger className="h-8 w-[100px]">
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
      <Sheet open={selectedId !== null} onOpenChange={(open) => !open && setSelectedId(null)}>
        <SheetContent className="max-w-2xl overflow-y-auto p-0 sm:w-[640px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{detail?.company_name || '详情'}</SheetTitle>
            <SheetDescription>外贸通清洗公司详情</SheetDescription>
          </div>
          {detail && (
            <div className="space-y-5 p-5 text-sm">
              {/* 分组 1：基本信息 */}
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">基本信息</h2>
                <DescriptionGrid
                  rows={[
                    ['公司名', dash(detail.company_name)],
                    ['英文名', dash(detail.english_name)],
                    ['国家', dash(detail.country)],
                    ['域名', dash(detail.domain)],
                    ['网站', dash(detail.website)],
                    ['行业', dash(detail.industry)],
                    ['电话', dash(detail.phone)],
                    ['员工规模', dash(detail.employee_size)],
                    ['公司规模', dash(detail.company_size)],
                    ['成立年份', dash(detail.founded_year)],
                    ['地址', dash(detail.full_address)],
                    ['描述', dash(detail.description)],
                  ]}
                  linkField="网站"
                  linkValue={detail.website}
                />
              </section>

              {/* 分组 2：AI 评估 */}
              {showAiSection && (
                <section>
                  <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">AI 评估</h2>
                  <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <div className="text-xs text-muted-foreground">评级</div>
                        <div className="mt-1">
                          {detail.grade ? (
                            <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${GRADE_COLORS[detail.grade] ?? ''}`}>
                              {detail.grade}
                            </span>
                          ) : '-'}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-muted-foreground">评分</div>
                        <div className="mt-1 font-medium">{detail.score != null ? detail.score : '-'}</div>
                      </div>
                    </div>

                    {detail.score_details && Array.isArray(detail.score_details) && detail.score_details.length > 0 && (
                      <div>
                        <div className="mb-1 text-xs text-muted-foreground">评分明细</div>
                        <div className="space-y-2 rounded-md border p-3">
                          {detail.score_details.map((d: any, i: number) => (
                            <div key={i}>
                              <div className="flex items-center justify-between text-xs">
                                <span>{d.dimension ?? `维度 ${i + 1}`}</span>
                                <span>{d.score ?? 0} / {d.max_possible ?? 100}</span>
                              </div>
                              <div className="mt-1 h-2 overflow-hidden rounded-full bg-muted">
                                <div
                                  className="h-full rounded-full bg-primary"
                                  style={{ width: `${Math.min(100, ((d.score ?? 0) / (d.max_possible || 100)) * 100)}%` }}
                                />
                              </div>
                              {d.explanation && <div className="mt-0.5 text-xs text-muted-foreground">{d.explanation}</div>}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <DescriptionGrid
                      rows={[
                        ['细分行业', dash(detail.sub_industry)],
                        ['公司类型分析', dash(detail.company_type_analysis)],
                        ['邮箱优先级', dash(detail.email_priority)],
                        ['销售策略', dash(detail.sales_approach)],
                      ]}
                    />

                    {detail.product_tags && detail.product_tags.length > 0 && (
                      <div>
                        <div className="mb-1 text-xs text-muted-foreground">产品标签</div>
                        <div className="flex flex-wrap gap-1">
                          {detail.product_tags.map((t: string) => <Badge key={t} variant="secondary">{t}</Badge>)}
                        </div>
                      </div>
                    )}

                    <TagList label="匹配原因" items={detail.match_reasons} />
                    <TagList label="潜在需求" items={detail.potential_needs} />
                    <TagList label="推荐产品" items={detail.recommended_products} />
                    <TagList label="风险因素" items={detail.risk_factors} />
                    <TagList label="主营业务" items={detail.main_business} />
                  </div>
                </section>
              )}

              {/* 分组 3：贸易数据 */}
              {showTradeSection && (
                <section>
                  <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">贸易数据</h2>
                  <DescriptionGrid
                    rows={[
                      ['有贸易数据', dash(detail.has_trade_data)],
                      ['3年贸易额(USD)', detail.trade_amount_3y_usd != null ? Number(detail.trade_amount_3y_usd).toLocaleString() : '-'],
                      ['贸易次数', dash(detail.trade_count)],
                    ]}
                  />
                  {detail.trade_summary && (
                    <div className="mt-3">
                      <div className="mb-1 text-xs text-muted-foreground">贸易摘要</div>
                      <pre className="max-h-48 overflow-auto rounded-md border bg-muted/40 p-3 text-xs">
                        {JSON.stringify(detail.trade_summary, null, 2)}
                      </pre>
                    </div>
                  )}
                </section>
              )}

              {/* 分组 4：联系人 */}
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                  联系人 ({contactsQuery.isLoading ? '...' : contacts.length})
                </h2>
                {contactsQuery.isLoading ? (
                  <p className="rounded-md border py-8 text-center text-muted-foreground">加载中...</p>
                ) : contacts.length === 0 ? (
                  <p className="rounded-md border py-8 text-center text-muted-foreground">暂无联系人数据</p>
                ) : (
                  <div className="overflow-x-auto rounded-md border">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/60">
                          {['姓名', '职位', '部门', '邮箱', '邮箱状态', '电话', 'LinkedIn', '来源'].map((h) => (
                            <th key={h} className="px-3 py-2 text-left font-medium">{h}</th>
                          ))}
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

              {/* 分组 5：数据来源与元数据 */}
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">数据来源与元数据</h2>
                {detail.data_source_tags && detail.data_source_tags.length > 0 && (
                  <div className="mb-3">
                    <div className="mb-1 text-xs text-muted-foreground">数据源标签</div>
                    <div className="flex flex-wrap gap-1">
                      {detail.data_source_tags.map((t: string) => <Badge key={t} variant="outline">{t}</Badge>)}
                    </div>
                  </div>
                )}
                <DescriptionGrid
                  rows={[
                    ['Source ID', dash(detail.source_id)],
                    ['sys_company_id', dash(detail.sys_company_id)],
                    ['详情状态', dash(detail.detail_status)],
                    ['联系人状态', dash(detail.contacts_status)],
                    ['贸易状态', dash(detail.trade_status)],
                    ['创建时间', detail.created_at ? formatDateTime(detail.created_at) : '-'],
                    ['更新时间', detail.updated_at ? formatDateTime(detail.updated_at) : '-'],
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

function TagList({ label, items }: { label: string; items: unknown[] | null }) {
  if (!items || !Array.isArray(items) || items.length === 0) return null;
  return (
    <div>
      <div className="mb-1 text-xs text-muted-foreground">{label}</div>
      <ul className="list-inside list-disc space-y-0.5 text-sm">
        {items.map((item, i) => <li key={i}>{typeof item === 'string' ? item : JSON.stringify(item)}</li>)}
      </ul>
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
