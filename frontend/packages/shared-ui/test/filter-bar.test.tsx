import { fireEvent, render, screen, within } from '@testing-library/react';
import { useState } from 'react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import {
  FilterBar,
  type FilterField,
} from '../src/components/filter-bar';

type Draft = {
  keyword: string;
  minimum: string;
  date: string;
  status: string;
  tags: readonly string[];
  custom: string;
};

const initialValues: Draft = {
  keyword: '',
  minimum: '',
  date: '',
  status: '',
  tags: [],
  custom: '',
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

function ControlledFilterBar({
  fields,
  onSubmit = vi.fn(),
  onReset = vi.fn(),
  isSubmitting = false,
  appliedCount,
}: {
  fields: ReadonlyArray<FilterField<Draft>>;
  onSubmit?: (draft: Draft) => void;
  onReset?: () => void;
  isSubmitting?: boolean;
  appliedCount?: number;
}) {
  const [values, setValues] = useState(initialValues);

  return (
    <FilterBar
      values={values}
      fields={fields}
      onChange={setValues}
      onSubmit={onSubmit}
      onReset={onReset}
      isSubmitting={isSubmitting}
      appliedCount={appliedCount}
    />
  );
}

describe('FilterBar', () => {
  it('只更新受控 draft，并在表单提交时把当前 draft 交给父页面', () => {
    const onSubmit = vi.fn();
    const fields: ReadonlyArray<FilterField<Draft>> = [
      { name: 'keyword', kind: 'text', label: '关键词' },
      { name: 'minimum', kind: 'number', label: '最低分' },
      { name: 'date', kind: 'date', label: '创建日期' },
      {
        name: 'custom',
        kind: 'custom',
        label: '自定义条件',
        render: ({ setValue }) => (
          <button type="button" onClick={() => setValue('custom', '已设置')}>
            设置自定义条件
          </button>
        ),
      },
    ];

    render(<ControlledFilterBar fields={fields} onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText('关键词'), { target: { value: '电路板' } });
    fireEvent.change(screen.getByLabelText('最低分'), { target: { value: '80' } });
    fireEvent.change(screen.getByLabelText('创建日期'), { target: { value: '2026-07-14' } });
    fireEvent.click(screen.getByRole('button', { name: '设置自定义条件' }));
    fireEvent.submit(screen.getByRole('button', { name: '查询' }).closest('form')!);

    expect(onSubmit).toHaveBeenCalledOnce();
    expect(onSubmit).toHaveBeenCalledWith({
      ...initialValues,
      keyword: '电路板',
      minimum: '80',
      date: '2026-07-14',
      custom: '已设置',
    });
  });

  it('重置只通知父页面一次，不额外提交或拼装空筛选值', () => {
    const onChange = vi.fn();
    const onSubmit = vi.fn();
    const onReset = vi.fn();

    render(
      <FilterBar
        values={{ ...initialValues, keyword: '保留到父层处理' }}
        fields={[{ name: 'keyword', kind: 'text', label: '关键词' }]}
        onChange={onChange}
        onSubmit={onSubmit}
        onReset={onReset}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '重置' }));

    expect(onReset).toHaveBeenCalledOnce();
    expect(onChange).not.toHaveBeenCalled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('select 与 multiSelect 更新受控值，且 multiSelect 不允许创建自由选项', () => {
    const onSubmit = vi.fn();
    const fields: ReadonlyArray<FilterField<Draft>> = [
      {
        name: 'status',
        kind: 'select',
        label: '状态',
        placeholder: '选择状态',
        options: [
          { label: '启用', value: 'active' },
          { label: '停用', value: 'inactive' },
        ],
      },
      {
        name: 'tags',
        kind: 'multiSelect',
        label: '标签',
        placeholder: '选择标签',
        options: [
          { label: '采购商', value: 'buyer' },
          { label: '制造商', value: 'manufacturer' },
        ],
      },
    ];

    render(<ControlledFilterBar fields={fields} onSubmit={onSubmit} />);

    const statusTrigger = screen.getByLabelText('状态');
    fireEvent.keyDown(statusTrigger, { key: 'ArrowDown' });
    fireEvent.click(screen.getByRole('option', { name: '启用' }));

    fireEvent.click(screen.getByRole('button', { name: '选择标签' }));
    const command = screen.getByPlaceholderText('选择标签');
    fireEvent.change(command, { target: { value: '采购商' } });
    fireEvent.click(screen.getByText('采购商'));

    fireEvent.change(screen.getByPlaceholderText('选择标签'), { target: { value: '新标签' } });
    expect(screen.queryByText(/新增.*新标签/)).not.toBeInTheDocument();

    fireEvent.submit(screen.getByRole('button', { name: '查询' }).closest('form')!);
    expect(onSubmit).toHaveBeenCalledWith({
      ...initialValues,
      status: 'active',
      tags: ['buyer'],
    });
  });

  it('advanced 字段在窄屏默认折叠，并在入口展示已应用条件数量', () => {
    const fields: ReadonlyArray<FilterField<Draft>> = [
      { name: 'keyword', kind: 'text', label: '关键词' },
      { name: 'date', kind: 'date', label: '创建日期', advanced: true },
    ];

    render(<ControlledFilterBar fields={fields} appliedCount={2} />);

    const toggle = screen.getByRole('button', { name: '更多条件（2）' });
    const advancedFields = screen.getByTestId('filter-bar-advanced-fields');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    expect(advancedFields).toHaveClass('hidden', 'sm:grid');

    fireEvent.click(toggle);

    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(advancedFields).not.toHaveClass('hidden');
    expect(screen.getByLabelText('创建日期')).toBeInTheDocument();
  });

  it('分别表达 select 与 multiSelect 的选项加载和空状态', () => {
    const fields: ReadonlyArray<FilterField<Draft>> = [
      {
        name: 'status',
        kind: 'select',
        label: '状态',
        options: [],
        optionState: 'loading',
      },
      {
        name: 'tags',
        kind: 'multiSelect',
        label: '标签',
        options: [],
        optionState: 'empty',
      },
    ];

    render(<ControlledFilterBar fields={fields} />);

    expect(screen.getByLabelText('状态')).toBeDisabled();
    expect(screen.getByText('正在加载选项…')).toBeInTheDocument();
    const tagsGroup = screen.getByRole('group', { name: '标签' });
    expect(within(tagsGroup).getByRole('button')).toBeDisabled();
    expect(within(tagsGroup).getByText('暂无可选项')).toBeInTheDocument();
  });

  it('提交中禁用筛选控件和操作，并把 disabled 传给 custom 字段', () => {
    const fields: ReadonlyArray<FilterField<Draft>> = [
      { name: 'keyword', kind: 'text', label: '关键词' },
      {
        name: 'custom',
        kind: 'custom',
        label: '自定义条件',
        render: ({ disabled }) => <span>{disabled ? '自定义条件已禁用' : '自定义条件可用'}</span>,
      },
    ];

    render(<ControlledFilterBar fields={fields} isSubmitting />);

    expect(screen.getByLabelText('关键词')).toBeDisabled();
    expect(screen.getByRole('button', { name: '查询中…' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '重置' })).toBeDisabled();
    expect(screen.getByText('自定义条件已禁用')).toBeInTheDocument();
  });
});
