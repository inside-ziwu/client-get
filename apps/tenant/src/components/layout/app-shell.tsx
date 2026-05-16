'use client';

import { useAuthStore } from '@shared/hooks';
import { useQuery } from '@tanstack/react-query';
import { Bell, LogOut, Menu } from 'lucide-react';
import { useRouter } from 'next/navigation';
import { type ReactNode } from 'react';
import { Avatar, AvatarFallback, Button, Badge } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { Sidebar } from './sidebar';

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const payload = useAuthStore((state) => state.payload);
  const logout = useAuthStore((state) => state.logout);
  const meQuery = useQuery({
    queryKey: ['tenant', 'auth', 'me'],
    queryFn: async () => (await tenantApi.auth.me()).data.data,
  });
  const notificationsQuery = useQuery({
    queryKey: ['tenant', 'notifications', 'layout'],
    queryFn: async () => (await tenantApi.notifications.list()).data.data,
  });

  const currentUser = meQuery.data ?? {
    name: payload?.roles?.includes('admin') ? 'Tenant Admin' : 'Tenant User',
    email: payload?.slug ?? 'tenant',
  };
  const unread = (notificationsQuery.data ?? []).filter((item) => !item.is_read).length;

  const handleLogout = () => {
    const slug = payload?.slug;
    logout();
    router.replace(slug ? `/login?slug=${slug}` : '/login');
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="flex">
        <Sidebar />
        <div className="flex min-h-screen min-w-0 flex-1 flex-col">
          <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-border bg-white/95 px-4 backdrop-blur lg:px-6">
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" className="lg:hidden" aria-label="打开导航">
                <Menu className="h-4 w-4" />
              </Button>
              <div className="text-sm font-medium text-slate-700">租户工作台</div>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="ghost" size="icon" aria-label="通知" onClick={() => router.push('/')}>
                <Bell className="h-4 w-4" />
              </Button>
              {unread ? <Badge className="-ml-5 -mt-5 h-5 min-w-5 justify-center px-1">{unread}</Badge> : null}
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
