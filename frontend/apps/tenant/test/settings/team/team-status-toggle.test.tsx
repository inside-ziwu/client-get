import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { type Mock, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'sonner';

const MOCK_USERS = [
  { id: 'current-user-id', email: 'me@test.com', name: '当前用户', roles: ['admin'], status: 'active', created_at: '2026-01-01', last_login_at: '2026-05-23T14:00:00Z' },
  { id: 'active-user', email: 'active@test.com', name: '激活用户', roles: ['operator'], status: 'active', created_at: '2026-01-01', last_login_at: '2026-05-22T10:00:00Z' },
  { id: 'disabled-user', email: 'disabled@test.com', name: '禁用用户', roles: ['readonly'], status: 'disabled', created_at: '2026-01-01', last_login_at: null },
];

vi.mock('@/lib/api', () => ({
  tenantApi: {
    team: {
      list: vi.fn().mockResolvedValue({ data: { data: [] } }),
      create: vi.fn(),
      update: vi.fn().mockResolvedValue({ data: { data: {} } }),
      delete: vi.fn(),
    },
  },
}));

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
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <TeamPage />
    </QueryClientProvider>,
  );
}

describe('状态切换', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.team.list as Mock).mockResolvedValue({ data: { data: MOCK_USERS } });
    (tenantApi.team.update as Mock).mockResolvedValue({ data: { data: {} } });
  });

  afterEach(() => {
    cleanup();
  });

  it('已激活成员点击「禁用」后调用 update API，status 参数为 disabled', async () => {
    renderWithProviders();
    const activeName = await screen.findByText('激活用户');
    const row = activeName.closest('tr')!;
    const disableBtn = within(row).getByText('禁用');
    fireEvent.click(disableBtn);

    await waitFor(() => {
      expect(tenantApi.team.update).toHaveBeenCalledWith(
        'active-user',
        { status: 'disabled' },
      );
    });
  });

  it('已禁用成员点击「启用」后调用 update API，status 参数为 active', async () => {
    renderWithProviders();
    const disabledName = await screen.findByText('禁用用户');
    const row = disabledName.closest('tr')!;
    const enableBtn = within(row).getByText('启用');
    fireEvent.click(enableBtn);

    await waitFor(() => {
      expect(tenantApi.team.update).toHaveBeenCalledWith(
        'disabled-user',
        { status: 'active' },
      );
    });
  });

  it('切换成功后显示 toast.success', async () => {
    renderWithProviders();
    const activeName = await screen.findByText('激活用户');
    const row = activeName.closest('tr')!;
    const disableBtn = within(row).getByText('禁用');
    fireEvent.click(disableBtn);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('状态已更新');
    });
  });

  it('切换失败后显示 toast.error', async () => {
    (tenantApi.team.update as Mock).mockRejectedValueOnce(new Error('更新失败'));
    renderWithProviders();
    const activeName = await screen.findByText('激活用户');
    const row = activeName.closest('tr')!;
    const disableBtn = within(row).getByText('禁用');
    fireEvent.click(disableBtn);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('状态更新失败');
    });
  });
});
