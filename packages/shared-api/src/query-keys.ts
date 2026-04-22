import { useAuthStore } from '@shared/hooks';

function tenantScope() {
  const { payload } = useAuthStore.getState();
  return payload?.tid ?? 'unknown';
}

export const queryKeys = {
  // ── Tenant keys ──
  companies: {
    all: () => ['tenant', tenantScope(), 'companies'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.companies.all(), 'list', filters] as const,
    detail: (id: string) => [...queryKeys.companies.all(), 'detail', id] as const,
  },
  prospects: {
    all: () => ['tenant', tenantScope(), 'prospects'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.prospects.all(), 'list', filters] as const,
  },
  groups: {
    all: () => ['tenant', tenantScope(), 'groups'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.groups.all(), 'list', filters] as const,
    detail: (id: string) => [...queryKeys.groups.all(), 'detail', id] as const,
  },
  sendingPlans: {
    all: () => ['tenant', tenantScope(), 'sendingPlans'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.sendingPlans.all(), 'list', filters] as const,
    detail: (id: string) => [...queryKeys.sendingPlans.all(), 'detail', id] as const,
  },
  emails: {
    all: () => ['tenant', tenantScope(), 'emails'] as const,
    stats: (filters?: Record<string, unknown>) => [...queryKeys.emails.all(), 'stats', filters] as const,
    trend: (filters?: Record<string, unknown>) => [...queryKeys.emails.all(), 'trend', filters] as const,
    aiAnalysis: (filters?: Record<string, unknown>) => [...queryKeys.emails.all(), 'aiAnalysis', filters] as const,
  },
  intelligence: {
    all: () => ['tenant', tenantScope(), 'intelligence'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.intelligence.all(), 'list', filters] as const,
    subscriptions: () => [...queryKeys.intelligence.all(), 'subscriptions'] as const,
  },
  emailTemplates: {
    all: () => ['tenant', tenantScope(), 'emailTemplates'] as const,
    list: (filters?: Record<string, unknown>) => [...queryKeys.emailTemplates.all(), 'list', filters] as const,
    detail: (id: string) => [...queryKeys.emailTemplates.all(), 'detail', id] as const,
  },
  dashboard: {
    all: () => ['tenant', tenantScope(), 'dashboard'] as const,
    overview: () => [...queryKeys.dashboard.all(), 'overview'] as const,
    funnel: () => [...queryKeys.dashboard.all(), 'funnel'] as const,
    aiCapabilities: () => [...queryKeys.dashboard.all(), 'aiCapabilities'] as const,
  },
  aiProvider: {
    all: () => ['tenant', tenantScope(), 'aiProvider'] as const,
    openrouter: () => [...queryKeys.aiProvider.all(), 'openrouter'] as const,
    usageSummary: (period?: string) => [...queryKeys.aiProvider.all(), 'usageSummary', period] as const,
    usageTrend: (filters?: Record<string, unknown>) => [...queryKeys.aiProvider.all(), 'usageTrend', filters] as const,
  },
  notifications: {
    all: () => ['tenant', tenantScope(), 'notifications'] as const,
    unread: () => [...queryKeys.notifications.all(), 'unread'] as const,
  },
  keywords: {
    all: () => ['tenant', tenantScope(), 'keywords'] as const,
    list: () => [...queryKeys.keywords.all(), 'list'] as const,
  },
  scoring: {
    all: () => ['tenant', tenantScope(), 'scoring'] as const,
  },
  contactRules: {
    all: () => ['tenant', tenantScope(), 'contactRules'] as const,
  },
  team: {
    all: () => ['tenant', tenantScope(), 'team'] as const,
    list: () => [...queryKeys.team.all(), 'list'] as const,
  },

  // ── Admin keys ──
  admin: {
    dataSources: {
      all: () => ['admin', 'dataSources'] as const,
      list: () => [...queryKeys.admin.dataSources.all(), 'list'] as const,
      credentials: (type: string) => [...queryKeys.admin.dataSources.all(), 'credentials', type] as const,
    },
    scoringTemplates: {
      all: () => ['admin', 'scoringTemplates'] as const,
      list: () => [...queryKeys.admin.scoringTemplates.all(), 'list'] as const,
      detail: (id: string) => [...queryKeys.admin.scoringTemplates.all(), 'detail', id] as const,
    },
    intelligenceSources: {
      all: () => ['admin', 'intelligenceSources'] as const,
      list: () => [...queryKeys.admin.intelligenceSources.all(), 'list'] as const,
      detail: (id: string) => [...queryKeys.admin.intelligenceSources.all(), 'detail', id] as const,
    },
    emailTemplates: {
      all: () => ['admin', 'emailTemplates'] as const,
      list: () => [...queryKeys.admin.emailTemplates.all(), 'list'] as const,
      detail: (id: string) => [...queryKeys.admin.emailTemplates.all(), 'detail', id] as const,
    },
    warmupRules: {
      all: () => ['admin', 'warmupRules'] as const,
    },
    aiConfig: {
      all: () => ['admin', 'aiConfig'] as const,
      models: () => [...queryKeys.admin.aiConfig.all(), 'models'] as const,
      pricing: () => [...queryKeys.admin.aiConfig.all(), 'pricing'] as const,
      sceneDefaults: () => [...queryKeys.admin.aiConfig.all(), 'sceneDefaults'] as const,
    },
    tenants: {
      all: () => ['admin', 'tenants'] as const,
      list: (filters?: Record<string, unknown>) => [...queryKeys.admin.tenants.all(), 'list', filters] as const,
      detail: (id: string) => [...queryKeys.admin.tenants.all(), 'detail', id] as const,
      domains: (id: string) => [...queryKeys.admin.tenants.all(), id, 'domains'] as const,
      team: (id: string) => [...queryKeys.admin.tenants.all(), id, 'team'] as const,
      aiProvider: (id: string) => [...queryKeys.admin.tenants.all(), id, 'aiProvider'] as const,
    },
  },
} as const;
