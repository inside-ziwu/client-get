import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { type Mock, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/api', () => ({
  tenantApi: {
    intelligence: {
      list: vi.fn(),
      markRead: vi.fn(),
    },
  },
}));

import IntelligencePage from '@/app/(dashboard)/intelligence/page';
import { tenantApi } from '@/lib/api';

const article = {
  publication_id: 'publication-1',
  article_id: 'article-1',
  title: 'PCB 行业快讯',
  content_summary: '摘要内容',
  ai_category: '行业动态',
  ai_relevance_score: 92,
  published_at: '2026-07-15T12:00:00Z',
  status: 'published',
  article_created_at: '2026-07-15T12:00:00Z',
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <IntelligencePage />
    </QueryClientProvider>,
  );
}

describe('IntelligencePage 列表模式迁移', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.intelligence.list as Mock).mockResolvedValue({ data: { data: [article] } });
    (tenantApi.intelligence.markRead as Mock).mockResolvedValue({});
  });

  afterEach(() => cleanup());

  it('使用具名列表表格，并统一列宽与对齐', async () => {
    renderPage();

    expect(await screen.findByRole('table', { name: '情报列表' })).toBeInTheDocument();
    expect(screen.getByRole('columnheader', { name: '标题' })).toHaveClass('w-ui-table-large');
    expect(screen.getByRole('columnheader', { name: '分类' })).toHaveClass('w-ui-table-small', 'text-center');
    expect(screen.getByRole('columnheader', { name: '相关度' })).toHaveClass('w-ui-table-small', 'text-center');
    expect(screen.getByRole('columnheader', { name: '发布时间' })).toHaveClass('w-ui-table-medium', 'text-center');
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveClass('w-ui-table-medium', 'text-center');
  });

  it('初始加载失败时提供可重试状态', async () => {
    (tenantApi.intelligence.list as Mock)
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce({ data: { data: [article] } });

    renderPage();
    expect(await screen.findByRole('alert')).toHaveTextContent('情报加载失败');
    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    expect(await screen.findByText('PCB 行业快讯')).toBeInTheDocument();
  });

  it('标记已读期间只禁用当前行操作', async () => {
    let resolveMarkRead: (() => void) | undefined;
    (tenantApi.intelligence.markRead as Mock).mockReturnValue(
      new Promise<void>((resolve) => {
        resolveMarkRead = resolve;
      }),
    );

    renderPage();
    const title = await screen.findByText('PCB 行业快讯');
    const row = title.closest('tr')!;
    fireEvent.click(within(row).getByRole('button', { name: '标记已读' }));

    await waitFor(() => expect(within(row).getByRole('button', { name: '标记已读' })).toBeDisabled());
    resolveMarkRead?.();
  });
});
