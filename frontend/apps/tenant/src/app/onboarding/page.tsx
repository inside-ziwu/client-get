'use client';

import { useMutation } from '@tanstack/react-query';
import { CheckCircle2, KeyRound, Mail, Settings } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { Button, Card, CardContent } from '@shared/ui';
import { toast } from 'sonner';
import { tenantApi } from '@/lib/api';

const steps = [
  { title: '确认账号', description: '完成租户账号和登录信息检查。', icon: KeyRound },
  { title: '配置关键词', description: '建立客户采集关键词。', icon: Settings },
  { title: '准备邮件', description: '维护模板、域名和发送计划。', icon: Mail },
];

export default function OnboardingPage() {
  const router = useRouter();
  const completeMutation = useMutation({
    mutationFn: async () => (await tenantApi.onboarding.complete()).data.data,
    onSuccess: () => {
      toast.success('引导已完成');
      router.replace('/');
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
            完成并进入工作台
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
