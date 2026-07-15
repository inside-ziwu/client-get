import { cleanup, render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CompanyListFilterBar } from '@/app/(dashboard)/companies/company-list-filter-bar';
import { EMPTY_FILTERS } from '@/components/company-filters';

afterEach(() => cleanup());

describe('公司列表筛选密度', () => {
  it('收紧短选项字段，并把操作区接在全部条件之后', () => {
    render(
      <CompanyListFilterBar
        values={EMPTY_FILTERS}
        optionsState="ready"
        appliedCount={0}
        isSubmitting={false}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
      />,
    );

    expect(screen.getByLabelText('关键词').closest('[data-filter-kind="text"]')).toHaveClass(
      'sm:w-ui-control-medium',
    );
    for (const label of ['国家', '大模型评级', '模板评级']) {
      expect(screen.getByRole('group', { name: label })).toHaveClass('sm:w-ui-control-small');
    }
    for (const label of ['采集类型', '群组状态']) {
      expect(screen.getByLabelText(label).closest('[data-filter-kind="select"]')).toHaveClass(
        'sm:w-ui-control-small',
      );
    }
    expect(screen.getByRole('group', { name: '细分行业' })).toHaveClass(
      'sm:w-ui-control-small',
    );
    expect(screen.getByRole('group', { name: '产品标签' })).toHaveClass(
      'sm:w-ui-control-small',
    );
    for (const label of ['进口额', '进口次数', '联系人', '成立年份']) {
      const range = screen.getByRole('group', { name: label });
      expect(range).toHaveClass('sm:w-[var(--filter-field-width)]');
      expect(range.style.getPropertyValue('--filter-field-width')).toBe('256px');
    }

    const layout = screen.getByTestId('filter-bar-inline-layout');
    expect(layout.children[1]).toBe(screen.getByTestId('filter-bar-actions'));
    expect(screen.getByTestId('filter-bar-fields').children).toHaveLength(12);
  });
});
