import { useAuthStore } from './useAuth';

type Role = 'admin' | 'operator' | 'viewer';

const PERMISSIONS: Record<string, Role[]> = {
  // Page-level
  'settings.keywords': ['admin'],
  'settings.scoring': ['admin'],
  'settings.contact-rules': ['admin'],
  'settings.team': ['admin'],
  'settings.ai-provider': ['admin'],

  // Operation-level
  'company.create': ['admin', 'operator'],
  'company.import': ['admin', 'operator'],
  'company.blacklist': ['admin', 'operator'],
  'group.create': ['admin', 'operator'],
  'template.create': ['admin', 'operator'],
  'template.ai-generate': ['admin', 'operator'],
  'plan.create': ['admin', 'operator'],
  'plan.execute': ['admin', 'operator'],
  'monitor.ai-analysis': ['admin', 'operator'],
};

export function usePermission() {
  const { payload } = useAuthStore();
  const role = payload?.roles[0] as Role | undefined;

  return {
    can: (permission: string): boolean => {
      if (!role) return false;
      const allowed = PERMISSIONS[permission];
      return allowed ? allowed.includes(role) : false;
    },
    role,
    isAdmin: role === 'admin',
    isOperator: role === 'operator',
    isViewer: role === 'viewer',
  };
}
