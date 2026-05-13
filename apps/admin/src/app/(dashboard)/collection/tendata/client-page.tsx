'use client';

import { Search, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { DatePicker } from '@/components/ui/date-picker';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

const PAGE_SIZE = 20;

interface RawCompanyRow {
  id: string;
  name: string;
  country?: string;
  domain?: string | null;
  task_id?: string | null;
  created_at: string;
  raw_payload: Record<string, unknown>;
}

type Filters = {
  keyword: string;
  country: string;
  supplier: string;
  amount_min: string;
  amount_max: string;
  year_min: string;
  year_max: string;
  created_from: string;
  created_to: string;
};

const EMPTY_FILTERS: Filters = {
  keyword: '',
  country: '',
  supplier: '',
  amount_min: '',
  amount_max: '',
  year_min: '',
  year_max: '',
  created_from: '',
  created_to: '',
};

function pick(payload: Record<string, unknown>, ...keys: string[]) {
  for (const key of keys) {
    const value = payload[key];
    if (value != null && value !== '') return String(value);
  }
  return '-';
}

function contactsFrom(row: RawCompanyRow | null) {
  const contacts = row?.raw_payload.contacts;
  return Array.isArray(contacts) ? (contacts as Record<string, unknown>[]) : [];
}

function RangeField({
  label,
  min,
  max,
  onMin,
  onMax,
}: {
  label: string;
  min: string;
  max: string;
  onMin: (value: string) => void;
  onMax: (value: string) => void;
}) {
  return (
    <div className="space-y-2">
      <Label>{label}</Label>
      <div className="grid grid-cols-2 gap-2">
        <Input placeholder="最小" value={min} onChange={(event) => onMin(event.target.value)} />
        <Input placeholder="最大" value={max} onChange={(event) => onMax(event.target.value)} />
      </div>
    </div>
  );
}

export function TendataArchivePage() {
  const [filters, setFilters] = useState<Filters>(EMPTY_FILTERS);
  const [applied, setApplied] = useState<Filters>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<RawCompanyRow | null>(null);

  const query = useQuery({
    queryKey: ['admin', 'collection', 'tendata', page, applied],
    queryFn: async () =>
      (
        await adminApi.collection.listRawCompanies('tendata', {
          page,
          page_size: PAGE_SIZE,
          keyword: applied.keyword || undefined,
          country: applied.country || undefined,
        })
      ).data,
  });

  const rows = query.data?.data ?? [];
  const total = query.data?.pagination.total ?? rows.length;
  const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const contacts = contactsFrom(selected);

  const onSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setApplied(filters);
    setPage(1);
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">Tendata 采集归档</h1>
          <p className="admin-page-description">腾道原始记录，多级筛选和联系人详情。</p>
        </div>
      </div>

      <Card>
        <CardContent className="p-4">
          <form className="grid gap-3 lg:grid-cols-4" onSubmit={onSearch}>
            <div className="space-y-2">
              <Label>关键词</Label>
              <Input value={filters.keyword} onChange={(event) => setFilters((c) => ({ ...c, keyword: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>国家</Label>
              <Input value={filters.country} onChange={(event) => setFilters((c) => ({ ...c, country: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>供应商</Label>
              <Input value={filters.supplier} onChange={(event) => setFilters((c) => ({ ...c, supplier: event.target.value }))} />
            </div>
            <RangeField
              label="贸易金额"
              min={filters.amount_min}
              max={filters.amount_max}
              onMin={(value) => setFilters((c) => ({ ...c, amount_min: value }))}
              onMax={(value) => setFilters((c) => ({ ...c, amount_max: value }))}
            />
            <RangeField
              label="成立年份"
              min={filters.year_min}
              max={filters.year_max}
              onMin={(value) => setFilters((c) => ({ ...c, year_min: value }))}
              onMax={(value) => setFilters((c) => ({ ...c, year_max: value }))}
            />
            <div className="space-y-2">
              <Label>采集开始</Label>
              <DatePicker value={filters.created_from} onChange={(value) => setFilters((c) => ({ ...c, created_from: value }))} />
            </div>
            <div className="space-y-2">
              <Label>采集结束</Label>
              <DatePicker value={filters.created_to} onChange={(value) => setFilters((c) => ({ ...c, created_to: value }))} />
            </div>
            <div className="flex items-end gap-2">
              <Button type="submit">
                <Search className="h-4 w-4" />
                查询
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setFilters(EMPTY_FILTERS);
                  setApplied(EMPTY_FILTERS);
                }}
              >
                <X className="h-4 w-4" />
                重置
              </Button>
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
                  {['公司', '国家', '域名', '贸易金额', '供应商', '成立年份', '联系人', '任务', '采集时间', '操作'].map((label) => (
                    <th key={label} className="px-3 py-2">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b last:border-0 hover:bg-muted/40">
                    <td className="max-w-[240px] px-3 py-2 font-medium">{row.name}</td>
                    <td className="px-3 py-2">{row.country ?? pick(row.raw_payload, 'country', 'buyer_country')}</td>
                    <td className="max-w-[180px] truncate px-3 py-2 text-primary">{row.domain ?? '-'}</td>
                    <td className="px-3 py-2">{pick(row.raw_payload, 'trade_amount', 'amount', 'usd_amount')}</td>
                    <td className="px-3 py-2">{pick(row.raw_payload, 'supplier', 'supplier_name')}</td>
                    <td className="px-3 py-2">{pick(row.raw_payload, 'established_year', 'year')}</td>
                    <td className="px-3 py-2">
                      <Badge variant="secondary">{contactsFrom(row).length}</Badge>
                    </td>
                    <td className="px-3 py-2 text-muted-foreground">{row.task_id ?? '-'}</td>
                    <td className="px-3 py-2 text-muted-foreground">{formatDateTime(row.created_at)}</td>
                    <td className="px-3 py-2">
                      <Button size="sm" variant="outline" onClick={() => setSelected(row)}>
                        详情
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!rows.length && <div className="py-10 text-center text-sm text-muted-foreground">暂无 Tendata 采集归档</div>}
          </div>
          <div className="flex items-center justify-between border-t px-4 py-3 text-sm">
            <span className="text-muted-foreground">共 {total} 条</span>
            <div className="flex items-center gap-2">
              <Button size="sm" variant="outline" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</Button>
              <span>第 {page} / {maxPage} 页</span>
              <Button size="sm" variant="outline" disabled={page >= maxPage} onClick={() => setPage((p) => p + 1)}>下一页</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Sheet open={Boolean(selected)} onOpenChange={(open) => !open && setSelected(null)}>
        <SheetContent className="max-w-2xl overflow-y-auto p-0 sm:w-[640px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{selected?.name ?? '详情'}</SheetTitle>
            <SheetDescription>原始 payload 与联系人子表</SheetDescription>
          </div>
          <div className="space-y-5 p-5">
            <div>
              <h3 className="mb-2 text-sm font-semibold">联系人</h3>
              <div className="rounded-md border">
                {contacts.map((contact, index) => (
                  <div key={index} className="grid grid-cols-3 gap-2 border-b p-3 text-sm last:border-0">
                    <span>{pick(contact, 'name', 'contact_name')}</span>
                    <span>{pick(contact, 'title', 'position')}</span>
                    <span>{pick(contact, 'email', 'phone')}</span>
                  </div>
                ))}
                {!contacts.length && <div className="p-4 text-sm text-muted-foreground">暂无联系人</div>}
              </div>
            </div>
            <pre className="max-h-80 overflow-auto rounded-md bg-muted p-3 text-xs">{JSON.stringify(selected?.raw_payload ?? {}, null, 2)}</pre>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
