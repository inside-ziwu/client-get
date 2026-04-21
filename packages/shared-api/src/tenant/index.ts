import type { AxiosInstance } from 'axios';
import { authApi } from './auth';
import { companiesApi } from './companies';
import { prospectsApi } from './prospects';
import { groupsApi } from './groups';
import { domainsApi } from './domains';
import { emailTemplatesApi } from './email-templates';
import { sendingPlansApi } from './sending-plans';
import { emailsApi } from './emails';
import { intelligenceApi } from './intelligence';
import { keywordsApi } from './keywords';
import { onboardingApi } from './onboarding';
import { scoringApi } from './scoring';
import { contactRulesApi } from './contact-rules';
import { billingApi } from './billing';
import { teamApi } from './team';
import { notificationsApi } from './notifications';
import { dashboardApi } from './dashboard';

export function createTenantApi(client: AxiosInstance) {
  return {
    auth: authApi(client),
    companies: companiesApi(client),
    prospects: prospectsApi(client),
    groups: groupsApi(client),
    domains: domainsApi(client),
    emailTemplates: emailTemplatesApi(client),
    sendingPlans: sendingPlansApi(client),
    emails: emailsApi(client),
    intelligence: intelligenceApi(client),
    keywords: keywordsApi(client),
    onboarding: onboardingApi(client),
    scoring: scoringApi(client),
    contactRules: contactRulesApi(client),
    billing: billingApi(client),
    team: teamApi(client),
    notifications: notificationsApi(client),
    dashboard: dashboardApi(client),
  };
}

export type TenantApi = ReturnType<typeof createTenantApi>;
