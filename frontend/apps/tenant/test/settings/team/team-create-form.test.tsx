import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { type Mock, beforeEach, describe, expect, it, vi } from 'vitest';
import { toast } from 'sonner';

// mock tenantApi
vi.mock('@/lib/api', () => ({
  tenantApi: {
    team: {
      list: vi.fn().mockResolvedValue({ data: { data: [] } }),
      create: vi.fn().mockResolvedValue({ data: { data: { id: '1' } } }),
    },
  },
}));

// mock useAuthStore
vi.mock('@shared/hooks', () => ({
  useAuthStore: Object.assign(
    (selector: (s: unknown) => unknown) => selector({ payload: { sub: 'current-user-id', tid: 't1' }, token: 'token', isExpired: false, hasHydrated: true }),
    { getState: () => ({ payload: { sub: 'current-user-id', tid: 't1' }, token: 'token', isExpired: false, hasHydrated: true }) },
  ),
}));

// mock sonner
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

function getForm() {
  return document.querySelector('form')!;
}

function submitForm() {
  const form = getForm();
  fireEvent.submit(form);
}

describe('创建表单 - 角色选择', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.team.list as Mock).mockResolvedValue({ data: { data: [] } });
    (tenantApi.team.create as Mock).mockResolvedValue({ data: { data: { id: 'new-1' } } });
  });

  it('表单渲染包含角色 Label', () => {
    renderWithProviders();
    const form = getForm();
    expect(form.textContent).toContain('角色');
  });

  it('新增成员操作框中姓名和角色使用 small，邮箱使用 medium', () => {
    renderWithProviders();

    expect(screen.getByLabelText('姓名').parentElement).toHaveClass(
      'sm:w-ui-control-small',
    );
    expect(screen.getByLabelText('邮箱').parentElement).toHaveClass(
      'sm:w-ui-control-medium',
    );
    expect(within(getForm()).getByText('角色').parentElement).toHaveClass(
      'sm:w-ui-control-small',
    );
  });

  it('提交时携带默认角色 operator', async () => {
    renderWithProviders();
    const nameInput = document.getElementById('member-name') as HTMLInputElement;
    const emailInput = document.getElementById('member-email') as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: '测试用户' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    submitForm();

    await waitFor(() => {
      expect(tenantApi.team.create).toHaveBeenCalledWith(
        expect.objectContaining({ roles: ['operator'] }),
      );
    });
  });

  it('创建失败时显示 toast.error', async () => {
    (tenantApi.team.create as Mock).mockRejectedValueOnce(new Error('创建失败'));
    renderWithProviders();
    const nameInput = document.getElementById('member-name') as HTMLInputElement;
    const emailInput = document.getElementById('member-email') as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: '测试用户' } });
    fireEvent.change(emailInput, { target: { value: 'test@example.com' } });
    submitForm();

    await waitFor(() => {
      expect(toast.error).toHaveBeenCalledWith('创建失败');
    });
  });
});
