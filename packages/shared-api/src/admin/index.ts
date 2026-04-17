import type { AxiosInstance } from 'axios';
import { authApi } from './auth';
import { dataSourcesApi } from './data-sources';
import { scoringTemplatesApi } from './scoring-templates';
import { intelligenceSourcesApi } from './intelligence-sources';
import { emailTemplatesApi } from './email-templates';
import { warmupRulesApi } from './warmup-rules';
import { aiConfigApi } from './ai-config';
import { tenantsApi } from './tenants';

export function createAdminApi(client: AxiosInstance) {
  return {
    auth: authApi(client),
    dataSources: dataSourcesApi(client),
    scoringTemplates: scoringTemplatesApi(client),
    intelligenceSources: intelligenceSourcesApi(client),
    emailTemplates: emailTemplatesApi(client),
    warmupRules: warmupRulesApi(client),
    aiConfig: aiConfigApi(client),
    tenants: tenantsApi(client),
  };
}

export type AdminApi = ReturnType<typeof createAdminApi>;
