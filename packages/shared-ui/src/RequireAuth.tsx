import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@shared/hooks';

export function RequireAuth({
  children,
  loginPath = '/login',
}: {
  children: React.ReactNode;
  loginPath?: string;
}) {
  const { token, isExpired } = useAuthStore();
  const location = useLocation();

  if (!token || isExpired()) {
    return <Navigate to={loginPath} state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
