import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { EMPTY_FILTERS } from '@/components/company-filters';
import { CompanyListFilterBar } from '@/app/(dashboard)/companies/company-list-filter-bar';

describe('公司列表紧凑筛选布局', () => {
  it('全部业务条件常驻显示，并按统一宽度契约布局', () => {
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
      'sm:w-ui-control-medium',
    );
    const importRange = screen.getByRole('group', { name: '进口额' });
    expect(importRange).toHaveClass('sm:w-[var(--filter-field-width)]');
    expect(importRange.style.getPropertyValue('--filter-field-width')).toBe('256px');
  });
});
