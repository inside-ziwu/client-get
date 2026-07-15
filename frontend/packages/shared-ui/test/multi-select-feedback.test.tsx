import { fireEvent, render, screen, within } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
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

describe('MultiSelect 远程选项反馈', () => {
  it('加载中允许打开弹层，并在数据返回后原位显示选项', () => {
    const { rerender } = render(
      <MultiSelect
        value={[]}
        options={[]}
        onChange={vi.fn()}
        placeholder="不限"
        searchPlaceholder="搜索产品标签"
        optionState="loading"
        allowCreate={false}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: /正在加载选项/ }));
    expect(screen.getByPlaceholderText('搜索产品标签')).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('正在加载选项…');

    rerender(
      <MultiSelect
        value={[]}
        options={[{ label: 'PCB', value: 'pcb' }]}
        onChange={vi.fn()}
        placeholder="不限"
        searchPlaceholder="搜索产品标签"
        optionState="ready"
        allowCreate={false}
      />,
    );

    expect(screen.getByPlaceholderText('搜索产品标签')).toBeEnabled();
    expect(screen.getByText('PCB')).toBeInTheDocument();
  });

  it('空数据时允许打开弹层并明确显示暂无可选项', () => {
    render(
      <MultiSelect
        value={[]}
        options={[]}
        onChange={vi.fn()}
        placeholder="不限"
        searchPlaceholder="搜索国家"
        optionState="empty"
        allowCreate={false}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '暂无可选项' }));

    expect(screen.getByPlaceholderText('搜索国家')).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('暂无可选项');
  });

  it('触发器占位与弹层搜索提示分别表达筛选状态和搜索对象', () => {
    render(
      <MultiSelect
        value={[]}
        options={[{ label: '中国', value: 'CHN' }]}
        onChange={vi.fn()}
        placeholder="不限"
        searchPlaceholder="搜索国家"
        optionState="ready"
        allowCreate={false}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '不限' }));

    const searchInput = screen.getByPlaceholderText('搜索国家');
    fireEvent.change(searchInput, { target: { value: '不存在' } });
    expect(within(screen.getByRole('dialog')).getByText('没有匹配项')).toBeInTheDocument();
  });
});
