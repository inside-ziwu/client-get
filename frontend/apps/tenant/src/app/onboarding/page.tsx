'use client';

import { useMutation } from '@tanstack/react-query';
import { Building2, CheckCircle2, Mail, Users } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button, Card, CardContent } from '@shared/ui';
import { toast } from 'sonner';
import { tenantApi } from '@/lib/api';

const steps = [
  { title: '筛选目标公司', description: '从共享客户池找到适合的潜在客户。', icon: Building2 },
  { title: '建立客户群组', description: '将目标公司和联系人整理到群组。', icon: Users },
  { title: '创建发送计划', description: '选择邮件模板并安排发送。', icon: Mail },
];

export default function OnboardingPage() {
  const router = useRouter();
  const completeMutation = useMutation({
    mutationFn: async () => (await tenantApi.onboarding.complete()).data.data,
    onSuccess: () => {
      toast.success('引导已完成');
      router.replace('/companies');
    },
    onError: () => toast.error('提交失败，请稍后重试'),
  });

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-3xl">
        <CardContent className="space-y-6 p-6">
          <div>
            <h1 className="text-xl font-semibold">新手引导</h1>
            <p className="mt-1 text-sm text-muted-foreground">完成这些基础检查后进入租户工作台。</p>
          </div>
          <div className="grid gap-3 md:grid-cols-3">
            {steps.map((step, index) => {
              const Icon = step.icon;
              return (
                <div key={step.title} className="rounded-md border border-border p-4">
                  <div className="flex items-center gap-2">
                    <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted">
                      <Icon className="h-4 w-4" />
                    </div>
                    <span className="text-sm font-medium">步骤 {index + 1}</span>
                  </div>
                  <h2 className="mt-4 font-medium">{step.title}</h2>
                  <p className="mt-1 text-sm text-muted-foreground">{step.description}</p>
                </div>
              );
            })}
          </div>
          <Button onClick={() => completeMutation.mutate()} disabled={completeMutation.isPending}>
            <CheckCircle2 className="h-4 w-4" />
            浏览公司
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
