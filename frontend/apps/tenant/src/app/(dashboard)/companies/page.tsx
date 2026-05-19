'use client';

import type { Company, CompanyListFilters, Group } from '@shared/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Search, X } from 'lucide-react';
import { FormEvent, useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogTitle,
  Badge, Button, Card, CardContent, Checkbox, Dialog, DialogContent,
  DialogTitle, Input, MultiSelect, RatingTag,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Sheet, SheetContent, SheetTitle,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { PageHeader } from '@/components/pages/page-kit';
import CompanyDetail from './company-detail';

const PAGE_SIZE_OPTIONS = [20, 50, 100] as const;

type FilterValues = {
  keyword: string;
  countries: string[];
  sub_industries: string[];
  product_tags: string[];
  grade: string;
  trade_amount_min: string;
  trade_amount_max: string;
  trade_count_min: string;
  trade_count_max: string;
  contact_count_min: string;
  contact_count_max: string;
  founded_year_from: string;
  founded_year_to: string;
};

const EMPTY_FILTERS: FilterValues = {
  keyword: '',
  countries: [],
  sub_industries: [],
  product_tags: [],
  grade: '',
  trade_amount_min: '',
  trade_amount_max: '',
  trade_count_min: '',
  trade_count_max: '',
  contact_count_min: '',
  contact_count_max: '',
  founded_year_from: '',
  founded_year_to: '',
};

function dash(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '-';
  return String(value);
}

function buildParams(f: FilterValues, page: number, pageSize: number): CompanyListFilters {
  const p: CompanyListFilters = { page, page_size: pageSize };
  if (f.keyword.trim()) p.keyword = f.keyword.trim();
  if (f.grade) p.grade = f.grade;
  if (f.countries.length) p['countries[]'] = f.countries;
  if (f.sub_industries.length) p['sub_industries[]'] = f.sub_industries;
  if (f.product_tags.length) p['product_tags[]'] = f.product_tags;
  if (f.trade_amount_min) p.trade_amount_min = Number(f.trade_amount_min);
  if (f.trade_amount_max) p.trade_amount_max = Number(f.trade_amount_max);
  if (f.trade_count_min) p.trade_count_min = Number(f.trade_count_min);
  if (f.trade_count_max) p.trade_count_max = Number(f.trade_count_max);
  if (f.contact_count_min) p.contact_count_min = Number(f.contact_count_min);
  if (f.contact_count_max) p.contact_count_max = Number(f.contact_count_max);
  if (f.founded_year_from) p.founded_year_from = Number(f.founded_year_from);
  if (f.founded_year_to) p.founded_year_to = Number(f.founded_year_to);
  return p;
}

export default function CompaniesPage() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [jumpPage, setJumpPage] = useState('');

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [detailId, setDetailId] = useState<string | null>(null);
  const [groupTarget, setGroupTarget] = useState<{ tcIds: string[]; label: string } | null>(null);
  const [blacklistTarget, setBlacklistTarget] = useState<{ tcId: string; name: string } | null>(null);

  const filtersQuery = useQuery({
    queryKey: ['tenant', 'companies', 'filters'],
    queryFn: async () => (await tenantApi.companies.filters()).data.data,
  });

  const listQuery = useQuery({
    queryKey: ['tenant', 'companies', 'list', page, pageSize, appliedFilters],
    queryFn: async () => (await tenantApi.companies.list(buildParams(appliedFilters, page, pageSize))).data,
  });

  const items: Company[] = listQuery.data?.data ?? [];
  const total = listQuery.data?.pagination?.total ?? 0;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  const detailQuery = useQuery({
    queryKey: ['tenant', 'companies', 'detail', detailId],
    queryFn: async () => detailId ? (await tenantApi.companies.detail(detailId)).data.data : null,
    enabled: detailId !== null,
  });

  const onSearch = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setAppliedFilters(filters);
    setPage(1);
    setSelectedIds(new Set());
  };

  const onReset = () => {
    setFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
    setSelectedIds(new Set());
  };

  const toggleSelect = (tcId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(tcId)) next.delete(tcId); else next.add(tcId);
      return next;
    });
  };

  const allSelected = items.length > 0 && items.every((c) => selectedIds.has(c.tc_id));
  const someSelected = items.some((c) => selectedIds.has(c.tc_id)) && !allSelected;

  const toggleAll = () => {
    if (allSelected) {
      setSelectedIds(new Set());
    } else {
      setSelectedIds(new Set(items.map((c) => c.tc_id)));
    }
  };

  const invalidateList = () => queryClient.invalidateQueries({ queryKey: ['tenant', 'companies'] });

  const fo = filtersQuery.data;
  const countryOpts = (fo?.countries ?? []).map((v: string) => ({ label: v, value: v }));
  const subIndustryOpts = (fo?.sub_industries ?? []).map((v: string) => ({ label: v, value: v }));
  const productTagOpts = (fo?.product_tags ?? []).map((v: string) => ({ label: v, value: v }));
  const gradeOpts = (fo?.grades ?? []) as string[];

  return (
    <div className="tenant-page space-y-4">
      <PageHeader title="公司列表" description="筛选、查看和处理租户公司数据" />

      {/* 筛选面板 */}
      <Card>
        <CardContent className="p-4">
          <form className="space-y-3" onSubmit={onSearch}>
            <div className="grid gap-3 lg:grid-cols-5">
              <Input
                placeholder="公司名 / 域名搜索"
                value={filters.keyword}
                onChange={(e) => setFilters((f) => ({ ...f, keyword: e.target.value }))}
              />
              <MultiSelect
                value={filters.countries}
                onChange={(v) => setFilters((f) => ({ ...f, countries: v }))}
                options={countryOpts}
                placeholder="国家"
              />
              <MultiSelect
                value={filters.sub_industries}
                onChange={(v) => setFilters((f) => ({ ...f, sub_industries: v }))}
                options={subIndustryOpts}
                placeholder="细分行业"
              />
              <MultiSelect
                value={filters.product_tags}
                onChange={(v) => setFilters((f) => ({ ...f, product_tags: v }))}
                options={productTagOpts}
                placeholder="产品标签"
              />
              <Select
                value={filters.grade || 'all'}
                onValueChange={(v) => setFilters((f) => ({ ...f, grade: v === 'all' ? '' : v }))}
              >
                <SelectTrigger><SelectValue placeholder="评级（不限）" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">评级（不限）</SelectItem>
                  {gradeOpts.map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="grid gap-3 lg:grid-cols-[1fr_1fr_1fr_1fr_auto]">
              <div className="flex items-center gap-1">
                <Input type="number" placeholder="进口额(起)" value={filters.trade_amount_min}
                  onChange={(e) => setFilters((f) => ({ ...f, trade_amount_min: e.target.value }))} />
                <span className="text-muted-foreground">-</span>
                <Input type="number" placeholder="进口额(止)" value={filters.trade_amount_max}
                  onChange={(e) => setFilters((f) => ({ ...f, trade_amount_max: e.target.value }))} />
              </div>
              <div className="flex items-center gap-1">
                <Input type="number" placeholder="进口次数(起)" value={filters.trade_count_min}
                  onChange={(e) => setFilters((f) => ({ ...f, trade_count_min: e.target.value }))} />
                <span className="text-muted-foreground">-</span>
                <Input type="number" placeholder="进口次数(止)" value={filters.trade_count_max}
                  onChange={(e) => setFilters((f) => ({ ...f, trade_count_max: e.target.value }))} />
              </div>
              <div className="flex items-center gap-1">
                <Input type="number" placeholder="联系人(起)" value={filters.contact_count_min}
                  onChange={(e) => setFilters((f) => ({ ...f, contact_count_min: e.target.value }))} />
                <span className="text-muted-foreground">-</span>
                <Input type="number" placeholder="联系人(止)" value={filters.contact_count_max}
                  onChange={(e) => setFilters((f) => ({ ...f, contact_count_max: e.target.value }))} />
              </div>
              <div className="flex items-center gap-1">
                <Input type="number" placeholder="成立年(起)" value={filters.founded_year_from}
                  onChange={(e) => setFilters((f) => ({ ...f, founded_year_from: e.target.value }))} />
                <span className="text-muted-foreground">-</span>
                <Input type="number" placeholder="成立年(止)" value={filters.founded_year_to}
                  onChange={(e) => setFilters((f) => ({ ...f, founded_year_to: e.target.value }))} />
              </div>
              <div className="flex items-center gap-2">
                <Button type="submit" size="sm"><Search className="mr-1 h-3.5 w-3.5" />查询</Button>
                <Button type="button" variant="outline" size="sm" onClick={onReset}><X className="mr-1 h-3.5 w-3.5" />重置</Button>
              </div>
            </div>
          </form>
        </CardContent>
      </Card>

      {/* 批量操作栏 */}
      {selectedIds.size > 0 && (
        <div className="flex items-center gap-3 rounded-md border bg-muted/50 px-4 py-2 text-sm">
          <span>已选 {selectedIds.size} 家公司</span>
          <Button size="sm" variant="outline" onClick={() => {
            setGroupTarget({ tcIds: Array.from(selectedIds), label: `选中的 ${selectedIds.size} 家公司` });
          }}>加入群组</Button>
          <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>取消选择</Button>
        </div>
      )}

      {/* 表格 */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[1100px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  <th className="w-10 px-3 py-2">
                    <Checkbox checked={allSelected ? true : someSelected ? 'indeterminate' : false} onCheckedChange={toggleAll} />
                  </th>
                  {['公司', '国家', '细分行业', '产品标签', '评级', '总分', '操作'].map((h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.length === 0 && (
                  <tr><td colSpan={8} className="py-12 text-center text-muted-foreground">
                    {listQuery.isLoading ? '加载中...' : '暂无数据'}
                  </td></tr>
                )}
                {items.map((row) => (
                  <tr key={row.id} className="border-b hover:bg-muted/40">
                    <td className="px-3 py-2">
                      <Checkbox checked={selectedIds.has(row.tc_id)} onCheckedChange={() => toggleSelect(row.tc_id)} />
                    </td>
                    <td className="max-w-[200px] px-3 py-2">
                      <button className="text-left font-medium text-primary hover:underline" onClick={() => setDetailId(row.id)}>
                        {dash(row.name)}
                      </button>
                      <div className="truncate text-xs text-muted-foreground">{row.domain ?? ''}</div>
                    </td>
                    <td className="px-3 py-2">{dash(row.country_iso3)}</td>
                    <td className="max-w-[120px] truncate px-3 py-2">{dash(row.sub_industry)}</td>
                    <td className="max-w-[160px] px-3 py-2">
                      <div className="flex flex-wrap gap-1">
                        {(row.product_tags ?? []).slice(0, 3).map((t) => <Badge key={t} variant="secondary" className="text-xs">{t}</Badge>)}
                        {(row.product_tags ?? []).length > 3 && <Badge variant="outline" className="text-xs">+{(row.product_tags!.length - 3)}</Badge>}
                        {!(row.product_tags ?? []).length && '-'}
                      </div>
                    </td>
                    <td className="px-3 py-2">{row.grade ? <RatingTag grade={row.grade} /> : '-'}</td>
                    <td className="px-3 py-2">{row.wmt_score != null ? row.wmt_score : '-'}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <div className="flex items-center gap-1">
                        <Button variant="link" size="sm" className="h-auto p-0" onClick={() => setDetailId(row.id)}>详情</Button>
                        <Button variant="link" size="sm" className="h-auto p-0" onClick={() => {
                          setGroupTarget({ tcIds: [row.tc_id], label: row.name });
                        }}>群组</Button>
                        <Button variant="link" size="sm" className="h-auto p-0 text-destructive" onClick={() => {
                          setBlacklistTarget({ tcId: row.tc_id, name: row.name });
                        }}>拉黑</Button>
                      </div>
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
              <Select value={String(pageSize)} onValueChange={(v) => { setPageSize(Number(v)); setPage(1); setSelectedIds(new Set()); }}>
                <SelectTrigger className="h-8 w-[100px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((s) => <SelectItem key={s} value={String(s)}>{s} 条/页</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => { setPage((p) => p - 1); setSelectedIds(new Set()); }}>上一页</Button>
              <span>第</span>
              <Input
                type="number" className="h-8 w-16 text-center" min={1} max={maxPage}
                value={jumpPage || page}
                onChange={(e) => setJumpPage(e.target.value)}
                onFocus={() => setJumpPage(String(page))}
                onBlur={() => {
                  if (jumpPage) { setPage(Math.max(1, Math.min(Number(jumpPage) || 1, maxPage))); setSelectedIds(new Set()); }
                  setJumpPage('');
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setPage(Math.max(1, Math.min(Number(jumpPage) || 1, maxPage)));
                    setSelectedIds(new Set());
                    setJumpPage('');
                    (e.target as HTMLInputElement).blur();
                  }
                }}
              />
              <span>/ {maxPage} 页</span>
              <Button variant="outline" size="sm" disabled={page >= maxPage} onClick={() => { setPage((p) => p + 1); setSelectedIds(new Set()); }}>下一页</Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 详情 Drawer */}
      <Sheet open={detailId !== null} onOpenChange={(open) => !open && setDetailId(null)}>
        <SheetContent className="w-[660px] max-w-full overflow-y-auto p-0">
          <div className="border-b px-5 py-4">
            <SheetTitle>{detailQuery.data?.name ?? '公司详情'}</SheetTitle>
          </div>
          {detailQuery.data && (
            <CompanyDetail
              company={detailQuery.data}
              onGroupAdd={(tcId, name) => setGroupTarget({ tcIds: [tcId], label: name })}
              onSaved={invalidateList}
            />
          )}
        </SheetContent>
      </Sheet>

      {/* 群组 Modal */}
      <GroupModal
        target={groupTarget}
        onClose={() => setGroupTarget(null)}
        onSuccess={() => { invalidateList(); setSelectedIds(new Set()); }}
      />

      {/* 拉黑 Modal */}
      <BlacklistModal
        target={blacklistTarget}
        onClose={() => setBlacklistTarget(null)}
        onSuccess={invalidateList}
      />
    </div>
  );
}

/* ─── GroupModal ─────────────────────────────────────────────── */

function GroupModal({ target, onClose, onSuccess }: {
  target: { tcIds: string[]; label: string } | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [selectedGroup, setSelectedGroup] = useState<string>('');
  const groupsQuery = useQuery({
    queryKey: ['tenant', 'groups'],
    queryFn: async () => (await tenantApi.groups.list()).data.data,
    enabled: target !== null,
  });
  const mutation = useMutation({
    mutationFn: async () => {
      if (!target || !selectedGroup) return;
      await tenantApi.groups.batchAddMembers(selectedGroup, target.tcIds);
    },
    onSuccess: () => {
      toast.success('已加入群组');
      setSelectedGroup('');
      onClose();
      onSuccess();
    },
    onError: () => toast.error('加入群组失败'),
  });

  const groups = groupsQuery.data ?? [];

  return (
    <Dialog open={target !== null} onOpenChange={(open) => { if (!open) { setSelectedGroup(''); onClose(); } }}>
      <DialogContent>
        <DialogTitle>
          {target && target.tcIds.length > 1
            ? `将选中的 ${target.tcIds.length} 家公司批量加入群组`
            : `将「${target?.label ?? ''}」加入群组`}
        </DialogTitle>
        {groups.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">暂无群组，请先创建群组</p>
        ) : (
          <div className="max-h-64 space-y-2 overflow-y-auto py-2">
            {groups.map((g: Group) => (
              <label key={g.id} className="flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 hover:bg-muted/50">
                <input type="radio" name="group" value={g.id} checked={selectedGroup === g.id}
                  onChange={() => setSelectedGroup(g.id)} className="accent-primary" />
                <span className="flex-1 text-sm font-medium">{g.name}</span>
                <span className="text-xs text-muted-foreground">{g.member_count} 个成员</span>
              </label>
            ))}
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={() => { setSelectedGroup(''); onClose(); }}>取消</Button>
          <Button disabled={!selectedGroup || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? '加入中...' : '确认加入'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ─── BlacklistModal ─────────────────────────────────────────── */

function BlacklistModal({ target, onClose, onSuccess }: {
  target: { tcId: string; name: string } | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const mutation = useMutation({
    mutationFn: async () => {
      if (!target) return;
      await tenantApi.companies.blacklist(target.tcId, 'manual blacklist');
    },
    onSuccess: () => {
      toast.success('已加入黑名单');
      onClose();
      onSuccess();
    },
    onError: () => toast.error('拉黑失败'),
  });

  return (
    <AlertDialog open={target !== null} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogTitle>确认拉黑</AlertDialogTitle>
        <AlertDialogDescription>
          将「{target?.name ?? ''}」加入黑名单后，不会再向其发送邮件，且不会出现在发送计划目标中。
        </AlertDialogDescription>
        <div className="flex justify-end gap-2 pt-2">
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            disabled={mutation.isPending}
            onClick={(e) => { e.preventDefault(); mutation.mutate(); }}
          >
            {mutation.isPending ? '处理中...' : '确认拉黑'}
          </AlertDialogAction>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
}
