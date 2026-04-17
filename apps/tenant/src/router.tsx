import { createBrowserRouter } from 'react-router-dom';

export const router = createBrowserRouter([
  {
    path: '/login',
    lazy: () => import('./pages/Login'),
  },
  {
    path: '/onboarding',
    lazy: () => import('./pages/Onboarding'),
  },
  {
    path: '/',
    lazy: () => import('./layouts/TenantLayout'),
    children: [
      { index: true, lazy: () => import('./pages/Dashboard') },
      { path: 'dashboard', lazy: () => import('./pages/Dashboard') },
      { path: 'companies', lazy: () => import('./pages/Companies') },
      { path: 'curated-customers', lazy: () => import('./pages/CuratedCustomers') },
      { path: 'templates', lazy: () => import('./pages/Templates') },
      { path: 'send-plans', lazy: () => import('./pages/SendPlans') },
      { path: 'send-plans/new', lazy: () => import('./pages/SendPlans/New') },
      { path: 'send-plans/:id', lazy: () => import('./pages/SendPlans/Detail') },
      { path: 'email-monitor', lazy: () => import('./pages/EmailMonitor') },
      { path: 'intelligence', lazy: () => import('./pages/Intelligence') },
      { path: 'settings/keywords', lazy: () => import('./pages/Settings/Keywords') },
      { path: 'settings/scoring', lazy: () => import('./pages/Settings/Scoring') },
      { path: 'settings/contact-rules', lazy: () => import('./pages/Settings/ContactRules') },
      { path: 'settings/ai-balance', lazy: () => import('./pages/Settings/AIBalance') },
      { path: 'settings/team', lazy: () => import('./pages/Settings/Team') },
    ],
  },
]);
