import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { FilterBar, type FilterField } from '../src/components/filter-bar';

type Draft = {
  tags: readonly string[];
};

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

describe('FilterBar 可查看选项状态', () => {
  it('把加载状态和独立搜索文案传给多选弹层，但不禁用触发器', () => {
    const fields: ReadonlyArray<FilterField<Draft>> = [
      {
        name: 'tags',
        kind: 'multiSelect',
        label: '产品标签',
        placeholder: '不限',
        searchPlaceholder: '搜索产品标签',
        options: [],
        optionState: 'loading',
      },
    ];

    render(
      <FilterBar
        values={{ tags: [] }}
        fields={fields}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
        optionStateMode="inspectable"
      />,
    );

    const trigger = within(screen.getByRole('group', { name: '产品标签' })).getByRole('button');
    expect(trigger).toBeEnabled();
    fireEvent.click(trigger);
    expect(screen.getByPlaceholderText('搜索产品标签')).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('正在加载选项…');
  });
});
