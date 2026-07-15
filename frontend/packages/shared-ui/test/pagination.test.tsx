import { fireEvent, render, screen } from '@testing-library/react';
import { beforeAll, describe, expect, it, vi } from 'vitest';
import { Pagination } from '../src/components/pagination';

beforeAll(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

describe('Pagination', () => {
  it('total=0 时显示第 1/1 页并禁用前后翻页', () => {
    render(
      <Pagination
        mode="total"
        total={0}
        value={{ page: 1, pageSize: 20 }}
        onChange={vi.fn()}
      />,
    );

    expect(screen.getByText('共 0 条')).toBeInTheDocument();
    expect(screen.getByText('第 1/1 页')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: '每页条数' })).toHaveClass(
      'h-10',
      'rounded-ui-md',
    );
    expect(screen.getByLabelText('跳转页码')).toHaveClass(
      'h-10',
      'rounded-ui-md',
      'focus-visible:ring-ui-foreground',
    );
    expect(screen.getByRole('button', { name: '上一页' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '上一页' })).toHaveClass('h-10', 'w-10');
    expect(screen.getByRole('button', { name: '下一页' })).toBeDisabled();
  });

  it('前后翻页分别发出完整分页值', () => {
    const onChange = vi.fn();
    render(
      <Pagination
        mode="total"
        total={200}
        value={{ page: 3, pageSize: 20 }}
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole('button', { name: '上一页' }));
    fireEvent.click(screen.getByRole('button', { name: '下一页' }));
    expect(onChange).toHaveBeenNthCalledWith(1, { page: 2, pageSize: 20 });
    expect(onChange).toHaveBeenNthCalledWith(2, { page: 4, pageSize: 20 });
  });

  it('改变 pageSize 时一次性回到第一页，并保留当前非默认选项', async () => {
    const onChange = vi.fn();
    render(
      <Pagination
        mode="total"
        total={200}
        value={{ page: 3, pageSize: 30 }}
        onChange={onChange}
      />,
    );

    fireEvent.click(screen.getByRole('combobox', { name: '每页条数' }));
    expect(await screen.findByRole('option', { name: '30 条/页' })).toBeInTheDocument();
    fireEvent.click(screen.getByRole('option', { name: '50 条/页' }));

    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange).toHaveBeenCalledWith({ page: 1, pageSize: 50 });
  });

  it('unknownTotal 隐藏总数、总页数与跳页，并按 hasNextPage 控制下一页', () => {
    const onChange = vi.fn();
    render(
      <Pagination
        mode="unknownTotal"
        hasNextPage={false}
        value={{ page: 2, pageSize: 20 }}
        onChange={onChange}
      />,
    );

    expect(screen.getByText('第 2 页')).toBeInTheDocument();
    expect(screen.queryByText(/共 \d+ 条/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText('跳转页码')).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: '下一页' })).toBeDisabled();

    fireEvent.click(screen.getByRole('button', { name: '上一页' }));
    expect(onChange).toHaveBeenCalledWith({ page: 1, pageSize: 20 });
  });

  it('unknownTotal 第一页禁用上一页，并在还有下一页时允许前进', () => {
    const onChange = vi.fn();
    render(
      <Pagination
        mode="unknownTotal"
        hasNextPage
        value={{ page: 1, pageSize: 50 }}
        onChange={onChange}
      />,
    );

    expect(screen.getByRole('button', { name: '上一页' })).toBeDisabled();
    const nextButton = screen.getByRole('button', { name: '下一页' });
    expect(nextButton).toBeEnabled();
    fireEvent.click(nextButton);
    expect(onChange).toHaveBeenCalledWith({ page: 2, pageSize: 50 });
  });

  it('total 模式可以显式隐藏跳页控件', () => {
    render(
      <Pagination
        mode="total"
        total={100}
        showPageJump={false}
        value={{ page: 2, pageSize: 20 }}
        onChange={vi.fn()}
      />,
    );

    expect(screen.queryByLabelText('跳转页码')).not.toBeInTheDocument();
    expect(screen.getByText('第 2/5 页')).toBeInTheDocument();
  });

  it('跳页会 clamp 到合法范围，且 Enter 后的 blur 不重复提交', () => {
    const onChange = vi.fn();
    render(
      <Pagination
        mode="total"
        total={95}
        value={{ page: 2, pageSize: 20 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByLabelText('跳转页码');
    fireEvent.change(input, { target: { value: '99' } });
    fireEvent.keyDown(input, { key: 'Enter' });
    fireEvent.blur(input);

    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange).toHaveBeenCalledWith({ page: 5, pageSize: 20 });
    expect(input).toHaveValue('5');
  });

  it('跳页为空或 NaN 时恢复当前页且不触发回调', () => {
    const onChange = vi.fn();
    render(
      <Pagination
        mode="total"
        total={95}
        value={{ page: 2, pageSize: 20 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByLabelText('跳转页码');
    fireEvent.change(input, { target: { value: '' } });
    fireEvent.blur(input);
    expect(input).toHaveValue('2');

    fireEvent.change(input, { target: { value: '不是数字' } });
    fireEvent.blur(input);
    expect(input).toHaveValue('2');
    expect(onChange).not.toHaveBeenCalled();
  });

  it('跳页向下 clamp，跳到当前页不回调，并同步外部页码更新', () => {
    const onChange = vi.fn();
    const { rerender } = render(
      <Pagination
        mode="total"
        total={95}
        value={{ page: 2, pageSize: 20 }}
        onChange={onChange}
      />,
    );

    const input = screen.getByLabelText('跳转页码');
    fireEvent.change(input, { target: { value: '-8' } });
    fireEvent.blur(input);
    expect(onChange).toHaveBeenCalledWith({ page: 1, pageSize: 20 });

    onChange.mockClear();
    fireEvent.change(input, { target: { value: '2' } });
    fireEvent.blur(input);
    expect(onChange).not.toHaveBeenCalled();

    rerender(
      <Pagination
        mode="total"
        total={95}
        value={{ page: 4, pageSize: 20 }}
        onChange={onChange}
      />,
    );
    expect(screen.getByLabelText('跳转页码')).toHaveValue('4');
  });

  it('isDisabled 会禁用所有分页控件', () => {
    render(
      <Pagination
        mode="total"
        total={200}
        value={{ page: 2, pageSize: 20 }}
        onChange={vi.fn()}
        isDisabled
      />,
    );

    expect(screen.getByRole('combobox', { name: '每页条数' })).toBeDisabled();
    expect(screen.getByLabelText('跳转页码')).toBeDisabled();
    expect(screen.getByRole('button', { name: '上一页' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '下一页' })).toBeDisabled();
  });
});
