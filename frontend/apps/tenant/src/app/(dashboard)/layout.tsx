'use client';

import { useAuthStore } from '@shared/hooks';
import { useRouter } from 'next/navigation';
import { type ReactNode, useEffect } from 'react';
import { AppShell } from '@/components/layout/app-shell';

function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const payload = useAuthStore((state) => state.payload);
  const isExpired = useAuthStore((state) => state.isExpired);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);

  useEffect(() => {
    if (!hasHydrated) return;
    if (!token || isExpired()) {
      router.replace(payload?.slug ? `/login?slug=${payload.slug}` : '/login');
    }
  }, [hasHydrated, token, payload?.slug, isExpired, router]);

  if (!hasHydrated || !token || isExpired()) return null;
  return <>{children}</>;
}

export default function DashboardLayout({ children }: { children: ReactNode }) {
  return (
    <RequireAuth>
      <AppShell>{children}</AppShell>
    </RequireAuth>
  );
}
