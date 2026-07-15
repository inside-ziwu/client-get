import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { FilterBar, type FilterField } from '../src/components/filter-bar';
import { MultiSelect } from '../src/components/multi-select';

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

const options = [
  { value: 'long', label: '100%リサイクル高機能伸銅品' },
  { value: 'short', label: '1553接口卡' },
] as const;

type Draft = { tags: readonly string[] };

function FilterBarWithTags({ tags }: Draft) {
  const fields: ReadonlyArray<FilterField<Draft>> = [
    {
      name: 'tags',
      kind: 'multiSelect',
      label: '产品标签',
      placeholder: '不限',
      options,
    },
  ];

  return (
    <FilterBar
      values={{ tags }}
      fields={fields}
      onChange={vi.fn()}
      onSubmit={vi.fn()}
      onReset={vi.fn()}
    />
  );
}

describe('MultiSelect 紧凑筛选布局', () => {
  // Regression: 人工 Gate 发现长文案会把 16px 选项框压窄
  // Found by user acceptance on 2026-07-15
  it('固定选项框宽度，并只让文案区域截断', () => {
    render(
      <MultiSelect
        value={[]}
        options={options}
        onChange={vi.fn()}
        placeholder="选择产品标签"
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '选择产品标签' }));
    const item = screen.getByText(options[0].label).closest('[cmdk-item]');
    const checkbox = item?.querySelector('span.flex.h-4.w-4');

    expect(checkbox).toHaveClass('shrink-0');
    expect(screen.getByText(options[0].label)).toHaveClass('min-w-0', 'flex-1', 'truncate');
  });

  // Regression: 人工 Gate 发现已选标签从 40px 触发器上下溢出
  // Found by user acceptance on 2026-07-15
  it('选择一项时单行显示选项，不渲染可溢出的标签', () => {
    render(<FilterBarWithTags tags={['long']} />);

    const group = screen.getByRole('group', { name: '产品标签' });
    const trigger = within(group).getAllByRole('button')[0];
    expect(trigger).toHaveTextContent(options[0].label);
    expect(trigger).toHaveClass('h-10', 'overflow-hidden');
    expect(within(group).queryByRole('button', { name: '移除 long' })).not.toBeInTheDocument();
  });

  it('选择多项时显示数量摘要并保持单行', () => {
    render(<FilterBarWithTags tags={['long', 'short']} />);

    const group = screen.getByRole('group', { name: '产品标签' });
    const trigger = within(group).getAllByRole('button')[0];
    expect(trigger).toHaveTextContent('已选 2 项');
    expect(trigger).toHaveClass('h-10', 'overflow-hidden');
  });
});
