'use client';

import { CircleAlert, RefreshCw, RotateCcw } from 'lucide-react';
import { useEffect } from 'react';
import { Button } from './button';

export interface RouteErrorStateProps {
  onReload: () => void;
  onRetry: () => void;
}

export interface RouteErrorBoundaryProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export function RouteErrorBoundary({ error, reset }: RouteErrorBoundaryProps) {
  useEffect(() => {
    console.error('[路由错误]', error);
  }, [error]);

  return <RouteErrorState onReload={() => window.location.reload()} onRetry={reset} />;
}

export function RouteErrorState({ onReload, onRetry }: RouteErrorStateProps) {
  return (
    <div className="flex min-h-[60vh] items-center justify-center px-4" role="alert">
      <div className="w-full max-w-md text-center">
        <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
          <CircleAlert aria-hidden="true" className="h-6 w-6" />
        </div>
        <h2 className="mt-4 text-xl font-semibold text-slate-950">页面加载失败</h2>
        <p className="mt-2 text-sm text-muted-foreground">
          暂时无法显示当前页面。请重试，或刷新页面后继续。
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Button onClick={onRetry} type="button">
            <RotateCcw aria-hidden="true" className="h-4 w-4" />
            重试
          </Button>
          <Button onClick={onReload} type="button" variant="outline">
            <RefreshCw aria-hidden="true" className="h-4 w-4" />
            刷新页面
          </Button>
        </div>
      </div>
    </div>
  );
}
