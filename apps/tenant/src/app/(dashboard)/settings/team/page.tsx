'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { type FormEvent, useState } from 'react';
import { toast } from 'sonner';
import { Badge, Button, Card, CardContent, Input, Label } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';

export default function TeamPage() {
  const queryClient = useQueryClient();
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const usersQuery = useQuery({
    queryKey: ['tenant', 'team'],
    queryFn: async () => (await tenantApi.team.list()).data.data,
  });
  const createMutation = useMutation({
    mutationFn: async () => tenantApi.team.create({ email, name, roles: ['operator'], must_change_pwd: true }),
    onSuccess: async () => {
      toast.success('成员已创建');
      setEmail('');
      setName('');
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'team'] });
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
          { key: 'roles', title: '角色', render: (row) => row.roles?.join(', ') || '-' },
          { key: 'status', title: '状态', render: (row) => <Badge variant={row.status === 'active' ? 'default' : 'secondary'}>{row.status}</Badge> },
          { key: 'login', title: '最近登录', render: (row) => row.last_login_at?.slice(0, 10) ?? '-' },
        ]}
      />
    </div>
  );
}
