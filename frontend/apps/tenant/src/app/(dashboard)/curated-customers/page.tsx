'use client';

import type { Company, Group } from '@shared/api';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Pencil, Plus, Trash2, Users } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogTitle,
  Button, Card, CardContent,
  Dialog, DialogContent, DialogTitle, Input, RatingTag,
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  Sheet, SheetContent, SheetTitle, Textarea,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';
import { PageHeader } from '@/components/pages/page-kit';
import CompanyDetail from '@/components/company-detail';
import CompanyFilters, { type FilterValues, EMPTY_FILTERS, buildParams, countryZh } from '@/components/company-filters';
import AddCompanyModal from './add-company-modal';

const PAGE_SIZE_OPTIONS = [20, 50, 100, 500, 1000] as const;
const EMPLOYEE_SIZE_COLUMN_CLASS = 'w-[88px] min-w-[88px] max-w-[88px] whitespace-nowrap px-2 py-2';

function dash(value: string | number | null | undefined) {
  if (value === null || value === undefined || value === '') return '-';
  return String(value);
}

function tableHeaderClass(header: string) {
  return header === '员工规模' ? EMPLOYEE_SIZE_COLUMN_CLASS : 'whitespace-nowrap px-3 py-2';
}

export default function CuratedCustomersPage() {
  const queryClient = useQueryClient();
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [appliedFilters, setAppliedFilters] = useState<FilterValues>(EMPTY_FILTERS);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(50);
  const [jumpPage, setJumpPage] = useState('');

  const [detailId, setDetailId] = useState<string | null>(null);
  const [removeTarget, setRemoveTarget] = useState<{ tcId: string; name: string } | null>(null);
  const [groupForm, setGroupForm] = useState<{ open: boolean; editGroup: Group | null }>({ open: false, editGroup: null });
  const [deleteGroup, setDeleteGroup] = useState<Group | null>(null);
  const [addModalOpen, setAddModalOpen] = useState(false);

  const groupsQuery = useQuery({
    queryKey: ['tenant', 'groups'],
    queryFn: async () => (await tenantApi.groups.list()).data.data,
  });
  const groups: Group[] = groupsQuery.data ?? [];

  useEffect(() => {
    if (!selectedGroupId && groups.length > 0) {
      setSelectedGroupId(groups[0]!.id);
    }
  }, [groups, selectedGroupId]);

  const filtersQuery = useQuery({
    queryKey: ['tenant', 'companies', 'filters'],
    queryFn: async () => (await tenantApi.companies.filters()).data.data,
  });

  const listQuery = useQuery({
    queryKey: ['tenant', 'curated-companies', selectedGroupId, page, pageSize, appliedFilters],
    queryFn: async () => {
      if (!selectedGroupId) return { data: [], pagination: { total: 0 } };
      return (await tenantApi.companies.list({ ...buildParams(appliedFilters, page, pageSize), group_id: selectedGroupId })).data;
    },
    enabled: selectedGroupId !== null,
  });

  const items: Company[] = listQuery.data?.data ?? [];
  const total = listQuery.data?.pagination?.total ?? 0;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  const detailQuery = useQuery({
    queryKey: ['tenant', 'companies', 'detail', detailId],
    queryFn: async () => detailId ? (await tenantApi.companies.detail(detailId)).data.data : null,
    enabled: detailId !== null,
  });

  const removeMutation = useMutation({
    mutationFn: async () => {
      if (!removeTarget || !selectedGroupId) return;
      await tenantApi.groups.batchRemoveMembers(selectedGroupId, [removeTarget.tcId]);
    },
    onSuccess: () => {
      toast.success('已从群组移除');
      setRemoveTarget(null);
      invalidateAll();
    },
    onError: () => toast.error('移除失败'),
  });

  const handleApplyFilters = (filters: FilterValues) => {
    setAppliedFilters(filters);
    setPage(1);
  };

  const handleResetFilters = () => {
    setAppliedFilters(EMPTY_FILTERS);
    setPage(1);
  };

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['tenant', 'groups'] });
    queryClient.invalidateQueries({ queryKey: ['tenant', 'curated-companies'] });
  };

  const selectedGroup = groups.find((g) => g.id === selectedGroupId);

  return (
    <div className="tenant-page h-[calc(100vh-theme(spacing.14)-3rem)]">
      <PageHeader title="优选客户" description="按群组管理和查看优选客户公司" />

      <div className="flex min-h-0 flex-1 gap-4">
        {/* 左侧群组面板 */}
        <Card className="w-60 shrink-0 overflow-y-auto">
          <CardContent className="p-3">
            <Button size="sm" className="mb-3 w-full" onClick={() => setGroupForm({ open: true, editGroup: null })}>
              <Plus className="mr-1 h-3.5 w-3.5" />新建群组
            </Button>
            {groups.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                <Users className="mx-auto mb-2 h-8 w-8 opacity-40" />
                <p>暂无群组</p>
                <p className="mt-1 text-xs">点击上方按钮创建第一个群组</p>
              </div>
            ) : (
              <div className="space-y-1">
                {groups.map((g) => (
                  <div
                    key={g.id}
                    className={`group flex cursor-pointer items-center justify-between rounded-md px-3 py-2 text-sm transition-colors ${
                      selectedGroupId === g.id ? 'border-l-2 border-primary bg-primary/5 font-medium' : 'hover:bg-muted/50'
                    }`}
                    onClick={() => { setSelectedGroupId(g.id); setPage(1); setAppliedFilters(EMPTY_FILTERS); }}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate">{g.name}</div>
                      <div className="text-xs text-muted-foreground">{g.member_count} 家公司</div>
                    </div>
                    <div className="flex shrink-0 items-center gap-0.5 opacity-0 group-hover:opacity-100">
                      <button className="rounded p-1 hover:bg-muted" onClick={(e) => { e.stopPropagation(); setGroupForm({ open: true, editGroup: g }); }}>
                        <Pencil className="h-3.5 w-3.5 text-muted-foreground" />
                      </button>
                      <button className="rounded p-1 hover:bg-muted" onClick={(e) => { e.stopPropagation(); setDeleteGroup(g); }}>
                        <Trash2 className="h-3.5 w-3.5 text-muted-foreground" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* 右侧公司列表 */}
        <div className="flex min-w-0 flex-1 flex-col gap-4">
          {!selectedGroup ? (
            <Card>
              <CardContent className="py-20 text-center text-sm text-muted-foreground">
                <Users className="mx-auto mb-3 h-10 w-10 opacity-30" />
                <p>{groups.length === 0 ? '创建一个群组开始管理优选客户' : '选择左侧群组查看公司列表'}</p>
              </CardContent>
            </Card>
          ) : (
            <>
              {/* 标题栏 */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-semibold">{selectedGroup.name}</h2>
                  {selectedGroup.description && (
                    <p className="text-sm text-muted-foreground">{selectedGroup.description}</p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="outline" onClick={() => setGroupForm({ open: true, editGroup: selectedGroup })}>
                    <Pencil className="mr-1 h-3.5 w-3.5" />编辑
                  </Button>
                  <Button size="sm" variant="outline" className="text-destructive" onClick={() => setDeleteGroup(selectedGroup)}>
                    <Trash2 className="mr-1 h-3.5 w-3.5" />删除
                  </Button>
                  <Button size="sm" onClick={() => setAddModalOpen(true)}>
                    <Plus className="mr-1 h-3.5 w-3.5" />从公司列表添加
                  </Button>
                </div>
              </div>

              {/* 筛选 */}
              <CompanyFilters
                filtersOptions={filtersQuery.data}
                onApply={handleApplyFilters}
                onReset={handleResetFilters}
              />

              {/* 表格 */}
              <Card className="flex min-h-0 flex-1 flex-col">
                <CardContent className="flex min-h-0 flex-1 flex-col p-0">
                  <div className="min-h-0 flex-1 overflow-auto">
                    <table className="w-full min-w-[1240px] text-sm">
                      <thead className="sticky top-0 z-10 border-b bg-muted/90 text-left text-xs text-muted-foreground shadow-sm">
                        <tr>
                          {['公司名', '国家', '域名', '行业', '员工规模', '成立', '大模型评级', '大模型评分', '模板评级', '模板评分', '细分行业', '联系人数', '操作', '入库时间'].map((h) => (
                            <th key={h} className={tableHeaderClass(h)}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {items.length === 0 && (
                          <tr><td colSpan={14} className="py-12 text-center text-muted-foreground">
                            {listQuery.isLoading ? '加载中...' : '群组内暂无公司'}
                          </td></tr>
                        )}
                        {items.map((row) => (
                          <tr key={row.id} className="border-b transition-colors hover:bg-muted/45">
                            <td className="max-w-[220px] truncate px-3 py-2">
                              <button className="text-left font-medium text-primary hover:underline" onClick={() => setDetailId(row.id)}>
                                {dash(row.name)}
                              </button>
                            </td>
                            <td className="whitespace-nowrap px-3 py-2">{countryZh(row.country_iso3)}</td>
                            <td className="max-w-[150px] truncate px-3 py-2">{dash(row.domain)}</td>
                            <td className="max-w-[140px] truncate px-3 py-2">{dash(row.industry_desc)}</td>
                            <td className={EMPLOYEE_SIZE_COLUMN_CLASS}>
                              <span className="block truncate">{dash(row.employee_num)}</span>
                            </td>
                            <td className="whitespace-nowrap px-3 py-2">{dash(row.founded_year)}</td>
                            <td className="px-3 py-2">
                              {row.grade ? <RatingTag grade={row.grade} variant="model" /> : '-'}
                            </td>
                            <td className="px-3 py-2">{row.wmt_score != null ? row.wmt_score : '-'}</td>
                            <td className="px-3 py-2">
                              {row.system_grade ? <RatingTag grade={row.system_grade} variant="system" /> : '-'}
                            </td>
                            <td className="px-3 py-2">{row.system_score != null ? row.system_score : '-'}</td>
                            <td className="max-w-[120px] truncate px-3 py-2">{dash(row.sub_industry)}</td>
                            <td className="whitespace-nowrap px-3 py-2">{row.contacts_count ?? '-'}</td>
                            <td className="whitespace-nowrap px-3 py-2">
                              <div className="flex min-w-[72px] items-center gap-2">
                                <Button variant="link" size="sm" className="h-auto p-0" onClick={() => setDetailId(row.id)}>详情</Button>
                                <Button variant="link" size="sm" className="h-auto p-0 text-destructive" onClick={() => {
                                  setRemoveTarget({ tcId: row.tc_id, name: row.name });
                                }}>移除</Button>
                              </div>
                            </td>
                            <td className="whitespace-nowrap px-3 py-2">{formatDateTime(row.created_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>

                  {/* 分页 — 固定在底部 */}
                  <div className="shrink-0 flex items-center justify-between border-t px-4 py-3 text-sm">
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
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </div>

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
              <Button size="sm" variant="outline" className="mt-3" onClick={() => detailQuery.refetch()}>重试</Button>
            </div>
          )}
          {detailQuery.data && (
            <CompanyDetail company={detailQuery.data} onSaved={() => queryClient.invalidateQueries({ queryKey: ['tenant', 'curated-companies'] })} />
          )}
        </SheetContent>
      </Sheet>

      {/* 移除确认 */}
      <AlertDialog open={removeTarget !== null} onOpenChange={(open) => !open && setRemoveTarget(null)}>
        <AlertDialogContent>
          <AlertDialogTitle>确认移除</AlertDialogTitle>
          <AlertDialogDescription>
            将「{removeTarget?.name ?? ''}」从群组中移除？移除后不影响公司数据，可再次添加。
          </AlertDialogDescription>
          <div className="flex justify-end gap-2 pt-2">
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={removeMutation.isPending}
              onClick={(e) => { e.preventDefault(); removeMutation.mutate(); }}
            >
              {removeMutation.isPending ? '处理中...' : '确认移除'}
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>

      {/* 新建/编辑群组 */}
      <GroupFormDialog
        open={groupForm.open}
        editGroup={groupForm.editGroup}
        onClose={() => setGroupForm({ open: false, editGroup: null })}
        onSuccess={(newId) => {
          invalidateAll();
          if (newId) setSelectedGroupId(newId);
        }}
      />

      {/* 删除群组确认 */}
      <DeleteGroupDialog
        group={deleteGroup}
        onClose={() => setDeleteGroup(null)}
        onSuccess={() => {
          invalidateAll();
          if (deleteGroup?.id === selectedGroupId) {
            const remaining = groups.filter((g) => g.id !== deleteGroup?.id);
            setSelectedGroupId(remaining[0]?.id ?? null);
          }
        }}
      />

      {/* 从公司列表添加弹窗 */}
      {selectedGroupId && (
        <AddCompanyModal
          groupId={selectedGroupId}
          open={addModalOpen}
          onClose={() => { setAddModalOpen(false); invalidateAll(); }}
        />
      )}
    </div>
  );
}

/* ─── GroupFormDialog ───────────────────────────────────────── */

function GroupFormDialog({ open, editGroup, onClose, onSuccess }: {
  open: boolean;
  editGroup: Group | null;
  onClose: () => void;
  onSuccess: (newId?: string) => void;
}) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const isEdit = editGroup !== null;

  useEffect(() => {
    if (open && editGroup) {
      setName(editGroup.name);
      setDescription(editGroup.description ?? '');
    } else if (open) {
      setName('');
      setDescription('');
    }
  }, [open, editGroup]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (isEdit) {
        await tenantApi.groups.update(editGroup.id, { name: name.trim(), description: description.trim() || undefined });
        return editGroup.id;
      }
      const res = await tenantApi.groups.create({ name: name.trim(), description: description.trim() || undefined });
      return res.data.data.id;
    },
    onSuccess: (id) => {
      toast.success(isEdit ? '群组已更新' : '群组已创建');
      onClose();
      onSuccess(isEdit ? undefined : id);
    },
    onError: () => toast.error(isEdit ? '更新失败' : '创建失败'),
  });

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogContent>
        <DialogTitle>{isEdit ? '编辑群组' : '新建群组'}</DialogTitle>
        <div className="space-y-3 py-2">
          <div>
            <label className="mb-1 block text-sm font-medium">群组名称</label>
            <Input value={name} onChange={(e) => setName(e.target.value)} placeholder="输入群组名称" />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">描述（可选）</label>
            <Textarea rows={2} value={description} onChange={(e) => setDescription(e.target.value)} placeholder="群组描述" />
          </div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button disabled={!name.trim() || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? '提交中...' : isEdit ? '保存' : '创建'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ─── DeleteGroupDialog ────────────────────────────────────── */

function DeleteGroupDialog({ group, onClose, onSuccess }: {
  group: Group | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const mutation = useMutation({
    mutationFn: async () => {
      if (!group) return;
      await tenantApi.groups.delete(group.id);
    },
    onSuccess: () => {
      toast.success('群组已删除');
      onClose();
      onSuccess();
    },
    onError: () => toast.error('删除失败'),
  });

  return (
    <AlertDialog open={group !== null} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogTitle>确认删除群组</AlertDialogTitle>
        <AlertDialogDescription>
          确定删除群组「{group?.name ?? ''}」吗？仅删除群组，不影响公司数据。
        </AlertDialogDescription>
        <div className="flex justify-end gap-2 pt-2">
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            disabled={mutation.isPending}
            onClick={(e) => { e.preventDefault(); mutation.mutate(); }}
          >
            {mutation.isPending ? '处理中...' : '确认删除'}
          </AlertDialogAction>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
}
