'use client';

import { useAuthStore } from '@shared/hooks';
import { useRouter } from 'next/navigation';
import { type ReactNode, useEffect } from 'react';

export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);

  useEffect(() => {
    if (!token) {
      router.replace('/login');
    }
  }, [token, router]);

  if (!token) {
    return null;
  }

  return <>{children}</>;
}
