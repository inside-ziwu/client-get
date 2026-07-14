'use client';

import { useAuthStore } from '@shared/hooks';
import {
  Avatar,
  AvatarFallback,
  Badge,
  Button,
  DashboardShell,
  type DashboardShellLinkProps,
} from '@shared/ui';
import { useQuery } from '@tanstack/react-query';
import { Bell, LogOut } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { type ReactNode } from 'react';
import { tenantApi } from '@/lib/api';
import { tenantNavigationGroups } from './navigation';

function renderLink({ href, ...props }: DashboardShellLinkProps) {
  return <Link href={href} {...props} />;
}

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
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
    <DashboardShell
      brand="ClientGet"
      currentPath={pathname}
      groups={tenantNavigationGroups}
      headerActions={
        <>
          <Button variant="ghost" size="icon" aria-label="通知" onClick={() => router.push('/')}>
            <Bell className="h-4 w-4" />
          </Button>
          {unread ? (
            <Badge className="-ml-5 -mt-5 h-5 min-w-5 justify-center px-1">{unread}</Badge>
          ) : null}
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
        </>
      }
      homeHref="/"
      onPrefetch={(href) => router.prefetch(href)}
      renderLink={renderLink}
      title="租户工作台"
    >
      {children}
    </DashboardShell>
  );
}
