'use client';

import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import type { SendingPlan } from '@shared/api';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogTitle,
  Button, Card, CardContent,
  Input, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  StatusTag, Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';
import { PageHeader } from '@/components/pages/page-kit';

const PAGE_SIZE_OPTIONS = [20, 50, 100, 500, 1000] as const;

const STATUS_OPTIONS = [
  { value: 'all', label: '全部状态' },
  { value: 'draft', label: '草稿' },
  { value: 'scheduled', label: '已排期' },
  { value: 'running', label: '执行中' },
  { value: 'paused', label: '已暂停' },
  { value: 'completed', label: '已完成' },
  { value: 'cancelled', label: '已取消' },
] as const;

type DeleteTarget = { id: string; name: string } | null;

export default function SendPlansPage() {
  const router = useRouter();
  const queryClient = useQueryClient();

  const [statusFilter, setStatusFilter] = useState('all');
  const [searchInput, setSearchInput] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  const [appliedFilters, setAppliedFilters] = useState({ status: 'all', keyword: '', dateFrom: '', dateTo: '' });
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [jumpPage, setJumpPage] = useState('');
  const [deleteTarget, setDeleteTarget] = useState<DeleteTarget>(null);

  const applyFilters = () => {
    setAppliedFilters({ status: statusFilter, keyword: searchInput, dateFrom, dateTo });
    setPage(1);
  };

  const resetFilters = () => {
    setStatusFilter('all');
    setSearchInput('');
    setDateFrom('');
    setDateTo('');
    setAppliedFilters({ status: 'all', keyword: '', dateFrom: '', dateTo: '' });
    setPage(1);
  };

  const listQuery = useQuery({
    queryKey: ['tenant', 'sendingPlans', page, pageSize, appliedFilters],
    queryFn: async () => (await tenantApi.sendingPlans.list({
      page,
      page_size: pageSize,
      ...(appliedFilters.status !== 'all' && { status: appliedFilters.status }),
      ...(appliedFilters.keyword && { keyword: appliedFilters.keyword }),
      ...(appliedFilters.dateFrom && { date_from: appliedFilters.dateFrom }),
      ...(appliedFilters.dateTo && { date_to: appliedFilters.dateTo }),
    })).data,
  });

  const items: SendingPlan[] = listQuery.data?.data ?? [];
  const total = listQuery.data?.pagination?.total ?? 0;
  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  const deleteMutation = useMutation({
    mutationFn: (id: string) => tenantApi.sendingPlans.delete(id),
    onSuccess: () => {
      toast.success('计划已删除');
      setDeleteTarget(null);
      queryClient.invalidateQueries({ queryKey: ['tenant', 'sendingPlans'] });
    },
    onError: () => toast.error('删除失败'),
  });

  const canEdit = (status: string) => status === 'draft';
  const canDelete = (status: string) => ['draft', 'completed', 'cancelled'].includes(status);

  return (
    <div className="tenant-page space-y-4">
      <PageHeader
        title="发送计划"
        description="管理邮件触达计划"
        action={<Button asChild><Link href="/send-plans/new">新建计划</Link></Button>}
      />

      {/* 筛选栏 */}
      <div className="flex flex-wrap items-center gap-3">
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[140px]"><SelectValue placeholder="全部状态" /></SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map((opt) => (
              <SelectItem key={opt.value} value={opt.value}>{opt.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Input
          placeholder="搜索计划名称..."
          className="w-[200px]"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
        />

        <Input
          type="date"
          className="w-[160px]"
          value={dateFrom}
          onChange={(e) => setDateFrom(e.target.value)}
        />
        <span className="text-muted-foreground">至</span>
        <Input
          type="date"
          className="w-[160px]"
          value={dateTo}
          onChange={(e) => setDateTo(e.target.value)}
        />

        <Button size="sm" onClick={applyFilters}>查询</Button>
        <Button variant="outline" size="sm" onClick={resetFilters}>重置</Button>
      </div>

      {/* 表格 */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>计划名称</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>收件人数</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead>操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5} className="py-12 text-center text-muted-foreground">
                    {listQuery.isLoading ? '加载中...' : '暂无数据'}
                  </TableCell>
                </TableRow>
              )}
              {items.map((plan) => (
                <TableRow
                  key={plan.id}
                  className="cursor-pointer"
                  onClick={() => router.push(`/send-plans/${plan.id}`)}
                >
                  <TableCell className="font-medium">{plan.name}</TableCell>
                  <TableCell><StatusTag status={plan.status as never} /></TableCell>
                  <TableCell>{plan.total_recipients ?? '-'}</TableCell>
                  <TableCell>{formatDateTime(plan.created_at)}</TableCell>
                  <TableCell onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center gap-2">
                      <Button variant="link" size="sm" className="h-auto p-0" onClick={() => router.push(`/send-plans/${plan.id}`)}>
                        详情
                      </Button>
                      {canEdit(plan.status) && (
                        <Button variant="link" size="sm" className="h-auto p-0" onClick={() => router.push(`/send-plans/${plan.id}/edit`)}>
                          编辑
                        </Button>
                      )}
                      {canDelete(plan.status) && (
                        <Button variant="link" size="sm" className="h-auto p-0 text-destructive" onClick={() => setDeleteTarget({ id: plan.id, name: plan.name })}>
                          删除
                        </Button>
                      )}
                    </div>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>

          {/* 分页 */}
          <div className="flex items-center justify-between border-t px-4 py-3 text-sm">
            <div className="flex items-center gap-3 text-muted-foreground">
              <span>共 {total} 条</span>
              <Select value={String(pageSize)} onValueChange={(v) => { setPageSize(Number(v)); setPage(1); }}>
                <SelectTrigger className="h-8 w-[100px]"><SelectValue /></SelectTrigger>
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

      {/* 删除确认弹窗 */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogTitle>确认删除计划？</AlertDialogTitle>
          <AlertDialogDescription>
            确定要删除计划「{deleteTarget?.name}」吗？删除后无法恢复。
          </AlertDialogDescription>
          <div className="flex justify-end gap-2">
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
              disabled={deleteMutation.isPending}
              onClick={(e) => { e.preventDefault(); deleteTarget && deleteMutation.mutate(deleteTarget.id); }}
            >
              {deleteMutation.isPending ? '删除中...' : '删除'}
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
