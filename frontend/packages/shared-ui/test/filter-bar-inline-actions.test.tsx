import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { FilterBar, type FilterField } from '../src/components/filter-bar';

type Draft = {
  keyword: string;
  country: string;
};

const values: Draft = {
  keyword: '',
  country: '',
};

const fields: ReadonlyArray<FilterField<Draft>> = [
  {
    name: 'keyword',
    kind: 'text',
    label: '关键词',
    compactWidth: 'medium',
  },
  {
    name: 'country',
    kind: 'select',
    label: '国家',
    compactWidth: 'narrow',
    options: [{ label: '中国', value: 'CHN' }],
  },
];

describe('FilterBar 紧凑行内操作区', () => {
  it('允许字段覆盖默认紧凑宽度', () => {
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
      'sm:!w-56',
    );
    expect(screen.getByLabelText('国家').closest('[data-filter-kind="select"]')).toHaveClass(
      'sm:!w-40',
    );
  });

  it('把查询和重置接在最后一个筛选字段之后', () => {
    render(
      <FilterBar
        values={values}
        fields={fields}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
        layout="compact"
        collapseAdvanced={false}
        actionsPlacement="inline"
      />,
    );

    const layout = screen.getByTestId('filter-bar-inline-layout');
    const fieldContainer = screen.getByTestId('filter-bar-fields');
    const actions = screen.getByTestId('filter-bar-actions');

    expect(layout.children[0]).toBe(fieldContainer);
    expect(layout.children[1]).toBe(actions);
    expect(actions).toHaveClass('self-end');
    expect(actions).toContainElement(screen.getByRole('button', { name: '重置' }));
    expect(actions).toContainElement(screen.getByRole('button', { name: '查询' }));
  });
});
