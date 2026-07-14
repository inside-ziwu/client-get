'use client';

import { useAuthStore } from '@shared/hooks';
import {
  Avatar,
  AvatarFallback,
  Button,
  DashboardShell,
  type DashboardShellLinkProps,
} from '@shared/ui';
import { useQuery } from '@tanstack/react-query';
import { LogOut } from 'lucide-react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { type ReactNode } from 'react';
import { adminApi } from '@/lib/api';
import { adminNavigationGroups } from './navigation';

function renderLink({ href, ...props }: DashboardShellLinkProps) {
  return <Link href={href} {...props} />;
}

export function AppShell({ children }: { children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
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
    <DashboardShell
      brand="ClientGet"
      currentPath={pathname}
      groups={adminNavigationGroups}
      headerActions={
        <>
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
      homeHref="/data-sources"
      onPrefetch={(href) => router.prefetch(href)}
      renderLink={renderLink}
      title="后台管理"
    >
      {children}
    </DashboardShell>
  );
}
