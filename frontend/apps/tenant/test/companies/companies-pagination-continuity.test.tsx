import type { Company } from '@shared/api';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { type Mock, afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/api', () => ({
  tenantApi: {
    companies: {
      filters: vi.fn(),
      list: vi.fn(),
      detail: vi.fn(),
      contacts: vi.fn(),
      create: vi.fn(),
      blacklist: vi.fn(),
      patch: vi.fn(),
    },
    groups: {
      list: vi.fn().mockResolvedValue({ data: { data: [] } }),
      batchAddMembers: vi.fn(),
    },
  },
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { tenantApi } from '@/lib/api';
import CompaniesPage from '@/app/(dashboard)/companies/page';

const firstPageRow: Company = {
  id: 'company-1',
  tc_id: 'tenant-company-1',
  name: '第一页公司',
  collection_type: 'keyword',
  country_iso3: 'CHN',
};

const secondPageRow: Company = {
  id: 'company-2',
  tc_id: 'tenant-company-2',
  name: '第二页公司',
  collection_type: 'reverse',
  country_iso3: 'USA',
};

function response(rows: Company[], page: number) {
  return { data: { data: rows, pagination: { total: 100, page, page_size: 50 } } };
}

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <CompaniesPage />
    </QueryClientProvider>,
  );
}

describe('CompaniesPage 翻页连续性', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.companies.filters as Mock).mockResolvedValue({
      data: { data: { countries: [], sub_industries: [], product_tags: [], grades: [] } },
    });
  });

  afterEach(() => cleanup());

  it('下一页请求完成前保留旧行和总页数，完成后原子替换数据', async () => {
    let resolveSecondPage: ((value: ReturnType<typeof response>) => void) | undefined;
    const secondPage = new Promise<ReturnType<typeof response>>((resolve) => {
      resolveSecondPage = resolve;
    });

    (tenantApi.companies.list as Mock)
      .mockResolvedValueOnce(response([firstPageRow], 1))
      .mockReturnValueOnce(secondPage);

    renderPage();
    expect(await screen.findByText('第一页公司')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '下一页' }));
    await waitFor(() => expect(tenantApi.companies.list).toHaveBeenCalledTimes(2));

    expect(screen.getByText('第一页公司')).toBeInTheDocument();
    expect(screen.getByText('第 2/2 页')).toBeInTheDocument();

    resolveSecondPage?.(response([secondPageRow], 2));
    expect(await screen.findByText('第二页公司')).toBeInTheDocument();
    expect(screen.queryByText('第一页公司')).not.toBeInTheDocument();
  });
});
