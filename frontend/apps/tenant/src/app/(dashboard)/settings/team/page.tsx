'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { toast } from 'sonner';
import { Badge, Button, Card, CardContent, Input, Label } from '@shared/ui';
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
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const usersQuery = useQuery({
    queryKey: queryKeys.team.list(),
    queryFn: async () => (await tenantApi.team.list()).data.data,
  });
  const createMutation = useMutation({
    mutationFn: async () => tenantApi.team.create({ email, name, roles: ['operator'], must_change_pwd: true }),
    onSuccess: async () => {
      toast.success('成员已创建');
      setEmail('');
      setName('');
      await queryClient.invalidateQueries({ queryKey: queryKeys.team.all() });
    },
  });

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate();
  };

  return (
    <div className="tenant-page">
      <PageHeader title="团队管理" description="管理租户成员和角色" />
      <Card>
        <CardContent className="p-5">
          <form className="grid gap-3 md:grid-cols-[1fr_1fr_auto]" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="member-name">姓名</Label>
              <Input id="member-name" value={name} onChange={(event) => setName(event.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="member-email">邮箱</Label>
              <Input id="member-email" value={email} onChange={(event) => setEmail(event.target.value)} required />
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
        ]}
      />
    </div>
  );
}
