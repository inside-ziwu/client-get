import { createBrowserRouter } from 'react-router-dom';

const hydrateFallbackElement = <></>;

export const router = createBrowserRouter([
  {
    path: '/login',
    hydrateFallbackElement,
    lazy: () => import('./pages/Login'),
  },
  {
    path: '/onboarding',
    hydrateFallbackElement,
    lazy: () => import('./pages/Onboarding'),
  },
  {
    path: '/',
    hydrateFallbackElement,
    lazy: () => import('./layouts/TenantLayout'),
    children: [
      { index: true, hydrateFallbackElement, lazy: () => import('./pages/Dashboard') },
      { path: 'dashboard', hydrateFallbackElement, lazy: () => import('./pages/Dashboard') },
      { path: 'companies', hydrateFallbackElement, lazy: () => import('./pages/Companies') },
      { path: 'curated-customers', hydrateFallbackElement, lazy: () => import('./pages/CuratedCustomers') },
      { path: 'templates', hydrateFallbackElement, lazy: () => import('./pages/Templates') },
      { path: 'send-plans', hydrateFallbackElement, lazy: () => import('./pages/SendPlans') },
      { path: 'send-plans/new', hydrateFallbackElement, lazy: () => import('./pages/SendPlans/New') },
      { path: 'send-plans/:id', hydrateFallbackElement, lazy: () => import('./pages/SendPlans/Detail') },
      { path: 'email-monitor', hydrateFallbackElement, lazy: () => import('./pages/EmailMonitor') },
      { path: 'intelligence', hydrateFallbackElement, lazy: () => import('./pages/Intelligence') },
      { path: 'settings/keywords', hydrateFallbackElement, lazy: () => import('./pages/Settings/Keywords') },
      { path: 'settings/scoring', hydrateFallbackElement, lazy: () => import('./pages/Settings/Scoring') },
      { path: 'settings/contact-rules', hydrateFallbackElement, lazy: () => import('./pages/Settings/ContactRules') },
      { path: 'settings/ai-provider', hydrateFallbackElement, lazy: () => import('./pages/Settings/AIProvider') },
      { path: 'settings/team', hydrateFallbackElement, lazy: () => import('./pages/Settings/Team') },
    ],
  },
]);
