import type { Company } from '@shared/api';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

vi.mock('@/lib/api', () => ({
  tenantApi: {
    companies: {
      contacts: vi.fn().mockResolvedValue({
        data: {
          data: [
            {
              id: 'contact-1',
              name: '张三',
              position: '采购总监',
              department: '采购部',
              email: 'zhang@example.com',
              email_status: '有效',
              phone: '+86 13800000000',
            },
          ],
        },
      }),
      patch: vi.fn(),
    },
  },
}));

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}));

import CompanyDetail from '@/components/company-detail';

const company: Company = {
  id: 'company-1',
  tc_id: 'tenant-company-1',
  name: '示例公司',
  collection_type: 'manual',
};

describe('CompanyDetail 联系人契约', () => {
  it('使用 API 的 position 字段展示联系人职位', async () => {
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });

    render(
      <QueryClientProvider client={queryClient}>
        <CompanyDetail company={company} onSaved={vi.fn()} />
      </QueryClientProvider>,
    );

    expect(await screen.findByText('采购总监')).toBeInTheDocument();
  });
});
