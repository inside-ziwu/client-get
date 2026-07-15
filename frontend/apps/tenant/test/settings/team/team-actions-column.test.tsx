import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, render, screen, within } from '@testing-library/react';
import { type Mock, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const MOCK_USERS = [
  { id: 'current-user-id', email: 'me@test.com', name: '当前用户', roles: ['admin'], status: 'active', created_at: '2026-01-01', last_login_at: '2026-05-23T14:00:00Z' },
  { id: 'other-user-1', email: 'other@test.com', name: '其他用户', roles: ['operator'], status: 'active', created_at: '2026-01-01', last_login_at: '2026-05-22T10:00:00Z' },
  { id: 'other-user-2', email: 'disabled@test.com', name: '禁用用户', roles: ['readonly'], status: 'disabled', created_at: '2026-01-01', last_login_at: null },
];

// mock tenantApi
vi.mock('@/lib/api', () => ({
  tenantApi: {
    team: {
      list: vi.fn().mockResolvedValue({ data: { data: [] } }),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
  },
}));

// mock useAuthStore — 当前用户 sub = 'current-user-id'
vi.mock('@shared/hooks', () => ({
  useAuthStore: Object.assign(
    (selector: (s: unknown) => unknown) => selector({ payload: { sub: 'current-user-id', tid: 't1' }, token: 'token', isExpired: false, hasHydrated: true }),
    { getState: () => ({ payload: { sub: 'current-user-id', tid: 't1' }, token: 'token', isExpired: false, hasHydrated: true }) },
  ),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { tenantApi } from '@/lib/api';
import TeamPage from '@/app/(dashboard)/settings/team/page';

function renderWithProviders() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <TeamPage />
    </QueryClientProvider>,
  );
}

describe('操作列与自保护逻辑', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.team.list as Mock).mockResolvedValue({ data: { data: MOCK_USERS } });
  });

  afterEach(() => cleanup());

  it('当前用户行渲染「当前账号」文本，不渲染操作按钮', async () => {
    renderWithProviders();
    expect(await screen.findByRole('table', { name: '团队成员列表' })).toBeInTheDocument();
    // 等待数据加载
    const currentRow = await screen.findByText('当前账号');
    expect(currentRow).toBeInTheDocument();

    // 当前用户行不应有编辑/删除/禁用按钮
    const row = currentRow.closest('tr')!;
    expect(within(row).queryByText('编辑')).toBeNull();
    expect(within(row).queryByText('删除')).toBeNull();
    expect(within(row).queryByText('禁用')).toBeNull();
  });

  it('非当前用户（已激活）行渲染编辑、禁用、删除三个按钮', async () => {
    renderWithProviders();
    const otherName = await screen.findByText('其他用户');
    const row = otherName.closest('tr')!;
    expect(within(row).getByText('编辑')).toBeInTheDocument();
    expect(within(row).getByText('禁用')).toBeInTheDocument();
    expect(within(row).getByText('删除')).toBeInTheDocument();
  });

  it('已禁用成员行的按钮文案为「启用」', async () => {
    renderWithProviders();
    const disabledName = await screen.findByText('禁用用户');
    const row = disabledName.closest('tr')!;
    expect(within(row).getByText('启用')).toBeInTheDocument();
    expect(within(row).queryByText('禁用')).toBeNull();
  });

  it('姓名使用 medium、邮箱使用 large，短枚举、时间与操作列居中', async () => {
    renderWithProviders();
    const table = await screen.findByRole('table', { name: '团队成员列表' });
    await within(table).findByText('其他用户');

    expect(within(table).getByRole('columnheader', { name: '姓名' })).toHaveClass('w-ui-table-medium');
    expect(within(table).getByRole('columnheader', { name: '邮箱' })).toHaveClass('w-ui-table-large');
    for (const name of ['角色', '状态']) {
      expect(within(table).getByRole('columnheader', { name })).toHaveClass('w-ui-table-small', 'text-center');
    }
    for (const name of ['最近登录', '操作']) {
      expect(within(table).getByRole('columnheader', { name })).toHaveClass('text-center');
    }
  });
});
