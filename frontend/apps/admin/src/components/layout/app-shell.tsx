'use client';

import { useAuthStore } from '@shared/hooks';
import { useQuery } from '@tanstack/react-query';
import { LogOut, Menu } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { type ReactNode } from 'react';
import { adminApi } from '@/lib/api';
import { Avatar, AvatarFallback } from '@shared/ui';
import { Button } from '@shared/ui';
import { Sidebar } from './sidebar';

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const payload = useAuthStore((state) => state.payload);
  const logout = useAuthStore((state) => state.logout);
  const meQuery = useQuery({
    queryKey: ['admin', 'auth', 'me'],
    queryFn: async () => (await adminApi.auth.me()).data.data,
  });

  const currentUser = meQuery.data ?? {
    name: payload?.roles?.includes('platform_admin') ? 'Platform Admin' : 'Admin',
    email: 'platform-admin',
  };

  const handleLogout = async () => {
    const apiBase = process.env.NEXT_PUBLIC_ADMIN_API_BASE_URL ?? '';
    await fetch(`${apiBase}/admin/api/v1/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    }).catch(() => {});
    await fetch('/api/auth/clear-token', { method: 'POST' });
    logout();
    router.replace('/login');
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <div className="relative">
          <Sidebar />
        </div>
        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border bg-white/95 px-4 backdrop-blur lg:px-6">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="打开导航">
                <Menu className="h-4 w-4" />
              </Button>
              <div className="text-sm font-medium text-slate-700">后台管理</div>
            </div>
            <div className="flex items-center gap-3">
              <div className="hidden text-right sm:block">
                <div className="text-sm font-medium leading-5">{currentUser.name}</div>
                <div className="text-xs text-muted-foreground">{currentUser.email}</div>
              </div>
              <Avatar>
                <AvatarFallback>{currentUser.name.slice(0, 1).toUpperCase()}</AvatarFallback>
              </Avatar>
              <Button variant="outline" size="sm" onClick={handleLogout}>
                <LogOut className="h-4 w-4" />
                登出
              </Button>
            </div>
          </header>
          <main className="min-w-0 flex-1 p-4 lg:p-6">{children}</main>
        </div>
      </div>
    </div>
  );
}
