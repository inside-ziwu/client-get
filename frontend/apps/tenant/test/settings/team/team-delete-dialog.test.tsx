import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { type Mock, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'sonner';

const MOCK_USERS = [
  { id: 'other-user-1', email: 'other@test.com', name: '其他用户', roles: ['operator'], status: 'active', created_at: '2026-01-01', last_login_at: '2026-05-22T10:00:00Z' },
];

vi.mock('@/lib/api', () => ({
  tenantApi: {
    team: {
      list: vi.fn().mockResolvedValue({ data: { data: [] } }),
      create: vi.fn(),
      update: vi.fn().mockResolvedValue({ data: { data: {} } }),
      delete: vi.fn().mockResolvedValue({}),
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

async function openDeleteDialog() {
  const deleteBtns = await screen.findAllByText('删除');
  fireEvent.click(deleteBtns[0]);
  await waitFor(() => {
    expect(document.querySelector('[role="alertdialog"]')).toBeTruthy();
  });
  return document.querySelector('[role="alertdialog"]') as HTMLElement;
}

describe('删除确认对话框', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.team.list as Mock).mockResolvedValue({ data: { data: MOCK_USERS } });
    (tenantApi.team.delete as Mock).mockResolvedValue({});
  });

  afterEach(() => {
    cleanup();
  });

  it('点击删除后弹出确认对话框，显示确认文案', async () => {
    renderWithProviders();
    const dialog = await openDeleteDialog();
    expect(within(dialog).getByText(/确认删除成员/)).toBeInTheDocument();
    expect(within(dialog).getByText(/其他用户/)).toBeInTheDocument();
  });

  it('确认删除后调用 delete API', async () => {
    renderWithProviders();
    const dialog = await openDeleteDialog();
    const confirmBtn = within(dialog).getByText('确认删除');
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(tenantApi.team.delete).toHaveBeenCalledWith('other-user-1');
    });
  });

  it('删除成功后显示 toast.success', async () => {
    renderWithProviders();
    const dialog = await openDeleteDialog();
    const confirmBtn = within(dialog).getByText('确认删除');
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('成员已删除');
    });
  });

  it('删除失败后显示 toast.error', async () => {
    (tenantApi.team.delete as Mock).mockRejectedValueOnce(new Error('删除失败'));
    renderWithProviders();
    const dialog = await openDeleteDialog();
    const confirmBtn = within(dialog).getByText('确认删除');
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('删除失败');
    });
  });

  it('点击取消后对话框关闭，不调用 API', async () => {
    renderWithProviders();
    const dialog = await openDeleteDialog();
    const cancelBtn = within(dialog).getByText('取消');
    fireEvent.click(cancelBtn);

    await waitFor(() => {
      expect(document.querySelector('[role="alertdialog"]')).toBeNull();
    });
    expect(tenantApi.team.delete).not.toHaveBeenCalled();
  });
});
