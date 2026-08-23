import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { type Mock, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('sonner', () => ({ toast: { error: vi.fn(), success: vi.fn() } }));

vi.mock('@/lib/api', () => ({
  tenantApi: {
    industryNews: {
      list: vi.fn(),
      filters: vi.fn(),
      markRead: vi.fn(),
    },
  },
}));

import IndustryNewsPage from '@/app/(dashboard)/industry-news/page';
import { tenantApi } from '@/lib/api';

const unreadItem = {
  id: 'item-1',
  title: 'PCEA 发布新一期技术期刊',
  url: 'https://pcea.net/articles/example',
  source_id: 'source-1',
  source_name: 'PCEA',
  category: 'PCB 技术 / 工程',
  lang: 'en',
  time: '2026-08-23T01:00:00Z',
  is_read: false,
  target_domain: 'pcea.net',
  is_external: false,
};

const readItem = {
  id: 'item-2',
  title: 'CPCA 发布行业统计月报',
  url: 'https://www.cpca.org.cn/news/1',
  source_id: 'source-2',
  source_name: 'CPCA 协会动态',
  category: '中国 PCB 行业',
  lang: 'zh-CN',
  time: '2026-08-22T01:00:00Z',
  is_read: true,
  target_domain: 'www.cpca.org.cn',
  is_external: false,
};

const filterOptions = {
  categories: ['PCB 技术 / 工程', '中国 PCB 行业'],
  sources: [
    { id: 'source-1', name: 'PCEA' },
    { id: 'source-2', name: 'CPCA 协会动态' },
  ],
  langs: ['en', 'zh-CN'],
  has_sources: true,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <IndustryNewsPage />
    </QueryClientProvider>,
  );
}

beforeAll(() => {
  globalThis.ResizeObserver = class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
  Element.prototype.scrollIntoView = vi.fn();
  Element.prototype.hasPointerCapture = vi.fn(() => false);
  Element.prototype.setPointerCapture = vi.fn();
  Element.prototype.releasePointerCapture = vi.fn();
});

describe('IndustryNewsPage 行业动态', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.industryNews.list as Mock).mockResolvedValue({
      data: { data: [unreadItem, readItem], pagination: { total: 2, has_more: false, cursor: null } },
    });
    (tenantApi.industryNews.filters as Mock).mockResolvedValue({ data: { data: filterOptions } });
    (tenantApi.industryNews.markRead as Mock).mockResolvedValue({
      data: { data: { item_id: 'item-1', is_read: true } },
    });
  });

  afterEach(() => cleanup());

  it('未读与已读标题使用可区分的颜色', async () => {
    renderPage();

    const unreadLink = await screen.findByRole('link', { name: 'PCEA 发布新一期技术期刊' });
    expect(unreadLink).toHaveClass('text-ui-body-strong', 'text-ui-foreground');

    const readLink = screen.getByRole('link', { name: 'CPCA 发布行业统计月报' });
    expect(readLink).toHaveClass('text-ui-muted-foreground');
  });

  it('标题以新窗口打开原文，点击后调用已读接口并即时变为已读态', async () => {
    renderPage();

    const link = await screen.findByRole('link', { name: 'PCEA 发布新一期技术期刊' });
    expect(link).toHaveAttribute('href', 'https://pcea.net/articles/example');
    expect(link).toHaveAttribute('target', '_blank');
    expect(link).toHaveAttribute('rel', 'noopener noreferrer');

    fireEvent.click(link);
    await waitFor(() => expect(tenantApi.industryNews.markRead).toHaveBeenCalledWith('item-1'));
    await waitFor(() => expect(link).toHaveClass('text-ui-muted-foreground'));

    // 已拍板口径：标记已读不 invalidate 列表，点过的行保持可见，直到下一次取数
    expect(link).toBeInTheDocument();
    expect(tenantApi.industryNews.list).toHaveBeenCalledTimes(1);
  });

  it('标记已读失败时回滚本地已读态并提示', async () => {
    (tenantApi.industryNews.markRead as Mock).mockRejectedValue(new Error('network'));
    const { toast } = await import('sonner');
    renderPage();

    const link = await screen.findByRole('link', { name: 'PCEA 发布新一期技术期刊' });
    fireEvent.click(link);
    await waitFor(() => expect(toast.error).toHaveBeenCalledWith('标记已读失败，请稍后重试'));
    // 本地已读态被回滚：标题恢复未读样式
    await waitFor(() => expect(link).toHaveClass('text-ui-foreground'));
    expect(link).not.toHaveClass('text-ui-muted-foreground');
  });

  it('筛选选项加载失败时提示并可重试，列表仍可浏览', async () => {
    (tenantApi.industryNews.filters as Mock).mockRejectedValueOnce(new Error('network'));

    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('筛选选项加载失败');
    expect(await screen.findByRole('link', { name: 'PCEA 发布新一期技术期刊' })).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    await waitFor(() => expect(tenantApi.industryNews.filters).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(screen.queryByRole('alert')).not.toBeInTheDocument());
  });

  it('本实例未配置动态源时显示说明块而不渲染表格', async () => {
    (tenantApi.industryNews.filters as Mock).mockResolvedValue({
      data: { data: { categories: [], sources: [], langs: [], has_sources: false } },
    });

    renderPage();

    expect(await screen.findByText('本实例尚未配置动态源')).toBeInTheDocument();
    expect(screen.queryByRole('table')).not.toBeInTheDocument();
  });

  it('类别多选与只看未读随查询透传为列表参数', async () => {
    renderPage();
    await screen.findByRole('table', { name: '动态列表' });

    // 选项来自 /industry-news/filters，等选项就绪（触发器解除禁用）后再打开弹层
    const categoryTrigger = within(screen.getByRole('group', { name: '类别' })).getByRole('button');
    await waitFor(() => expect(categoryTrigger).toBeEnabled());
    fireEvent.click(categoryTrigger);
    fireEvent.click(await screen.findByRole('option', { name: /PCB 技术 \/ 工程/ }));
    fireEvent.click(screen.getByRole('switch', { name: '只看未读' }));

    // 输入只改 draft，点击「查询」后才应用
    expect(tenantApi.industryNews.list).toHaveBeenCalledTimes(1);
    fireEvent.click(screen.getByRole('button', { name: '查询' }));

    await waitFor(() => {
      expect(tenantApi.industryNews.list).toHaveBeenLastCalledWith(
        expect.objectContaining({
          'category[]': ['PCB 技术 / 工程'],
          unread_only: true,
          page: 1,
          page_size: 50,
        }),
      );
    });
  });
});
