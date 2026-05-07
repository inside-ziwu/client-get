import { createBrowserRouter, useRouteError } from 'react-router-dom';

function ChunkErrorBoundary() {
  const error = useRouteError();
  const isChunkError =
    error instanceof TypeError &&
    error.message.includes('Failed to fetch dynamically imported module');

  if (isChunkError) {
    window.location.reload();
    return null;
  }

  return (
    <div style={{ padding: 40, textAlign: 'center' }}>
      <h2>页面加载失败</h2>
      <p style={{ color: '#999' }}>请刷新页面重试</p>
      <button onClick={() => window.location.reload()}>刷新</button>
    </div>
  );
}

const hydrateFallbackElement = <></>;

export const router = createBrowserRouter([
  {
    path: '/login',
    hydrateFallbackElement,
    errorElement: <ChunkErrorBoundary />,
    lazy: () => import('./pages/Login'),
  },
  {
    path: '/onboarding',
    hydrateFallbackElement,
    errorElement: <ChunkErrorBoundary />,
    lazy: () => import('./pages/Onboarding'),
  },
  {
    path: '/',
    hydrateFallbackElement,
    errorElement: <ChunkErrorBoundary />,
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
{ path: 'settings/ai-provider', hydrateFallbackElement, lazy: () => import('./pages/Settings/AIProvider') },
      { path: 'settings/team', hydrateFallbackElement, lazy: () => import('./pages/Settings/Team') },
    ],
  },
]);
