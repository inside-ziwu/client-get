import type { Company } from '@shared/api';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
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
      list: vi.fn(),
      batchAddMembers: vi.fn(),
    },
  },
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import { tenantApi } from '@/lib/api';
import CompaniesPage from '@/app/(dashboard)/companies/page';

const company: Company = {
  id: 'company-1',
  tc_id: 'tenant-company-1',
  name: '示例公司',
  collection_type: 'manual',
  country_iso3: 'CHN',
};

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

describe('CompaniesPage 弹层说明', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (tenantApi.companies.filters as Mock).mockResolvedValue({
      data: { data: { countries: [], sub_industries: [], product_tags: [], grades: [] } },
    });
    (tenantApi.companies.list as Mock).mockResolvedValue({
      data: { data: [company], pagination: { total: 1, page: 1, page_size: 50 } },
    });
    (tenantApi.companies.detail as Mock).mockResolvedValue({ data: { data: company } });
    (tenantApi.companies.contacts as Mock).mockResolvedValue({ data: { data: [] } });
    (tenantApi.groups.list as Mock).mockResolvedValue({ data: { data: [] } });
  });

  afterEach(() => cleanup());

  it('公司详情抽屉向辅助技术说明内容范围', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '示例公司' }));

    expect(await screen.findByRole('dialog')).toHaveAccessibleDescription(
      '查看公司资料、AI 评估与联系人信息。',
    );
  });

  it('加入群组弹窗说明确认动作的影响', async () => {
    renderPage();
    fireEvent.click(await screen.findByRole('button', { name: '群组' }));

    expect(await screen.findByRole('dialog')).toHaveAccessibleDescription(
      '选择目标群组；确认后将更新所选公司的群组归属。',
    );
  });

  it('新增公司抽屉说明表单用途', async () => {
    renderPage();
    fireEvent.click(screen.getByRole('button', { name: '新增公司' }));

    expect(await screen.findByRole('dialog')).toHaveAccessibleDescription(
      '录入公司基本资料，并可同时添加联系人。',
    );
  });
});
