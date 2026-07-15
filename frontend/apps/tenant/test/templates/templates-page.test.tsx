import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { type Mock, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/api', () => ({
  tenantApi: {
    auth: { updateTestEmail: vi.fn() },
    emailTemplates: {
      list: vi.fn(),
      detail: vi.fn(),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      clone: vi.fn(),
      preview: vi.fn(),
      testSend: vi.fn(),
      aiGenerate: vi.fn(),
      platformTemplates: {
        list: vi.fn(),
        copy: vi.fn(),
      },
    },
  },
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import TemplatesPage from '@/app/(dashboard)/templates/page';
import { tenantApi } from '@/lib/api';

const ownTemplate = {
  id: 'template-1',
  name: 'PCB 开发信',
  subject: 'Hello PCB',
  body_html: '<p>Hello</p>',
  source_type: 'custom',
  variables: [],
  created_at: '2026-07-14T12:00:00Z',
  updated_at: '2026-07-15T12:00:00Z',
};

const platformTemplate = {
  id: 'platform-1',
  name: '平台 PCB 模板',
  subject: 'Platform PCB',
  created_at: '2026-07-14T12:00:00Z',
  updated_at: '2026-07-15T12:00:00Z',
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <TemplatesPage />
    </QueryClientProvider>,
  );
}

describe('TemplatesPage 双列表模式迁移', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.emailTemplates.list as Mock).mockResolvedValue({ data: { data: [ownTemplate] } });
    (tenantApi.emailTemplates.platformTemplates.list as Mock).mockResolvedValue({ data: { data: [platformTemplate] } });
  });

  afterEach(() => cleanup());

  it('保留双 Tab，并为两个列表提供独立具名表格', async () => {
    renderPage();

    expect(await screen.findByRole('table', { name: '我的模板列表' })).toBeInTheDocument();
    fireEvent.mouseDown(screen.getByRole('tab', { name: '平台模板库' }), { button: 0, ctrlKey: false });
    expect(await screen.findByRole('table', { name: '平台模板列表' })).toBeInTheDocument();
  });

  it('我的模板操作使用文字且在操作列居中', async () => {
    renderPage();
    expect(await screen.findByText('PCB 开发信')).toBeInTheDocument();

    for (const action of ['预览', '编辑', '克隆', '发送测试', '删除']) {
      expect(screen.getByRole('button', { name: action })).toHaveTextContent(action);
    }
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveClass('text-center');
  });

  it('我的模板加载失败时提供可重试状态', async () => {
    (tenantApi.emailTemplates.list as Mock).mockRejectedValueOnce(new Error('network'));
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('我的模板加载失败');
    expect(screen.getByRole('button', { name: '重试' })).toBeInTheDocument();
  });
});
