'use client';

import axios from 'axios';
import { useAuthStore } from '@shared/hooks';
import { Button, Card, CardContent, CardHeader, CardTitle, Input, Label } from '@shared/ui';
import { Loader2 } from 'lucide-react';
import { useRouter, useSearchParams } from 'next/navigation';
import { Suspense, type FormEvent, useState } from 'react';
import { toast } from 'sonner';
import type { ApiResponse, CurrentUser, LoginResponse } from '@shared/types';

function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const slug = searchParams.get('slug')?.trim() || null;
  const setToken = useAuthStore((state) => state.setToken);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const submittedEmail = String(formData.get('email') ?? '').trim();
    const submittedPassword = String(formData.get('password') ?? '');
    setLoading(true);
    try {
      const baseURL = process.env.NEXT_PUBLIC_API_BASE_URL ?? '';
      const response = await axios.post<ApiResponse<LoginResponse>>(`${baseURL}/t/${slug}/api/v1/auth/login`, {
        slug,
        email: submittedEmail,
        password: submittedPassword,
      }, {
        timeout: 15_000,
      });
      const token = response.data.data.access_token;
      setToken(token);
      const meResponse = await axios.get<ApiResponse<CurrentUser>>(`${baseURL}/t/${slug}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${token}` },
        timeout: 15_000,
      });
      const me = meResponse.data.data;
      toast.success('登录成功');
      router.replace(me.must_change_pwd || me.needs_onboarding ? '/onboarding' : '/');
    } catch (error) {
      if (axios.isAxiosError(error)) {
        const diagnostic = {
          status: error.response?.status,
          data: error.response?.data,
          url: error.config?.url,
          message: error.message,
        };
        console.error('Tenant login failed', diagnostic);
        toast.error(error.response?.status === 401 ? '账号或密码错误，请重试' : '登录后获取账号信息失败，请稍后重试');
        return;
      }
      console.error('Tenant login failed', error);
      toast.error('登录失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  if (!slug) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background p-6">
        <Card className="w-full max-w-md">
          <CardHeader>
            <CardTitle className="text-center text-xl">无法访问</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-center text-muted-foreground">请通过正确的链接访问登录页面</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-6">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-center text-xl">登录</CardTitle>
        </CardHeader>
        <CardContent>
          <form className="space-y-4" onSubmit={onSubmit}>
            <div className="space-y-2">
              <Label htmlFor="email">邮箱</Label>
              <Input id="email" name="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" autoFocus />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                name="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete="current-password"
              />
            </div>
            <Button type="submit" className="w-full" disabled={loading}>
              {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
              登录
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground">加载中...</div>}>
      <LoginForm />
    </Suspense>
  );
}
