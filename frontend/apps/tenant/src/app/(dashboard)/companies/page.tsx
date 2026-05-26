'use client';

import type { Company, Group } from '@shared/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogTitle,
  Button, Card, CardContent, Checkbox, Dialog, DialogContent,
  DialogTitle, Input,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Sheet, SheetContent, SheetTitle,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';
import { PageHeader } from '@/components/pages/page-kit';
import AddCompanySheet from './add-company-sheet';
import CompanyDetail from './company-detail';
import CompanyFilters, { type FilterValues, EMPTY_FILTERS, buildParams, countryZh } from '@/components/company-filters';

const PAGE_SIZE_OPTIONS = [20, 50, 100] as const;

const GRADE_COLORS: Record<string, string> = {
  S: 'bg-purple-100 text-purple-800',
  A: 'bg-green-100 text-green-800',
  B: 'bg-blue-100 text-blue-800',
  C: 'bg-orange-100 text-orange-800',
  D: 'bg-red-100 text-red-800',
};

function dash(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '-';
  return String(value);
}

export default function CompaniesPage() {
  const queryClient = useQueryClient();
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [jumpPage, setJumpPage] = useState('');

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [detailId, setDetailId] = useState<string | null>(null);
  const [groupTarget, setGroupTarget] = useState<{ tcIds: string[]; label: string } | null>(null);
  const [blacklistTarget, setBlacklistTarget] = useState<{ tcId: string; name: string } | null>(null);
  const [addSheetOpen, setAddSheetOpen] = useState(false);

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

  const handleApplyFilters = (filters: FilterValues) => {
    setAppliedFilters(filters);
    setPage(1);
    setSelectedIds(new Set());
  };

  const handleResetFilters = () => {
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

  return (
    <div className="tenant-page space-y-4">
      <PageHeader title="公司列表" description="筛选、查看和处理租户公司数据" action={<Button onClick={() => setAddSheetOpen(true)}>新增公司</Button>} />

      {/* 筛选面板 */}
      <CompanyFilters
        filtersOptions={filtersQuery.data}
        onApply={handleApplyFilters}
        onReset={handleResetFilters}
      />

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
            <table className="w-full min-w-[1280px] text-sm">
              <thead className="sticky top-0 z-10 border-b bg-muted/90 text-left text-xs text-muted-foreground shadow-sm">
                <tr>
                  <th className="w-10 px-3 py-2">
                    <Checkbox checked={allSelected ? true : someSelected ? 'indeterminate' : false} onCheckedChange={toggleAll} />
                  </th>
                  {['公司名', '国家', '域名', '行业', '员工规模', '成立', '评级', '评分', '细分行业', '来源同行', '来源同行（中文名）', '联系人数', '操作', '入库时间'].map((h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.length === 0 && (
                  <tr><td colSpan={15} className="py-12 text-center text-muted-foreground">
                    {listQuery.isLoading ? '加载中...' : '暂无数据'}
                  </td></tr>
                )}
                {items.map((row) => (
                  <tr key={row.id} className="border-b transition-colors hover:bg-muted/45">
                    <td className="px-3 py-2">
                      <Checkbox checked={selectedIds.has(row.tc_id)} onCheckedChange={() => toggleSelect(row.tc_id)} />
                    </td>
                    <td className="max-w-[220px] truncate px-3 py-2">
                      <button className="text-left font-medium text-primary hover:underline" onClick={() => setDetailId(row.id)}>
                        {dash(row.name)}
                      </button>
                    </td>
                    <td className="whitespace-nowrap px-3 py-2">{countryZh(row.country_iso3)}</td>
                    <td className="max-w-[150px] truncate px-3 py-2">{dash(row.domain)}</td>
                    <td className="max-w-[140px] truncate px-3 py-2">{dash(row.industry_desc)}</td>
                    <td className="whitespace-nowrap px-3 py-2">{dash(row.employee_num)}</td>
                    <td className="whitespace-nowrap px-3 py-2">{dash(row.founded_year)}</td>
                    <td className="px-3 py-2">
                      {row.grade ? (
                        <span className={`inline-block rounded px-2 py-0.5 text-xs font-medium ${GRADE_COLORS[row.grade] ?? ''}`}>
                          {row.grade}
                        </span>
                      ) : '-'}
                    </td>
                    <td className="px-3 py-2">{row.wmt_score != null ? row.wmt_score : '-'}</td>
                    <td className="max-w-[120px] truncate px-3 py-2">{dash(row.sub_industry)}</td>
                    <td className="max-w-[120px] truncate px-3 py-2">{dash(row.source_competitor)}</td>
                    <td className="max-w-[120px] truncate px-3 py-2">{dash(row.source_competitor_cn)}</td>
                    <td className="whitespace-nowrap px-3 py-2">{row.contacts_count ?? '-'}</td>
                    <td className="whitespace-nowrap px-3 py-2">
                      <div className="flex min-w-[104px] items-center gap-2">
                        <Button variant="link" size="sm" className="h-auto p-0" onClick={() => setDetailId(row.id)}>详情</Button>
                        <Button variant="link" size="sm" className="h-auto p-0" onClick={() => {
                          setGroupTarget({ tcIds: [row.tc_id], label: row.name });
                        }}>群组</Button>
                        <Button variant="link" size="sm" className="h-auto p-0 text-destructive" onClick={() => {
                          setBlacklistTarget({ tcId: row.tc_id, name: row.name });
                        }}>拉黑</Button>
                      </div>
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
          {detailQuery.isLoading && (
            <div className="flex items-center justify-center py-20 text-sm text-muted-foreground">加载中...</div>
          )}
          {detailQuery.isError && (
            <div className="px-5 py-10 text-center text-sm text-destructive">
              <p>加载失败</p>
              <p className="mt-1 text-xs text-muted-foreground">{String((detailQuery.error as Error)?.message ?? '未知错误')}</p>
              <Button size="sm" variant="outline" className="mt-3" onClick={() => detailQuery.refetch()}>重试</Button>
            </div>
          )}
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

      {/* 新增公司 Sheet */}
      <AddCompanySheet open={addSheetOpen} onOpenChange={setAddSheetOpen} onSuccess={invalidateList} />
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
