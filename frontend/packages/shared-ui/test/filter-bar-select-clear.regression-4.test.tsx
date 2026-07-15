import { fireEvent, render, screen } from '@testing-library/react';
import { useState } from 'react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { FilterBar, type FilterField } from '../src/components/filter-bar';

type Draft = { collectionType: string };

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

function ControlledFilterBar({ onSubmit }: { onSubmit: (draft: Draft) => void }) {
  const [values, setValues] = useState<Draft>({ collectionType: '' });
  const fields: ReadonlyArray<FilterField<Draft>> = [
    {
      name: 'collectionType',
      kind: 'select',
      label: '采集类型',
      placeholder: '不限',
      options: [{ value: 'manual', label: '手工录入' }],
    },
  ];

  return (
    <FilterBar
      values={values}
      fields={fields}
      onChange={setValues}
      onSubmit={onSubmit}
      onReset={() => setValues({ collectionType: '' })}
    />
  );
}

describe('FilterBar 单选条件清空', () => {
  // Regression: 人工 Gate 发现单选筛选选中后只能整体重置
  // Found by user acceptance on 2026-07-15
  it('允许把单个 select 条件重新选择为不限', () => {
    const onSubmit = vi.fn();
    render(<ControlledFilterBar onSubmit={onSubmit} />);

    const trigger = screen.getByLabelText('采集类型');
    fireEvent.keyDown(trigger, { key: 'ArrowDown' });
    fireEvent.click(screen.getByRole('option', { name: '手工录入' }));
    expect(trigger).toHaveTextContent('手工录入');

    fireEvent.keyDown(trigger, { key: 'ArrowDown' });
    fireEvent.click(screen.getByRole('option', { name: '不限' }));
    expect(trigger).toHaveTextContent('不限');

    fireEvent.submit(screen.getByRole('button', { name: '查询' }).closest('form')!);
    expect(onSubmit).toHaveBeenCalledWith({ collectionType: '' });
  });
});
