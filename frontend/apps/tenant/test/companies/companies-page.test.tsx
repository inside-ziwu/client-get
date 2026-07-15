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

const rows: Company[] = [
  {
    id: 'company-1',
    tc_id: 'tenant-company-1',
    name: '远航科技',
    collection_type: 'keyword',
    country_iso3: 'CHN',
    contacts_count: 3,
  },
  {
    id: 'company-2',
    tc_id: 'tenant-company-2',
    name: '星海贸易',
    collection_type: 'reverse',
    country_iso3: 'USA',
    contacts_count: 2,
  },
];

function listResponse() {
  return { data: { data: rows, pagination: { total: 100, page: 1, page_size: 50 } } };
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

describe('CompaniesPage Pattern 打样', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.companies.filters as Mock).mockResolvedValue({
      data: { data: { countries: ['CHN'], sub_industries: [], product_tags: [], grades: ['A'] } },
    });
    (tenantApi.companies.list as Mock).mockResolvedValue(listResponse());
  });

  afterEach(() => cleanup());

  it('查询只提交 draft，并在翻页时原子更新页码且清空 selection', async () => {
    renderPage();

    expect(await screen.findByRole('table', { name: '公司列表' })).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText('关键词'), { target: { value: 'PCB' } });
    expect(tenantApi.companies.list).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole('button', { name: '查询' }));
    await waitFor(() => {
      expect(tenantApi.companies.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ keyword: 'PCB', page: 1, page_size: 50 }),
      );
    });

    fireEvent.click(screen.getByRole('checkbox', { name: '选择公司 tenant-company-1' }));
    expect(screen.getByText('已选 1 家公司')).toBeInTheDocument();

    fireEvent.click(screen.getByRole('button', { name: '下一页' }));
    await waitFor(() => {
      expect(tenantApi.companies.list).toHaveBeenLastCalledWith(
        expect.objectContaining({ keyword: 'PCB', page: 2, page_size: 50 }),
      );
    });
    expect(screen.queryByText('已选 1 家公司')).not.toBeInTheDocument();
  });

  it('重置同时清空 draft、applied、页码和 selection', async () => {
    renderPage();
    await screen.findByText('远航科技');

    fireEvent.change(screen.getByLabelText('关键词'), { target: { value: 'PCB' } });
    fireEvent.click(screen.getByRole('button', { name: '查询' }));
    await waitFor(() => expect(tenantApi.companies.list).toHaveBeenCalledTimes(2));
    fireEvent.click(await screen.findByRole('checkbox', { name: '选择公司 tenant-company-1' }));

    fireEvent.click(screen.getByRole('button', { name: '重置' }));
    await waitFor(() => {
      expect(screen.getByLabelText('关键词')).toHaveValue('');
      expect(tenantApi.companies.list).toHaveBeenLastCalledWith(
        expect.not.objectContaining({ keyword: expect.anything() }),
      );
    });
    expect(screen.queryByText('已选 1 家公司')).not.toBeInTheDocument();
  });

  it('初始加载失败时展示可重试的 TableState', async () => {
    (tenantApi.companies.list as Mock)
      .mockRejectedValueOnce(new Error('network'))
      .mockResolvedValueOnce(listResponse());
    renderPage();

    expect(await screen.findByRole('alert')).toHaveTextContent('公司加载失败');
    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    expect(await screen.findByText('远航科技')).toBeInTheDocument();
  });
});
