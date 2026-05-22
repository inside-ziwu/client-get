'use client';

import { useAuthStore } from '@shared/hooks';
import { useRouter } from 'next/navigation';
import { type ReactNode, useEffect, useRef } from 'react';
import { AppShell } from '@/components/layout/app-shell';

function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const payload = useAuthStore((state) => state.payload);
  const isExpired = useAuthStore((state) => state.isExpired);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);

  // logout() 会清空 payload，但 useEffect 在清空后才触发，
  // 用 ref 缓存最后已知的 slug 避免丢失
  const lastSlugRef = useRef(payload?.slug);
  if (payload?.slug) lastSlugRef.current = payload.slug;

  useEffect(() => {
    if (!hasHydrated) return;
    if (!token || isExpired()) {
      const slug = lastSlugRef.current;
      router.replace(slug ? `/login?slug=${slug}` : '/login');
    }
  }, [hasHydrated, token, isExpired, router]);

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
