import type { AxiosInstance } from 'axios';
import { authApi } from './auth';
import { collectionApi } from './collection';
import { contactClassificationApi } from './contact-classification';
import { scoringTemplatesApi } from './scoring-templates';
import { intelligenceSourcesApi } from './intelligence-sources';
import { industryNewsSourcesApi } from './industry-news-sources';
import { emailTemplatesApi } from './email-templates';
import { warmupRulesApi } from './warmup-rules';
import { aiConfigApi } from './ai-config';
import { tenantsApi } from './tenants';
import { workScheduleApi } from './work-schedule';

export function createAdminApi(client: AxiosInstance) {
  return {
    auth: authApi(client),
    collection: collectionApi(client),
    contactClassification: contactClassificationApi(client),
    scoringTemplates: scoringTemplatesApi(client),
    intelligenceSources: intelligenceSourcesApi(client),
    industryNewsSources: industryNewsSourcesApi(client),
    emailTemplates: emailTemplatesApi(client),
    warmupRules: warmupRulesApi(client),
    aiConfig: aiConfigApi(client),
    tenants: tenantsApi(client),
    workSchedule: workScheduleApi(client),
  };
}

export type AdminApi = ReturnType<typeof createAdminApi>;
