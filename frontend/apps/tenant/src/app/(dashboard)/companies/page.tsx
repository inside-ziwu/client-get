'use client';

import type { Company, Group } from '@shared/api';
import { keepPreviousData, useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogTitle, AlertDialogTrigger,
  Button, CreateButton, DataTable, type DataTableColumn, Dialog, DialogContent,
  DialogDescription, DialogTitle, ListPage, Pagination, RatingTag,
  Sheet, SheetContent, SheetDescription, SheetTitle,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';
import AddCompanySheet from './add-company-sheet';
import CompanyDetail from './company-detail';
import { CompanyListFilterBar } from './company-list-filter-bar';
import { type FilterValues, EMPTY_FILTERS, buildParams, countryZh } from '@/components/company-filters';

const PAGE_SIZE_OPTIONS = [20, 50, 100, 500, 1000] as const;

function dash(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '-';
  return String(value);
}

function collectionTypeLabel(value: Company['collection_type']) {
  return {
    manual: '手工录入',
    keyword: '关键词采集',
    reverse: '精准反推',
    unknown: '来源待确认',
  }[value];
}

function countAppliedFilters(filters: FilterValues) {
  return Object.values(filters).filter((value) =>
    Array.isArray(value) ? value.length > 0 : value.trim() !== '',
  ).length;
}

export default function CompaniesPage() {
  const queryClient = useQueryClient();
  const [draftFilters, setDraftFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);

  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [detailId, setDetailId] = useState<string | null>(null);
  const [groupTarget, setGroupTarget] = useState<{ tcIds: string[]; label: string } | null>(null);
  const [addSheetOpen, setAddSheetOpen] = useState(false);

  const filtersQuery = useQuery({
    queryKey: ['tenant', 'companies', 'filters'],
    queryFn: async () => (await tenantApi.companies.filters()).data.data,
  });

  const listQuery = useQuery({
    queryKey: ['tenant', 'companies', 'list', page, pageSize, appliedFilters],
    queryFn: async () => (await tenantApi.companies.list(buildParams(appliedFilters, page, pageSize))).data,
    placeholderData: keepPreviousData,
  });

  const items: Company[] = listQuery.data?.data ?? [];
  const total = listQuery.data?.pagination?.total ?? 0;
  const appliedCount = countAppliedFilters(appliedFilters);

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
    setDraftFilters(EMPTY_FILTERS);
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

  const togglePage = (rows: readonly Company[]) => {
    setSelectedIds((current) => {
      const next = new Set(current);
      const allSelected = rows.every((row) => next.has(row.tc_id));
      rows.forEach((row) => allSelected ? next.delete(row.tc_id) : next.add(row.tc_id));
      return next;
    });
  };

  const invalidateList = () => queryClient.invalidateQueries({ queryKey: ['tenant', 'companies'] });

  const columns: ReadonlyArray<DataTableColumn<Company>> = [
    {
      id: 'name', header: '公司名', width: 'large', type: 'text', value: 'name',
      render: (row) => (
        <button className="text-left font-medium text-ui-foreground hover:underline" onClick={() => setDetailId(row.id)}>
          {dash(row.name)}
        </button>
      ),
    },
    { id: 'country', header: '国家', width: 'small', align: 'center', type: 'text', value: 'country_iso3', format: (value) => countryZh(value as string | undefined) },
    { id: 'collectionType', header: '采集类型', width: 'small', align: 'center', type: 'text', value: 'collection_type', format: (value) => collectionTypeLabel(value as Company['collection_type']) },
    { id: 'domain', header: '域名', width: 'large', type: 'text', value: 'domain' },
    { id: 'industry', header: '行业', width: 'large', type: 'text', value: 'industry_desc' },
    { id: 'employees', header: '员工规模', width: 'small', align: 'center', type: 'text', value: 'employee_num' },
    { id: 'foundedYear', header: '成立', width: 'small', align: 'center', type: 'number', value: 'founded_year' },
    { id: 'modelGrade', header: '大模型评级', width: 'small', align: 'center', type: 'text', value: 'grade', render: (row) => row.grade ? <RatingTag grade={row.grade} variant="model" /> : '-' },
    { id: 'modelScore', header: '大模型评分', width: 'small', align: 'center', type: 'number', value: 'wmt_score' },
    { id: 'systemGrade', header: '模板评级', width: 'small', align: 'center', type: 'text', value: 'system_grade', render: (row) => row.system_grade ? <RatingTag grade={row.system_grade} variant="system" /> : '-' },
    { id: 'systemScore', header: '模板评分', width: 'small', align: 'center', type: 'number', value: 'system_score' },
    { id: 'subIndustry', header: '细分行业', width: 'small', type: 'text', value: 'sub_industry' },
    { id: 'sourceCompetitor', header: '来源同行', width: 'small', type: 'text', value: 'source_competitor' },
    { id: 'sourceCompetitorCn', header: '来源同行（中文名）', width: 'medium', type: 'text', value: 'source_competitor_cn' },
    { id: 'contacts', header: '联系人数', width: 'small', align: 'center', type: 'number', value: 'contacts_count' },
    { id: 'createdAt', header: '入库时间', width: 'medium', align: 'center', type: 'date', value: 'created_at', format: (value) => formatDateTime(value as string | undefined) },
    {
      id: 'actions', header: '操作', width: 'medium', align: 'center', type: 'actions',
      render: (row) => (
        <div className="flex items-center justify-center gap-ui-xxs">
          <Button variant="link" className="h-8 px-ui-xxs text-ui-foreground" onClick={() => setDetailId(row.id)}>详情</Button>
          <Button variant="link" className="h-8 px-ui-xxs text-ui-foreground" onClick={() => setGroupTarget({ tcIds: [row.tc_id], label: row.name })}>群组</Button>
          <BlacklistAction row={row} onSuccess={invalidateList} />
        </div>
      ),
    },
  ];

  const tableState = listQuery.isLoading
    ? { kind: 'loading' as const }
    : listQuery.isError
      ? { kind: 'error' as const, description: '请检查网络后重试', onRetry: () => void listQuery.refetch() }
      : items.length === 0
        ? { kind: 'empty' as const, filtered: appliedCount > 0, onResetFilters: appliedCount > 0 ? handleResetFilters : undefined }
        : undefined;

  return (
    <ListPage
      className="tenant-page"
      title="公司列表"
      description="筛选、查看和处理租户公司数据"
      primaryAction={(
        <CreateButton onClick={() => setAddSheetOpen(true)}>
          新增公司
        </CreateButton>
      )}
      filters={(
        <div className="flex flex-col gap-ui-sm">
          <CompanyListFilterBar
            values={draftFilters}
            options={filtersQuery.data}
            optionsState={filtersQuery.isLoading ? 'loading' : filtersQuery.data ? 'ready' : 'empty'}
            appliedCount={appliedCount}
            isSubmitting={listQuery.isFetching}
            onChange={setDraftFilters}
            onSubmit={handleApplyFilters}
            onReset={handleResetFilters}
          />
          {filtersQuery.isError ? (
            <div className="flex items-center justify-between gap-ui-sm rounded-ui-md border border-ui-danger-foreground/20 bg-ui-danger-surface px-ui-md py-ui-sm text-ui-body text-ui-danger-foreground" role="alert">
              <span>筛选选项加载失败，仍可使用关键词和固定选项。</span>
              <Button size="sm" variant="outline" onClick={() => void filtersQuery.refetch()}>重试</Button>
            </div>
          ) : null}
        </div>
      )}
      selectionToolbar={selectedIds.size > 0 ? (
        <div className="flex flex-wrap items-center gap-ui-sm rounded-ui-md border border-ui-border bg-ui-surface-soft px-ui-md py-ui-sm text-ui-body">
          <span>已选 {selectedIds.size} 家公司</span>
          <Button size="sm" variant="outline" onClick={() => setGroupTarget({ tcIds: Array.from(selectedIds), label: `选中的 ${selectedIds.size} 家公司` })}>加入群组</Button>
          <Button size="sm" variant="ghost" onClick={() => setSelectedIds(new Set())}>取消选择</Button>
        </div>
      ) : undefined}
      pagination={(
        <Pagination
          mode="total"
          total={total}
          value={{ page, pageSize }}
          pageSizeOptions={PAGE_SIZE_OPTIONS}
          isDisabled={listQuery.isLoading}
          onChange={(next) => {
            setPage(next.page);
            setPageSize(next.pageSize);
            setSelectedIds(new Set());
          }}
        />
      )}
    >
      <DataTable
        columns={columns}
        data={items}
        entityName="公司"
        getRowId={(row) => row.tc_id}
        state={tableState}
        isRefreshing={listQuery.isFetching && !listQuery.isLoading}
        selection={{
          selectedKeys: selectedIds,
          onToggleRow: (row) => toggleSelect(row.tc_id),
          onTogglePage: togglePage,
        }}
      />

      {/* 详情 Drawer */}
      <Sheet open={detailId !== null} onOpenChange={(open) => !open && setDetailId(null)}>
        <SheetContent className="w-[660px] max-w-full overflow-y-auto p-0">
          <div className="border-b px-5 py-4">
            <SheetTitle>{detailQuery.data?.name ?? '公司详情'}</SheetTitle>
            <SheetDescription className="mt-1">查看公司资料、AI 评估与联系人信息。</SheetDescription>
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

      {/* 新增公司 Sheet */}
      <AddCompanySheet open={addSheetOpen} onOpenChange={setAddSheetOpen} onSuccess={invalidateList} />
    </ListPage>
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
        <DialogDescription>选择目标群组；确认后将更新所选公司的群组归属。</DialogDescription>
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

function BlacklistAction({ row, onSuccess }: {
  row: Company;
  onSuccess: () => void;
}) {
  const [open, setOpen] = useState(false);
  const mutation = useMutation({
    mutationFn: async () => tenantApi.companies.blacklist(row.tc_id, 'manual blacklist'),
    onSuccess: () => {
      toast.success('已加入黑名单');
      setOpen(false);
      onSuccess();
    },
    onError: () => toast.error('拉黑失败'),
  });

  return (
    <AlertDialog open={open} onOpenChange={(next) => !mutation.isPending && setOpen(next)}>
      <AlertDialogTrigger asChild>
        <Button
          variant="link"
          className="h-8 px-ui-xxs text-ui-foreground hover:text-ui-danger-foreground focus-visible:text-ui-danger-foreground"
        >
          拉黑
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogTitle>确认拉黑「{row.name}」？</AlertDialogTitle>
        <AlertDialogDescription>
          加入黑名单后，不会再向其发送邮件，且不会出现在发送计划目标中。
        </AlertDialogDescription>
        <div className="flex justify-end gap-2 pt-2">
          <AlertDialogCancel disabled={mutation.isPending}>取消</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={mutation.isPending}
            onClick={(e) => { e.preventDefault(); mutation.mutate(); }}
          >
            {mutation.isPending ? '拉黑中…' : '确认拉黑'}
          </AlertDialogAction>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
}
