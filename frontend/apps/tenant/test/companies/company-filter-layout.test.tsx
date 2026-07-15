import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { EMPTY_FILTERS } from '@/components/company-filters';
import { CompanyListFilterBar } from '@/app/(dashboard)/companies/company-list-filter-bar';

describe('公司列表紧凑筛选布局', () => {
  it('全部业务条件常驻显示，并按字段类型限制宽度', () => {
    render(
      <CompanyListFilterBar
        values={EMPTY_FILTERS}
        options={{ countries: ['CHN'], sub_industries: [], product_tags: [], grades: [] }}
        optionsState="ready"
        appliedCount={0}
        isSubmitting={false}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
      />,
    );

    expect(screen.queryByRole('button', { name: /更多条件/ })).not.toBeInTheDocument();
    expect(screen.getByLabelText('最低进口额')).toBeVisible();
    expect(screen.getByLabelText('关键词').closest('[data-filter-kind="text"]')).toHaveClass(
      'sm:w-80',
    );
    expect(screen.getByLabelText('最低进口额').closest('[data-filter-kind="number"]')).toHaveClass(
      'sm:w-48',
    );
  });
});
