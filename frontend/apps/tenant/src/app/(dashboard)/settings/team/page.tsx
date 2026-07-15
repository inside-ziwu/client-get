'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useEffect, useState } from 'react';
import { useAuthStore } from '@shared/hooks';
import { queryKeys, type TeamUser } from '@shared/api';
import { toast } from 'sonner';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogTitle,
  Button, Card, CardContent, DataTable,
  Dialog, DialogContent, DialogTitle,
  Input, Label, ListPage, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
  type DataTableColumn,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  operator: '运营',
  readonly: '只读',
};

export default function TeamPage() {
  const queryClient = useQueryClient();
  const payload = useAuthStore((s) => s.payload);
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [role, setRole] = useState('operator');
  const [editTarget, setEditTarget] = useState<TeamUser | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<TeamUser | null>(null);
  const usersQuery = useQuery({
    queryKey: queryKeys.team.list(),
    queryFn: async () => (await tenantApi.team.list()).data.data,
  });
  const createMutation = useMutation({
    mutationFn: async () => tenantApi.team.create({ email, name, roles: [role], must_change_pwd: true }),
    onSuccess: async () => {
      toast.success('成员已创建');
      setEmail('');
      setName('');
      setRole('operator');
      await queryClient.invalidateQueries({ queryKey: queryKeys.team.all() });
    },
    onError: () => toast.error('创建失败'),
  });

  const toggleStatusMutation = useMutation({
    mutationFn: async (user: TeamUser) => tenantApi.team.update(user.id, { status: user.status === 'active' ? 'disabled' : 'active' }),
    onSuccess: async () => {
      toast.success('状态已更新');
      await queryClient.invalidateQueries({ queryKey: queryKeys.team.all() });
    },
    onError: () => toast.error('状态更新失败'),
  });

  const handleToggleStatus = (user: TeamUser) => toggleStatusMutation.mutate(user);

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate();
  };

  const columns: DataTableColumn<TeamUser>[] = [
    {
      id: 'name',
      header: '姓名',
      width: 'medium',
      type: 'text',
      value: 'name',
      render: (row) => <span className="text-ui-body-strong">{row.name}</span>,
    },
    { id: 'email', header: '邮箱', width: 'large', type: 'text', value: 'email' },
    {
      id: 'roles',
      header: '角色',
      width: 'small',
      align: 'center',
      type: 'text',
      value: 'roles',
      render: (row) => row.roles?.length ? row.roles.map((item) => ROLE_LABELS[item] ?? item).join('、') : '-',
    },
    {
      id: 'status',
      header: '状态',
      width: 'small',
      align: 'center',
      type: 'status',
      value: 'status',
      statusMap: {
        active: { label: '已激活', tone: 'success' },
        disabled: { label: '已禁用', tone: 'neutral' },
      },
    },
    {
      id: 'login',
      header: '最近登录',
      width: 'medium',
      align: 'center',
      type: 'date',
      value: 'last_login_at',
      format: (value) => formatDateTime(value as string | undefined),
    },
    {
      id: 'actions',
      header: '操作',
      width: 'large',
      align: 'center',
      type: 'actions',
      render: (row) => {
        if (row.id === payload?.sub) {
          return <span className="text-ui-caption text-ui-muted-foreground">当前账号</span>;
        }
        const isToggling = toggleStatusMutation.isPending && toggleStatusMutation.variables?.id === row.id;
        return (
          <div className="flex items-center justify-center gap-ui-xxs">
            <Button variant="link" className="h-8 px-ui-xxs text-ui-foreground" onClick={() => setEditTarget(row)}>编辑</Button>
            <Button
              variant="link"
              className="h-8 px-ui-xxs text-ui-foreground"
              disabled={isToggling}
              onClick={() => handleToggleStatus(row)}
            >
              {row.status === 'active' ? '禁用' : '启用'}
            </Button>
            <Button
              variant="link"
              className="h-8 px-ui-xxs text-ui-foreground hover:text-ui-danger-foreground focus-visible:text-ui-danger-foreground"
              onClick={() => setDeleteTarget(row)}
            >
              删除
            </Button>
          </div>
        );
      },
    },
  ];

  const users = usersQuery.data ?? [];
  const tableState = usersQuery.isLoading
    ? { kind: 'loading' as const }
    : usersQuery.isError
      ? { kind: 'error' as const, description: '请检查网络后重试', onRetry: () => void usersQuery.refetch() }
      : users.length === 0
        ? { kind: 'empty' as const }
        : undefined;

  return (
    <ListPage
      className="tenant-page"
      title="团队管理"
      description="管理租户成员和角色"
      filters={(
        <Card>
          <CardContent className="p-5">
            <form className="flex flex-wrap items-end gap-3" onSubmit={onSubmit}>
              <div className="w-full flex-none space-y-2 sm:w-ui-control-small">
                <Label htmlFor="member-name">姓名</Label>
                <Input id="member-name" value={name} onChange={(event) => setName(event.target.value)} required />
              </div>
              <div className="w-full flex-none space-y-2 sm:w-ui-control-medium">
                <Label htmlFor="member-email">邮箱</Label>
                <Input id="member-email" value={email} onChange={(event) => setEmail(event.target.value)} required />
              </div>
              <div className="w-full flex-none space-y-2 sm:w-ui-control-small">
                <Label>角色</Label>
                <Select value={role} onValueChange={setRole}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {Object.entries(ROLE_LABELS).map(([value, label]) => (
                      <SelectItem key={value} value={value}>{label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex items-end">
                <Button type="submit" disabled={createMutation.isPending}>
                  {createMutation.isPending ? '创建中…' : '邀请/创建'}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>
      )}
    >
      <DataTable
        columns={columns}
        data={users}
        entityName="团队成员"
        getRowId={(row) => row.id}
        isRefreshing={usersQuery.isFetching && !usersQuery.isLoading}
        state={tableState}
      />
      <EditMemberDialog
        target={editTarget}
        onClose={() => setEditTarget(null)}
        onSuccess={async () => {
          await queryClient.invalidateQueries({ queryKey: queryKeys.team.all() });
        }}
      />
      <DeleteMemberDialog
        target={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        onSuccess={async () => {
          await queryClient.invalidateQueries({ queryKey: queryKeys.team.all() });
        }}
      />
    </ListPage>
  );
}

/* ─── EditMemberDialog ───────────────────────────────────── */

function EditMemberDialog({ target, onClose, onSuccess }: {
  target: TeamUser | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [editName, setEditName] = useState('');
  const [editRole, setEditRole] = useState('operator');
  const [error, setError] = useState('');

  useEffect(() => {
    if (target) {
      setEditName(target.name);
      setEditRole(target.roles?.[0] ?? 'operator');
      setError('');
    }
  }, [target]);

  const mutation = useMutation({
    mutationFn: async () => {
      if (!target) return;
      await tenantApi.team.update(target.id, { name: editName, roles: [editRole] });
    },
    onSuccess: () => {
      toast.success('成员已更新');
      onClose();
      onSuccess();
    },
    onError: () => setError('保存失败，请重试'),
  });

  return (
    <Dialog open={target !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogTitle>编辑成员</DialogTitle>
        <div className="space-y-3 py-2">
          <div>
            <label className="mb-1 block text-sm font-medium">姓名</label>
            <Input value={editName} onChange={(e) => setEditName(e.target.value)} />
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium">角色</label>
            <Select value={editRole} onValueChange={setEditRole}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {Object.entries(ROLE_LABELS).map(([value, label]) => (
                  <SelectItem key={value} value={value}>{label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={onClose}>取消</Button>
          <Button disabled={!editName.trim() || mutation.isPending} onClick={() => mutation.mutate()}>
            {mutation.isPending ? '保存中...' : '保存'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

/* ─── DeleteMemberDialog ─────────────────────────────────── */

function DeleteMemberDialog({ target, onClose, onSuccess }: {
  target: TeamUser | null;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const mutation = useMutation({
    mutationFn: async () => {
      if (!target) return;
      await tenantApi.team.delete(target.id);
    },
    onSuccess: () => {
      toast.success('成员已删除');
      onClose();
      onSuccess();
    },
    onError: () => toast.error('删除失败'),
  });

  return (
    <AlertDialog open={target !== null} onOpenChange={(open) => !open && onClose()}>
      <AlertDialogContent>
        <AlertDialogTitle>确认删除成员</AlertDialogTitle>
        <AlertDialogDescription>
          确定删除成员「{target?.name ?? ''}」吗？此操作不可撤销。
        </AlertDialogDescription>
        <div className="flex justify-end gap-2 pt-2">
          <AlertDialogCancel>取消</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={mutation.isPending}
            onClick={(e) => { e.preventDefault(); mutation.mutate(); }}
          >
            {mutation.isPending ? '删除中...' : '确认删除'}
          </AlertDialogAction>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
}
