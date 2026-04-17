import { createBrowserRouter } from 'react-router-dom';

export const router = createBrowserRouter([
  {
    path: '/login',
    lazy: () => import('./pages/Login'),
  },
  {
    path: '/',
    lazy: () => import('./layouts/AdminLayout'),
    children: [
      { index: true, lazy: () => import('./pages/DataSources') },
      { path: 'data-sources', lazy: () => import('./pages/DataSources') },
      { path: 'scoring-templates', lazy: () => import('./pages/ScoringTemplates') },
      { path: 'intelligence-sources', lazy: () => import('./pages/IntelligenceSources') },
      { path: 'email-templates', lazy: () => import('./pages/EmailTemplates') },
      { path: 'warmup-rules', lazy: () => import('./pages/WarmupRules') },
      { path: 'ai-config', lazy: () => import('./pages/AIConfig') },
      { path: 'tenants', lazy: () => import('./pages/Tenants') },
    ],
  },
]);
