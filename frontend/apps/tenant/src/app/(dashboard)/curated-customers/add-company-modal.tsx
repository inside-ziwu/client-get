'use client';

import type { Company } from '@shared/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import {
  Button, Checkbox, Dialog, DialogContent, DialogTitle,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Input, RatingTag,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import CompanyFilters, { type FilterValues, EMPTY_FILTERS, buildParams, countryZh } from '@/components/company-filters';

const PAGE_SIZE_OPTIONS = [20, 50, 100, 500, 1000] as const;

function dash(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '-';
  return String(value);
}

interface Props {
  groupId: string;
  open: boolean;
  onClose: () => void;
}

export default function AddCompanyModal({ groupId, open, onClose }: Props) {
  const queryClient = useQueryClient();
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [jumpPage, setJumpPage] = useState('');
  const [selectedTcIds, setSelectedTcIds] = useState<Set<string>>(new Set());

  const filtersQuery = useQuery({
    queryKey: ['tenant', 'companies', 'filters'],
    queryFn: async () => (await tenantApi.companies.filters()).data.data,
  });

  const listQuery = useQuery({
    queryKey: ['tenant', 'add-modal-companies', page, pageSize, appliedFilters],
    queryFn: async () => (await tenantApi.companies.list(buildParams(appliedFilters, page, pageSize))).data,
    enabled: open,
  });

  const existingQuery = useQuery({
    queryKey: ['tenant', 'group-member-ids', groupId],
    queryFn: async () => {
      const res = await tenantApi.companies.list({ group_id: groupId, page: 1, page_size: 500 });
      return new Set(res.data.data.map((c: Company) => c.tc_id));
    },
    enabled: open,
  });

  const items: Company[] = listQuery.data?.data ?? [];
  const total = listQuery.data?.pagination?.total ?? 0;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));
  const existingIds = existingQuery.data ?? new Set<string>();

  const addMutation = useMutation({
    mutationFn: async () => {
      await tenantApi.groups.batchAddMembers(groupId, Array.from(selectedTcIds));
    },
    onSuccess: () => {
      toast.success(`已添加 ${selectedTcIds.size} 家公司到群组`);
      setSelectedTcIds(new Set());
      queryClient.invalidateQueries({ queryKey: ['tenant', 'groups'] });
      queryClient.invalidateQueries({ queryKey: ['tenant', 'curated-companies'] });
      queryClient.invalidateQueries({ queryKey: ['tenant', 'group-member-ids'] });
      onClose();
    },
    onError: () => toast.error('添加失败'),
  });

  const handleApplyFilters = (filters: FilterValues) => {
    setAppliedFilters(filters);
    setPage(1);
    setSelectedTcIds(new Set());
  };

  const handleResetFilters = () => {
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
    setSelectedTcIds(new Set());
  };

  const toggleSelect = (tcId: string) => {
    if (existingIds.has(tcId)) return;
    setSelectedTcIds((prev) => {
      const next = new Set(prev);
      if (next.has(tcId)) next.delete(tcId); else next.add(tcId);
      return next;
    });
  };

  const selectableItems = items.filter((c) => !existingIds.has(c.tc_id));
  const allSelected = selectableItems.length > 0 && selectableItems.every((c) => selectedTcIds.has(c.tc_id));
  const someSelected = selectableItems.some((c) => selectedTcIds.has(c.tc_id)) && !allSelected;

  const toggleAll = () => {
    if (allSelected) {
      setSelectedTcIds((prev) => {
        const next = new Set(prev);
        for (const c of selectableItems) next.delete(c.tc_id);
        return next;
      });
    } else {
      setSelectedTcIds((prev) => {
        const next = new Set(prev);
        for (const c of selectableItems) next.add(c.tc_id);
        return next;
      });
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) { setSelectedTcIds(new Set()); setAppliedFilters(EMPTY_FILTERS); setPage(1); onClose(); } }}>
      <DialogContent className="max-w-6xl max-h-[85vh] overflow-hidden flex flex-col">
        <DialogTitle>从公司列表添加</DialogTitle>

        <div className="min-h-0 flex-1 overflow-y-auto space-y-3">
          <CompanyFilters
            filtersOptions={filtersQuery.data}
            onApply={handleApplyFilters}
            onReset={handleResetFilters}
            compact
          />

          <div className="overflow-x-auto">
            <table className="w-full min-w-[1200px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  <th className="w-10 px-3 py-2">
                    <Checkbox checked={allSelected ? true : someSelected ? 'indeterminate' : false} onCheckedChange={toggleAll} />
                  </th>
                  {['公司名', '国家', '域名', '行业', '员工规模', '大模型评级', '大模型评分', '系统评级', '系统评分', '细分行业', '联系人数', '状态'].map((h) => (
                    <th key={h} className="whitespace-nowrap px-3 py-2">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.length === 0 && (
                  <tr><td colSpan={13} className="py-12 text-center text-muted-foreground">
                    {listQuery.isLoading ? '加载中...' : '暂无数据'}
                  </td></tr>
                )}
                {items.map((row) => {
                  const inGroup = existingIds.has(row.tc_id);
                  return (
                    <tr key={row.id} className={`border-b ${inGroup ? 'opacity-50' : 'hover:bg-muted/40'}`}>
                      <td className="px-3 py-2">
                        <Checkbox
                          checked={inGroup ? false : selectedTcIds.has(row.tc_id)}
                          disabled={inGroup}
                          onCheckedChange={() => toggleSelect(row.tc_id)}
                        />
                      </td>
                      <td className="max-w-[180px] truncate px-3 py-2 font-medium">
                        {dash(row.name)}
                        {inGroup && <span className="ml-1 text-xs text-muted-foreground">已添加</span>}
                      </td>
                      <td className="px-3 py-2">{countryZh(row.country_iso3)}</td>
                      <td className="max-w-[150px] truncate px-3 py-2">{dash(row.domain)}</td>
                      <td className="max-w-[140px] truncate px-3 py-2">{dash(row.industry_desc)}</td>
                      <td className="px-3 py-2">{dash(row.employee_num)}</td>
                      <td className="px-3 py-2">
                        {row.grade ? <RatingTag grade={row.grade} variant="model" /> : '-'}
                      </td>
                      <td className="px-3 py-2">{row.wmt_score != null ? row.wmt_score : '-'}</td>
                      <td className="px-3 py-2">
                        {row.system_grade ? <RatingTag grade={row.system_grade} variant="system" /> : '-'}
                      </td>
                      <td className="px-3 py-2">{row.system_score != null ? row.system_score : '-'}</td>
                      <td className="max-w-[120px] truncate px-3 py-2">{dash(row.sub_industry)}</td>
                      <td className="px-3 py-2">{row.contacts_count ?? '-'}</td>
                      <td className="px-3 py-2">{dash(row.business_status)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* 分页 */}
          <div className="flex items-center justify-between px-1 py-2 text-sm">
            <div className="flex items-center gap-3 text-muted-foreground">
              <span>共 {total} 条</span>
              <Select value={String(pageSize)} onValueChange={(v) => { setPageSize(Number(v)); setPage(1); }}>
                <SelectTrigger className="h-8 w-[120px]"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PAGE_SIZE_OPTIONS.map((s) => <SelectItem key={s} value={String(s)}>{s} 条/页</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>上一页</Button>
              <span>第</span>
              <Input
                type="number" className="h-8 w-16 text-center" min={1} max={maxPage}
                value={jumpPage || page}
                onChange={(e) => setJumpPage(e.target.value)}
                onFocus={() => setJumpPage(String(page))}
                onBlur={() => {
                  if (jumpPage) setPage(Math.max(1, Math.min(Number(jumpPage) || 1, maxPage)));
                  setJumpPage('');
                }}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    setPage(Math.max(1, Math.min(Number(jumpPage) || 1, maxPage)));
                    setJumpPage('');
                    (e.target as HTMLInputElement).blur();
                  }
                }}
              />
              <span>/ {maxPage} 页</span>
              <Button variant="outline" size="sm" disabled={page >= maxPage} onClick={() => setPage((p) => p + 1)}>下一页</Button>
            </div>
          </div>
        </div>

        {/* 底部操作栏 */}
        <div className="flex items-center justify-between border-t pt-3">
          <span className="text-sm text-muted-foreground">
            {selectedTcIds.size > 0 ? `已选 ${selectedTcIds.size} 家公司` : '请勾选要添加的公司'}
          </span>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => { setSelectedTcIds(new Set()); setAppliedFilters(EMPTY_FILTERS); setPage(1); onClose(); }}>
              取消
            </Button>
            <Button disabled={selectedTcIds.size === 0 || addMutation.isPending} onClick={() => addMutation.mutate()}>
              {addMutation.isPending ? '添加中...' : `添加到群组 (${selectedTcIds.size})`}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
