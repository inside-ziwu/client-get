'use client';

import { Search, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

const PAGE_SIZE = 20;

interface CleanCompanyRow {
  id: string;
  name_normalized: string;
  name_display: string;
  country_iso3: string | null;
  domain: string | null;
  sources: string[];
  created_at: string;
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

export function CustomerArchivePage() {
  const [keyword, setKeyword] = useState('');
  const [appliedKeyword, setAppliedKeyword] = useState('');
  const [sourceMin, setSourceMin] = useState('');
  const [sourceMax, setSourceMax] = useState('');
  const [page, setPage] = useState(1);
  const [selected, setSelected] = useState<CleanCompanyRow | null>(null);

  const companiesQuery = useQuery({
    queryKey: ['admin', 'collection', 'clean-companies', page, appliedKeyword],
    queryFn: async () =>
      (
        await adminApi.collection.listCleanCompanies({
          page,
          page_size: PAGE_SIZE,
          keyword: appliedKeyword || undefined,
        })
      ).data,
  });

  const healthQuery = useQuery({
    queryKey: ['admin', 'collection', 'cleanup-health'],
    queryFn: async () => (await adminApi.collection.getCleanupHealth()).data.data,
  });

  const rows = companiesQuery.data?.data ?? [];
  const total = companiesQuery.data?.pagination.total ?? rows.length;
  const maxPage = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const health = healthQuery.data;

  const onSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setAppliedKeyword(keyword.trim());
    setPage(1);
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">客户采集归档</h1>
          <p className="admin-page-description">Clean Archive 规范化公司视图和清洗健康状态。</p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">待清洗</div><div className="mt-1 text-2xl font-semibold">{health?.pending_count ?? '-'}</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">失败耗尽</div><div className="mt-1 text-2xl font-semibold">{health?.failed_exhausted_count ?? '-'}</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">处理速度</div><div className="mt-1 text-2xl font-semibold">{health?.processed_per_minute ?? '-'} /min</div></CardContent></Card>
        <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">最旧等待</div><div className="mt-1 text-2xl font-semibold">{health?.oldest_pending_seconds ?? '-'}</div></CardContent></Card>
      </div>

      <Card>
        <CardContent className="p-4">
          <form className="grid gap-3 lg:grid-cols-[260px_260px_1fr]" onSubmit={onSearch}>
            <div className="space-y-2">
              <Label>规范化公司</Label>
              <Input value={keyword} onChange={(event) => setKeyword(event.target.value)} />
            </div>
            <RangeField label="来源数量" min={sourceMin} max={sourceMax} onMin={setSourceMin} onMax={setSourceMax} />
            <div className="flex items-end gap-2">
              <Button type="submit">
                <Search className="h-4 w-4" />
                查询
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setKeyword('');
                  setAppliedKeyword('');
                  setSourceMin('');
                  setSourceMax('');
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
            <table className="w-full min-w-[980px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  {['规范化公司', '展示名', '国家', '域名', '来源', '创建时间', '操作'].map((label) => (
                    <th key={label} className="px-4 py-3">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b last:border-0">
                    <td className="px-4 py-3 font-medium">{row.name_normalized}</td>
                    <td className="px-4 py-3">{row.name_display}</td>
                    <td className="px-4 py-3">{row.country_iso3 ?? '-'}</td>
                    <td className="px-4 py-3 text-primary">{row.domain ?? '-'}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {row.sources.map((source) => <Badge key={source} variant="outline">{source}</Badge>)}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDateTime(row.created_at)}</td>
                    <td className="px-4 py-3">
                      <Button size="sm" variant="outline" onClick={() => setSelected(row)}>详情</Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!rows.length && <div className="py-10 text-center text-sm text-muted-foreground">暂无客户采集归档</div>}
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
        <SheetContent className="overflow-y-auto p-0">
          <div className="border-b px-5 py-4">
            <SheetTitle>{selected?.name_display ?? '详情'}</SheetTitle>
            <SheetDescription>规范化公司详情</SheetDescription>
          </div>
          <div className="space-y-3 p-5 text-sm">
            <div className="grid grid-cols-2 gap-3">
              <div><div className="text-xs text-muted-foreground">标准名</div><div>{selected?.name_normalized}</div></div>
              <div><div className="text-xs text-muted-foreground">国家</div><div>{selected?.country_iso3 ?? '-'}</div></div>
              <div><div className="text-xs text-muted-foreground">域名</div><div>{selected?.domain ?? '-'}</div></div>
              <div><div className="text-xs text-muted-foreground">创建时间</div><div>{formatDateTime(selected?.created_at)}</div></div>
            </div>
            <div>
              <div className="mb-2 text-xs text-muted-foreground">来源</div>
              <div className="flex flex-wrap gap-1">{selected?.sources.map((source) => <Badge key={source}>{source}</Badge>)}</div>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
