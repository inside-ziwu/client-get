'use client';

import { useMutation } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { type FormEvent, useEffect, useState } from 'react';
import { useAuthStore } from '@shared/hooks';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@shared/ui';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import { tenantApi } from '@/lib/api';

export default function ForceChangePasswordPage() {
  const router = useRouter();
  const mustChangePwd = useAuthStore((state) => state.mustChangePwd);
  const setMustChangePwd = useAuthStore((state) => state.setMustChangePwd);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [validationError, setValidationError] = useState('');

  useEffect(() => {
    if (hasHydrated && !mustChangePwd) {
      router.replace('/');
    }
  }, [hasHydrated, mustChangePwd, router]);

  const mutation = useMutation({
    mutationFn: async () => {
      const res = await tenantApi.auth.changePassword({ current_password: currentPassword, new_password: newPassword });
      return res.data;
    },
    onSuccess: async () => {
      setMustChangePwd(false);
      toast.success('密码修改成功');
      try {
        const meRes = await tenantApi.auth.me();
        const me = meRes.data.data;
        router.replace(me.needs_onboarding ? '/onboarding' : '/');
      } catch {
        router.replace('/');
      }
    },
    onError: (error: any) => {
      const status = error?.response?.status;
      if (status === 401 || status === 400) {
        toast.error('当前密码错误');
      } else {
        toast.error('修改失败，请稍后重试');
      }
    },
  });

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setValidationError('');
    if (!currentPassword || !newPassword || !confirmPassword) {
      setValidationError('请填写所有字段');
      return;
    }
    if (newPassword.length < 8) {
      setValidationError('新密码至少 8 个字符');
      return;
    }
    if (newPassword !== confirmPassword) {
      setValidationError('两次输入的新密码不一致');
      return;
    }
    mutation.mutate();
  };

  if (!hasHydrated || !mustChangePwd) return null;

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center text-xl">修改密码</CardTitle>
          <p className="text-center text-sm text-muted-foreground">首次登录需要修改初始密码</p>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="currentPassword">当前密码</Label>
              <Input
                id="currentPassword"
                type="password"
                value={currentPassword}
                onChange={(e) => setCurrentPassword(e.target.value)}
                autoComplete="current-password"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="newPassword">新密码</Label>
              <Input
                id="newPassword"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="confirmPassword">确认新密码</Label>
              <Input
                id="confirmPassword"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                autoComplete="new-password"
              />
            </div>
            {validationError && <p className="text-sm text-destructive">{validationError}</p>}
            <Button type="submit" className="w-full" disabled={mutation.isPending}>
              {mutation.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              确认修改
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}
