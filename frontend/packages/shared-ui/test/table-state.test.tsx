import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { TableState } from '../src/components/table-state';

function renderState(props: React.ComponentProps<typeof TableState>) {
  return render(
    <table>
      <tbody>
        <TableState {...props} />
      </tbody>
    </table>,
  );
}

describe('TableState', () => {
  it('在合法表格行中展示 loading 标准文案和状态语义', () => {
    renderState({ state: { kind: 'loading' }, entityName: '公司', colSpan: 4 });

    const status = screen.getByRole('status');
    expect(status).toHaveTextContent('正在加载公司…');
    expect(status.parentElement).toHaveClass('sticky', 'left-0', 'w-[100cqw]');
    expect(status.closest('td')).toHaveAttribute('colspan', '4');
    expect(status.closest('tr')).toBeInTheDocument();
  });

  it('区分首次空态和筛选无结果', () => {
    const { rerender } = renderState({
      state: { kind: 'empty' },
      entityName: '联系人',
      colSpan: 2,
    });
    expect(screen.getByText('暂无联系人')).toBeInTheDocument();

    rerender(
      <table>
        <tbody>
          <TableState
            state={{ kind: 'empty', filtered: true }}
            entityName="联系人"
            colSpan={2}
          />
        </tbody>
      </table>,
    );
    expect(screen.getByText('没有符合当前条件的联系人')).toBeInTheDocument();
  });

  it('筛选无结果时可触发一次重置筛选', () => {
    const onResetFilters = vi.fn();
    renderState({
      state: { kind: 'empty', filtered: true, onResetFilters },
      entityName: '公司',
      colSpan: 3,
    });

    fireEvent.click(screen.getByRole('button', { name: '重置筛选' }));
    expect(onResetFilters).toHaveBeenCalledTimes(1);
  });

  it('错误态使用 alert，展示安全描述并支持重试', () => {
    const onRetry = vi.fn();
    renderState({
      state: { kind: 'error', description: '请稍后再试', onRetry },
      entityName: '邮件模板',
      colSpan: 5,
    });

    const alert = screen.getByRole('alert');
    expect(alert).toHaveTextContent('邮件模板加载失败');
    expect(alert).toHaveTextContent('请稍后再试');
    fireEvent.click(screen.getByRole('button', { name: '重试' }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });
});
