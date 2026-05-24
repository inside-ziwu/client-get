'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useEffect, useState } from 'react';
import { useAuthStore } from '@shared/hooks';
import type { TeamUser } from '@shared/api/src/tenant/team';
import { toast } from 'sonner';
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogTitle,
  Badge, Button, Card, CardContent,
  Dialog, DialogContent, DialogTitle,
  Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';
import { queryKeys } from '@shared/api';

const ROLE_LABELS: Record<string, string> = {
  admin: '管理员',
  operator: '运营',
  readonly: '只读',
};

const STATUS_LABELS: Record<string, string> = {
  active: '已激活',
  disabled: '已禁用',
};

function formatLoginTime(iso: string | null | undefined): string {
  if (!iso) return '-';
  const date = new Date(iso);
  if (isNaN(date.getTime())) return '-';
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  const h = String(date.getHours()).padStart(2, '0');
  const min = String(date.getMinutes()).padStart(2, '0');
  return `${y}-${m}-${d} ${h}:${min}`;
}

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

  return (
    <div className="tenant-page">
      <PageHeader title="团队管理" description="管理租户成员和角色" />
      <Card>
        <CardContent className="p-5">
          <form className="grid gap-3 md:grid-cols-[1fr_1.5fr_1fr_auto]" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="member-name">姓名</Label>
              <Input id="member-name" value={name} onChange={(event) => setName(event.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="member-email">邮箱</Label>
              <Input id="member-email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </div>
            <div className="space-y-2">
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
              <Button type="submit">邀请/创建</Button>
            </div>
          </form>
        </CardContent>
      </Card>
      <DataTable
        rows={usersQuery.data}
        columns={[
          { key: 'name', title: '姓名', render: (row) => <span className="font-medium">{row.name}</span> },
          { key: 'email', title: '邮箱', render: (row) => row.email },
          { key: 'roles', title: '角色', render: (row) => row.roles?.length ? row.roles.map((r) => ROLE_LABELS[r] ?? r).join('、') : '-' },
          { key: 'status', title: '状态', render: (row) => <Badge variant={row.status === 'active' ? 'default' : 'secondary'}>{STATUS_LABELS[row.status] ?? row.status}</Badge> },
          { key: 'login', title: '最近登录', render: (row) => formatLoginTime(row.last_login_at) },
          { key: 'actions', title: '操作', render: (row) => {
            if (row.id === payload?.sub) {
              return <span className="text-sm text-muted-foreground">当前账号</span>;
            }
            return (
              <div className="flex items-center gap-2">
                <Button variant="link" size="sm" onClick={() => setEditTarget(row)}>编辑</Button>
                <Button variant="outline" size="sm" onClick={() => handleToggleStatus(row)}>
                  {row.status === 'active' ? '禁用' : '启用'}
                </Button>
                <Button variant="destructive" size="sm" onClick={() => setDeleteTarget(row)}>删除</Button>
              </div>
            );
          }},
        ]}
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
    </div>
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
            className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
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
