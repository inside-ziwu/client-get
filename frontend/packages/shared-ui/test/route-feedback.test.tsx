import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { RouteErrorBoundary, RouteErrorState } from '../src/components/route-error-state';
import { RouteLoadingState } from '../src/components/route-loading-state';

describe('RouteErrorState', () => {
  it('提供重试和刷新两种恢复动作', () => {
    const onRetry = vi.fn();
    const onReload = vi.fn();
    render(<RouteErrorState onReload={onReload} onRetry={onRetry} />);

    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    fireEvent.click(screen.getByRole('button', { name: '刷新页面' }));

    expect(onRetry).toHaveBeenCalledOnce();
    expect(onReload).toHaveBeenCalledOnce();
  });

  it('只展示通用错误说明，不接收或暴露原始异常', () => {
    render(<RouteErrorState onReload={vi.fn()} onRetry={vi.fn()} />);

    expect(screen.getByRole('alert')).toHaveTextContent('页面加载失败');
    expect(screen.getByRole('alert')).toHaveTextContent('请重试，或刷新页面后继续');
  });
});

describe('RouteErrorBoundary', () => {
  it('隐藏原始异常并通过 reset 恢复当前路由', () => {
    const reset = vi.fn();
    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => undefined);

    render(<RouteErrorBoundary error={new Error('内部接口地址')} reset={reset} />);
    fireEvent.click(screen.getByRole('button', { name: '重试' }));

    expect(reset).toHaveBeenCalledOnce();
    expect(screen.queryByText('内部接口地址')).not.toBeInTheDocument();
    consoleError.mockRestore();
  });
});

describe('RouteLoadingState', () => {
  it('提供可访问的路由加载状态', () => {
    render(<RouteLoadingState />);

    expect(screen.getByRole('status', { name: '页面加载中' })).toBeInTheDocument();
  });
});
