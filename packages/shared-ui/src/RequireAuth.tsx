import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '@shared/hooks';

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { token, isExpired } = useAuthStore();
  const location = useLocation();

  if (!token || isExpired()) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return <>{children}</>;
}
