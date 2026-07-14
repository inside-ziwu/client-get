import { fireEvent, render, screen, within } from '@testing-library/react';
import type { ComponentPropsWithoutRef, ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { DashboardShell } from '../src/components/dashboard-shell';

type TestLinkProps = Omit<ComponentPropsWithoutRef<'a'>, 'onClick'> & {
  href: string;
  children: ReactNode;
  onClick?: () => void;
};

const groups = [
  {
    label: '工作台',
    items: [
      {
        href: '/dashboard',
        label: '仪表盘',
        icon: ({ className }: { className?: string }) => (
          <svg aria-hidden="true" className={className} />
        ),
      },
    ],
  },
];

function renderShell(onPrefetch = vi.fn()) {
  render(
    <DashboardShell
      brand="ClientGet"
      currentPath="/dashboard"
      groups={groups}
      headerActions={<span>当前用户</span>}
      homeHref="/dashboard"
      onPrefetch={onPrefetch}
      renderLink={({ href, onClick, ...props }: TestLinkProps) => (
        <a
          href={href}
          onClick={(event) => {
            event.preventDefault();
            onClick?.();
          }}
          {...props}
        />
      )}
      title="后台管理"
    >
      <div>页面内容</div>
    </DashboardShell>,
  );

  return { onPrefetch };
}

describe('DashboardShell', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('点击移动端菜单按钮后打开可访问的导航抽屉', async () => {
    renderShell();

    fireEvent.click(screen.getByRole('button', { name: '打开导航' }));

    const dialog = await screen.findByRole('dialog', { name: '主导航' });
    expect(within(dialog).getByRole('link', { name: '仪表盘' })).toBeInTheDocument();
  });

  it('点击移动端导航链接后关闭抽屉', async () => {
    renderShell();

    fireEvent.click(screen.getByRole('button', { name: '打开导航' }));
    const dialog = await screen.findByRole('dialog', { name: '主导航' });
    fireEvent.click(within(dialog).getByRole('link', { name: '仪表盘' }));

    expect(screen.queryByRole('dialog', { name: '主导航' })).not.toBeInTheDocument();
  });

  it('桌面导航保留当前页标记和折叠状态', () => {
    renderShell();

    const desktopNavigation = screen.getByRole('navigation', { name: '桌面主导航' });
    expect(within(desktopNavigation).getByRole('link', { name: '仪表盘' })).toHaveAttribute(
      'aria-current',
      'page',
    );

    fireEvent.click(screen.getByRole('button', { name: '收起侧边栏' }));
    expect(localStorage.getItem('sidebar-collapsed')).toBe('true');
  });
});
