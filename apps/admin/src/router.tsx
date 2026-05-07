import { createBrowserRouter } from 'react-router-dom';

const hydrateFallbackElement = <></>;

export const router = createBrowserRouter([
  {
    path: '/login',
    hydrateFallbackElement,
    lazy: () => import('./pages/Login'),
  },
  {
    path: '/',
    hydrateFallbackElement,
    lazy: () => import('./layouts/AdminLayout'),
    children: [
      { index: true, hydrateFallbackElement, lazy: () => import('./pages/DataSources') },
      { path: 'data-sources', hydrateFallbackElement, lazy: () => import('./pages/DataSources') },
      { path: 'scoring-templates', hydrateFallbackElement, lazy: () => import('./pages/ScoringTemplates') },
      { path: 'intelligence-sources', hydrateFallbackElement, lazy: () => import('./pages/IntelligenceSources') },
      { path: 'email-templates', hydrateFallbackElement, lazy: () => import('./pages/EmailTemplates') },
      { path: 'warmup-rules', hydrateFallbackElement, lazy: () => import('./pages/WarmupRules') },
      { path: 'ai-config', hydrateFallbackElement, lazy: () => import('./pages/AIConfig') },
      { path: 'tenants', hydrateFallbackElement, lazy: () => import('./pages/Tenants') },
      { path: 'collection-tasks', hydrateFallbackElement, lazy: () => import('./pages/CollectionTasks') },
      {
        path: 'collection/tendata',
        hydrateFallbackElement,
        lazy: async () => {
          const { TendataComponent } = await import('./pages/CollectionArchive');
          return { Component: TendataComponent };
        },
      },
      {
        path: 'collection/customers',
        hydrateFallbackElement,
        lazy: async () => {
          const { CustomersComponent } = await import('./pages/CollectionArchive');
          return { Component: CustomersComponent };
        },
      },
      {
        path: 'collection/peers',
        hydrateFallbackElement,
        lazy: () => import('./pages/PeersData'),
      },
      { path: 'contact-classification', hydrateFallbackElement, lazy: () => import('./pages/ContactClassification') },
    ],
  },
]);
