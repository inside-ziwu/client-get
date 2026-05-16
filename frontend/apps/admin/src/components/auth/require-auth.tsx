'use client';

import { useAuthStore } from '@shared/hooks';
import { useRouter } from 'next/navigation';
import { type ReactNode, useEffect } from 'react';

export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const isExpired = useAuthStore((state) => state.isExpired);

  useEffect(() => {
    if (!token || isExpired()) {
      router.replace('/login');
    }
  }, [token, isExpired, router]);

  return <>{children}</>;
}
