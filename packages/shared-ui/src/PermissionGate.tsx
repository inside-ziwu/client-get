import React from 'react';
import { usePermission } from '@shared/hooks';

export interface PermissionGateProps {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export function PermissionGate({ permission, children, fallback = null }: PermissionGateProps) {
  const { can } = usePermission();
  return can(permission) ? <>{children}</> : <>{fallback}</>;
}
