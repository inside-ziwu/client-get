'use client';

import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { type FormEvent, useState } from 'react';
import { toast } from 'sonner';
import { Button, Card, CardContent, Input, Label, Textarea } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { PageHeader } from '@/components/pages/page-kit';

export default function NewSendPlanPage() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const createMutation = useMutation({
    mutationFn: async () => (await tenantApi.sendingPlans.create({ name, description, status: 'draft' })).data.data,
    onSuccess: (plan) => {
      toast.success('发送计划已创建');
      router.replace(`/send-plans/${plan.id}`);
    },
    onError: () => toast.error('创建失败'),
  });

  const onSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    createMutation.mutate();
  };

  return (
    <div className="tenant-page">
      <PageHeader title="新建发送计划" description="创建草稿后可继续补充收件人和步骤" />
      <Card>
        <CardContent className="p-5">
          <form className="max-w-2xl space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="name">计划名称</Label>
              <Input id="name" value={name} onChange={(event) => setName(event.target.value)} required />
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">描述</Label>
              <Textarea id="description" value={description} onChange={(event) => setDescription(event.target.value)} />
            </div>
            <Button type="submit" disabled={createMutation.isPending}>创建计划</Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
