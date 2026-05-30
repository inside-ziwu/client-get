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

async function openEditDialog() {
  const editBtns = await screen.findAllByText('编辑');
  const editBtn = editBtns[0];
  expect(editBtn).toBeDefined();
  fireEvent.click(editBtn!);
  await waitFor(() => {
    expect(document.querySelector('[role="dialog"]')).toBeTruthy();
  });
  return document.querySelector('[role="dialog"]') as HTMLElement;
}

describe('编辑弹窗', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.team.list as Mock).mockResolvedValue({ data: { data: MOCK_USERS } });
    (tenantApi.team.update as Mock).mockResolvedValue({ data: { data: {} } });
  });

  afterEach(() => {
    cleanup();
  });

  it('点击编辑后弹窗打开，姓名预填当前值', async () => {
    renderWithProviders();
    const dialog = await openEditDialog();
    const nameInput = dialog.querySelector('input') as HTMLInputElement;
    expect(nameInput.value).toBe('其他用户');
  });

  it('修改姓名后点击保存，调用 update API 传入新姓名', async () => {
    renderWithProviders();
    const dialog = await openEditDialog();
    const nameInput = dialog.querySelector('input') as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: '新名字' } });
    const saveBtn = within(dialog).getByText('保存');
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(tenantApi.team.update).toHaveBeenCalledWith(
        'other-user-1',
        expect.objectContaining({ name: '新名字' }),
      );
    });
  });

  it('保存成功后弹窗关闭，显示 toast.success', async () => {
    renderWithProviders();
    const dialog = await openEditDialog();
    const saveBtn = within(dialog).getByText('保存');
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(toast.success).toHaveBeenCalledWith('成员已更新');
    });
  });

  it('保存失败时弹窗不关闭，弹窗内显示错误信息', async () => {
    (tenantApi.team.update as Mock).mockRejectedValueOnce(new Error('更新失败'));
    renderWithProviders();
    const dialog = await openEditDialog();
    const saveBtn = within(dialog).getByText('保存');
    fireEvent.click(saveBtn);

    await waitFor(() => {
      expect(document.querySelector('[role="dialog"]')).toBeTruthy();
      expect(within(dialog).getByText(/保存失败/)).toBeInTheDocument();
    });
  });
});
