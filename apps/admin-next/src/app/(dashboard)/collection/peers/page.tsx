'use client';

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

interface LixiaoyunRow {
  id: string;
  name: string;
  domain?: string | null;
  task_id?: string | null;
  created_at: string;
  raw_payload: unknown;
}

interface PageData {
  data: LixiaoyunRow[];
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

function safePayload(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {};
}

function pick(payload: unknown, ...keys: string[]): string {
  const source = safePayload(payload);
  for (const key of keys) {
    const value = source[key];
    if (value != null && value !== '') {
      return String(value);
    }
  }
  return '-';
}

function emptyPage(): PageData {
  return { data: [], pagination: { cursor: null, has_more: false, total: 0 } };
}

function contactsFrom(row: LixiaoyunRow | null) {
  const contacts = safePayload(row?.raw_payload).contacts;
  return Array.isArray(contacts) ? (contacts as Record<string, unknown>[]) : [];
}

export default function PeersDataPage() {
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [appliedName, setAppliedName] = useState<string | undefined>();
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<LixiaoyunRow | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'peers', page, appliedName],
    queryFn: async () => {
      try {
        return (
          await adminApi.collection.listRawCompanies('lixiaoyun', {
            page,
            page_size: PAGE_SIZE,
            keyword: appliedName,
          })
        ).data as PageData;
      } catch {
        return emptyPage();
      }
    },
  });

  const pageData = query.data ?? emptyPage();
  const total = pageData.pagination.total ?? pageData.data.length;
  const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const payload = safePayload(selected?.raw_payload);
  const contacts = contactsFrom(selected);

  const onSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAppliedName(filters.name.trim() || undefined);
    setPage(1);
  };

  const onReset = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedName(undefined);
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
                  const rowPayload = safePayload(row.raw_payload);
                  const contactCount = Number(pick(rowPayload, 'contacts_count', 'contact_num'));
                  const count = Number.isNaN(contactCount) ? 0 : contactCount;
                  const domain = row.domain ?? pick(rowPayload, 'website', 'domain');
                  const keyword = pick(rowPayload, 'keyword', 'search_keyword', 'query');
                  return (
                    <tr key={row.id} className="cursor-pointer border-b hover:bg-muted/40" onClick={() => setSelected(row)}>
                      <td className="max-w-[210px] px-3 py-2 font-medium">
                        {pick(rowPayload, 'name_cn', 'name_zh') || row.name}
                      </td>
                      <td className="max-w-[180px] px-3 py-2 text-muted-foreground">
                        {pick(rowPayload, 'name_en', 'name_english')}
                      </td>
                      <td className="px-3 py-2">{pick(rowPayload, 'employee_scale', 'staff_num')}</td>
                      <td className="px-3 py-2">{pick(rowPayload, 'reg_capital', 'registered_capital')}</td>
                      <td className="px-3 py-2">{pick(rowPayload, 'established_date', 'found_date', 'reg_date')}</td>
                      <td className="max-w-[180px] truncate px-3 py-2 text-muted-foreground">
                        {pick(rowPayload, 'address', 'reg_address', 'location')}
                      </td>
                      <td className="max-w-[150px] truncate px-3 py-2 text-primary">{domain !== '-' ? domain : '-'}</td>
                      <td className="px-3 py-2">
                        <Badge variant={count > 0 ? 'secondary' : 'outline'}>{count}</Badge>
                      </td>
                      <td className="px-3 py-2">{keyword !== '-' ? <Badge variant="outline">{keyword}</Badge> : '-'}</td>
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
            <span className="text-muted-foreground">共 {total} 条</span>
            <div className="flex items-center gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((current) => current - 1)}>
                上一页
              </Button>
              <span>
                第 {page} / {maxPage} 页
              </span>
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
            <SheetTitle>{selected ? pick(selected.raw_payload, 'name_cn', 'name_zh') || selected.name : '详情'}</SheetTitle>
            <SheetDescription>原始同行公司记录详情</SheetDescription>
          </div>
          {selected && (
            <div className="space-y-5 p-5 text-sm">
              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">基本信息</h2>
                <DescriptionGrid
                  rows={[
                    ['中文名', pick(payload, 'name_cn', 'name_zh') || selected.name],
                    ['英文名', pick(payload, 'name_en', 'name_english')],
                    ['网址', selected.domain ?? pick(payload, 'website', 'domain')],
                    ['成立时间', pick(payload, 'established_date', 'found_date', 'reg_date')],
                    ['员工规模', pick(payload, 'employee_scale', 'staff_num')],
                    ['注册资金', pick(payload, 'reg_capital', 'registered_capital')],
                    ['实缴资金', pick(payload, 'paid_capital', 'actual_capital')],
                    ['公司法人', pick(payload, 'legal_person', 'legal_representative')],
                    ['统一信用代码', pick(payload, 'credit_code', 'unified_credit_code')],
                    ['注册地址', pick(payload, 'address', 'reg_address')],
                    ['通讯地址', pick(payload, 'contact_address', 'mailing_address')],
                  ]}
                />
              </section>

              <section>
                <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">采集信息</h2>
                <DescriptionGrid
                  rows={[
                    ['励销云 ID', selected.id],
                    ['关键词', pick(payload, 'keyword', 'search_keyword')],
                    ['采集时间', formatDateTime(selected.created_at)],
                  ]}
                />
              </section>

              {contacts.length > 0 && (
                <section>
                  <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
                    联系人（{contacts.length}）
                  </h2>
                  <div className="overflow-x-auto rounded-md border">
                    <table className="w-full text-xs">
                      <thead className="bg-muted/70 text-left text-muted-foreground">
                        <tr>
                          {['姓名', '职位', '电话', '邮箱'].map((label) => (
                            <th key={label} className="px-3 py-2">
                              {label}
                            </th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {contacts.map((contact, index) => (
                          <tr key={index} className="border-t">
                            <td className="px-3 py-2">{String(contact.name ?? '-')}</td>
                            <td className="px-3 py-2 text-muted-foreground">
                              {String(contact.title ?? contact.position ?? '-')}
                            </td>
                            <td className="px-3 py-2 font-mono">{String(contact.phone ?? contact.mobile ?? '-')}</td>
                            <td className="px-3 py-2 text-muted-foreground">{String(contact.email ?? '-')}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              )}
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
