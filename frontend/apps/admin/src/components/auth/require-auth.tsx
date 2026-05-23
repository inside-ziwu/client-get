'use client';

import { useAuthStore } from '@shared/hooks';
import { useRouter } from 'next/navigation';
import { type ReactNode, useEffect, useRef, useState } from 'react';

export function RequireAuth({ children }: { children: ReactNode }) {
  const router = useRouter();
  const token = useAuthStore((state) => state.token);
  const isExpired = useAuthStore((state) => state.isExpired);
  const setToken = useAuthStore((state) => state.setToken);
  const logout = useAuthStore((state) => state.logout);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshAttempted = useRef(false);

  useEffect(() => {
    if (!token) {
      router.replace('/login');
      return;
    }

    if (!isExpired()) {
      return;
    }

    if (refreshAttempted.current || isRefreshing) {
      return;
    }

    refreshAttempted.current = true;
    setIsRefreshing(true);

    const apiBase = process.env.NEXT_PUBLIC_ADMIN_API_BASE_URL ?? '';
    fetch(`${apiBase}/admin/api/v1/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    })
      .then((res) => {
        if (!res.ok) throw new Error('refresh failed');
        return res.json();
      })
      .then((data) => {
        const newToken: string = data.data.access_token;
        setToken(newToken);
        return fetch('/api/auth/set-token', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ token: newToken }),
        });
      })
      .catch(() => {
        logout();
        router.replace('/login');
      })
      .finally(() => {
        setIsRefreshing(false);
      });
  }, [token, isExpired, setToken, logout, router, isRefreshing]);

  if (!token || (isExpired() && !isRefreshing)) {
    return null;
  }

  return <>{children}</>;
}
