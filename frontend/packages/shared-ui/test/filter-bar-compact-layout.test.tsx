import { render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { FilterBar, type FilterField } from '../src/components/filter-bar';

type Draft = {
  keyword: string;
  countries: readonly string[];
  minimum: string;
};

const values: Draft = {
  keyword: '',
  countries: [],
  minimum: '',
};

const fields: ReadonlyArray<FilterField<Draft>> = [
  { name: 'keyword', kind: 'text', label: '关键词' },
  {
    name: 'countries',
    kind: 'multiSelect',
    label: '国家',
    options: [{ label: '中国', value: 'CHN' }],
  },
  { name: 'minimum', kind: 'number', label: '最低进口额', advanced: true },
];

describe('FilterBar 紧凑常驻布局', () => {
  it('把全部条件放在同一自动换行容器内，不显示高级条件折叠入口', () => {
    render(
      <FilterBar
        values={values}
        fields={fields}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
        layout="compact"
        collapseAdvanced={false}
      />,
    );

    const fieldContainer = screen.getByTestId('filter-bar-fields');
    expect(fieldContainer).toHaveClass('flex', 'flex-wrap');
    expect(within(fieldContainer).getByLabelText('最低进口额')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /更多条件/ })).not.toBeInTheDocument();
  });

  it('所有字段默认使用 medium，小屏仍占满可用空间', () => {
    render(
      <FilterBar
        values={values}
        fields={fields}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
        layout="compact"
        collapseAdvanced={false}
      />,
    );

    expect(screen.getByLabelText('关键词').closest('[data-filter-kind="text"]')).toHaveClass(
      'w-full',
      'sm:w-ui-control-medium',
    );
    expect(
      screen.getByRole('group', { name: '国家' }).closest('[data-filter-kind="multiSelect"]'),
    ).toHaveClass('w-full', 'sm:w-ui-control-medium');
    expect(screen.getByLabelText('最低进口额').closest('[data-filter-kind="number"]')).toHaveClass(
      'w-full',
      'sm:w-ui-control-medium',
    );
  });
});
