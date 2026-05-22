import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(cleanup);

const mockReplace = vi.fn();

vi.mock('next/navigation', () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => new URLSearchParams(searchParamsValue),
}));

vi.mock('@shared/hooks', () => ({
  useAuthStore: Object.assign(vi.fn(() => vi.fn()), {
    getState: () => ({ token: null, payload: null, logout: vi.fn() }),
  }),
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

let searchParamsValue = '';

import LoginPage from '@/app/login/page';

describe('登录页带 slug', () => {
  it('不展示 slug 输入框', () => {
    searchParamsValue = 'slug=acme';
    render(<LoginPage />);
    expect(screen.queryByLabelText('租户标识')).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox', { name: /slug/i })).not.toBeInTheDocument();
  });

  it('展示邮箱和密码字段', () => {
    searchParamsValue = 'slug=acme';
    render(<LoginPage />);
    expect(screen.getByLabelText('邮箱')).toBeInTheDocument();
    expect(screen.getByLabelText('密码')).toBeInTheDocument();
  });
});

describe('无 slug 访问登录页', () => {
  it('无 slug 参数 → 展示错误提示，不展示表单', () => {
    searchParamsValue = '';
    render(<LoginPage />);
    expect(screen.getByText(/请通过正确的链接访问/)).toBeInTheDocument();
    expect(screen.queryByLabelText('邮箱')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('密码')).not.toBeInTheDocument();
  });

  it('空 slug (?slug=) → 展示错误提示，不展示表单', () => {
    searchParamsValue = 'slug=';
    render(<LoginPage />);
    expect(screen.getByText(/请通过正确的链接访问/)).toBeInTheDocument();
    expect(screen.queryByLabelText('邮箱')).not.toBeInTheDocument();
  });

  it('纯空格 slug (?slug=  ) → 展示错误提示，不展示表单', () => {
    searchParamsValue = 'slug=  ';
    render(<LoginPage />);
    expect(screen.getByText(/请通过正确的链接访问/)).toBeInTheDocument();
    expect(screen.queryByLabelText('邮箱')).not.toBeInTheDocument();
  });
});
