import { fireEvent, render, screen, within } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DataTable, type DataTableColumn } from '../src/components/data-table';

interface CompanyRow {
  id: string;
  name: string | null;
  score: number | null;
  createdAt: string;
  status: string;
  enabled: boolean;
  locked?: boolean;
}

const rows: readonly CompanyRow[] = [
  {
    id: 'company-1',
    name: '远航科技',
    score: 98,
    createdAt: '2026-07-14',
    status: 'active',
    enabled: true,
  },
  {
    id: 'company-2',
    name: null,
    score: null,
    createdAt: '2026-07-13',
    status: 'unexpected',
    enabled: false,
    locked: true,
  },
];

const columns: readonly DataTableColumn<CompanyRow>[] = [
  { id: 'name', header: '公司', width: 'lg', type: 'text', value: 'name' },
  {
    id: 'score',
    header: '评分',
    width: 'sm',
    type: 'number',
    value: 'score',
    format: (value) => (value == null ? '无评分' : `${value} 分`),
  },
  {
    id: 'createdAt',
    header: '创建时间',
    width: 'md',
    type: 'date',
    value: 'createdAt',
    format: (value) => `日期：${String(value)}`,
  },
  {
    id: 'status',
    header: '状态',
    width: 'sm',
    type: 'status',
    value: 'status',
    statusMap: { active: { label: '启用', tone: 'success' } },
  },
  {
    id: 'enabled',
    header: '可用',
    width: 'sm',
    type: 'boolean',
    value: 'enabled',
    booleanMode: 'readOnly',
    getBooleanLabel: (row) => (row.enabled ? '已启用' : '已停用'),
  },
  {
    id: 'actions',
    header: '操作',
    width: 'sm',
    type: 'actions',
    render: (row) => <button type="button">编辑 {row.id}</button>,
  },
];

describe('DataTable', () => {
  it('按列契约渲染默认值、格式、状态回退和固定列', () => {
    render(
      <DataTable
        columns={columns}
        data={rows}
        entityName="公司"
        getRowId={(row) => row.id}
      />,
    );

    const table = screen.getByRole('table');
    expect(table).toHaveAttribute('aria-busy', 'false');
    expect(table).toHaveAttribute('aria-label', '公司列表');
    expect(table).toHaveClass('table-fixed');
    expect(table.querySelectorAll('col')).toHaveLength(columns.length);
    expect(screen.getByText('远航科技')).toBeInTheDocument();
    expect(screen.getByText('-')).toBeInTheDocument();
    expect(screen.getByText('98 分')).toBeInTheDocument();
    expect(screen.getByText('无评分')).toBeInTheDocument();
    expect(screen.getByText('日期：2026-07-14')).toBeInTheDocument();
    expect(screen.getByText('启用')).toBeInTheDocument();
    expect(screen.getByText('unexpected')).toBeInTheDocument();
    expect(screen.getByText('已启用')).toBeInTheDocument();
    expect(screen.getByText('已停用')).toBeInTheDocument();

    const actionHeader = screen.getByRole('columnheader', { name: '操作' });
    expect(actionHeader).toHaveClass('sticky', 'right-0');
    expect(screen.getByRole('columnheader', { name: '公司' })).toHaveClass('sticky', 'top-0');
    expect(table.closest('[data-data-table-scroll]')).toHaveClass('overflow-x-auto');
  });

  it('关闭 sticky header 时仍能独立固定 actions 列', () => {
    render(
      <DataTable
        columns={columns}
        data={rows.slice(0, 1)}
        entityName="公司"
        getRowId={(row) => row.id}
        stickyHeader={false}
      />,
    );

    const nameHeader = screen.getByRole('columnheader', { name: '公司' });
    const actionHeader = screen.getByRole('columnheader', { name: '操作' });
    expect(nameHeader).not.toHaveClass('sticky');
    expect(actionHeader).toHaveClass('sticky', 'right-0');
  });

  it('文本只有实际溢出时才进入键盘序列', () => {
    const clientWidth = vi.spyOn(HTMLElement.prototype, 'clientWidth', 'get');
    const scrollWidth = vi.spyOn(HTMLElement.prototype, 'scrollWidth', 'get');
    clientWidth.mockReturnValue(100);
    scrollWidth.mockReturnValue(100);

    const { rerender } = render(
      <DataTable
        columns={columns.slice(0, 1)}
        data={rows.slice(0, 1)}
        entityName="公司"
        getRowId={(row) => row.id}
      />,
    );
    expect(screen.getByText('远航科技')).not.toHaveAttribute('tabindex');

    scrollWidth.mockReturnValue(200);
    rerender(
      <DataTable
        columns={columns.slice(0, 1)}
        data={rows.slice(0, 1)}
        entityName="公司"
        getRowId={(row) => row.id}
      />,
    );
    fireEvent(window, new Event('resize'));
    expect(screen.getByText('远航科技')).toHaveAttribute('tabindex', '0');

    clientWidth.mockRestore();
    scrollWidth.mockRestore();
  });

  it('render 优先于 format 和默认格式', () => {
    const priorityColumns: readonly DataTableColumn<CompanyRow>[] = [
      {
        id: 'name',
        header: '公司',
        width: 'md',
        type: 'text',
        value: 'name',
        format: () => 'format 内容',
        render: () => 'render 内容',
      },
    ];

    render(
      <DataTable
        columns={priorityColumns}
        data={rows.slice(0, 1)}
        entityName="公司"
        getRowId={(row) => row.id}
      />,
    );

    expect(screen.getByText('render 内容')).toBeInTheDocument();
    expect(screen.queryByText('format 内容')).not.toBeInTheDocument();
    expect(screen.queryByText('远航科技')).not.toBeInTheDocument();
  });

  it('交互布尔列提供可访问名称并透传切换值', () => {
    const onBooleanChange = vi.fn();
    const interactiveColumns: readonly DataTableColumn<CompanyRow>[] = [
      {
        id: 'enabled',
        header: '可用',
        width: 'sm',
        type: 'boolean',
        value: 'enabled',
        booleanMode: 'interactive',
        getBooleanLabel: (row) => `${row.name ?? '公司'}可用状态`,
        isBooleanDisabled: (row) => Boolean(row.locked),
        onBooleanChange,
      },
    ];

    render(
      <DataTable
        columns={interactiveColumns}
        data={rows}
        entityName="公司"
        getRowId={(row) => row.id}
      />,
    );

    fireEvent.click(screen.getByRole('switch', { name: '远航科技可用状态' }));
    expect(onBooleanChange).toHaveBeenCalledOnce();
    expect(onBooleanChange).toHaveBeenCalledWith(rows[0], false);
    expect(screen.getByRole('switch', { name: '公司可用状态' })).toBeDisabled();
  });

  it('当前页全选排除禁用行，并正确表达部分选中', () => {
    const onToggleRow = vi.fn();
    const onTogglePage = vi.fn();
    const firstRow = rows[0]!;
    const selectableSecondRow: CompanyRow = { ...rows[1]!, locked: false };
    const disabledThirdRow: CompanyRow = { ...rows[1]!, id: 'company-3', locked: true };
    const selectionRows: readonly CompanyRow[] = [
      firstRow,
      selectableSecondRow,
      disabledThirdRow,
    ];

    render(
      <DataTable
        columns={columns.slice(0, 1)}
        data={selectionRows}
        entityName="公司"
        getRowId={(row) => row.id}
        selection={{
          selectedKeys: new Set(['company-1']),
          isRowDisabled: (row) => Boolean(row.locked),
          onTogglePage,
          onToggleRow,
        }}
      />,
    );

    const selectPage = screen.getByRole('checkbox', { name: '选择当前页公司' });
    expect(selectPage).toHaveAttribute('data-state', 'indeterminate');
    fireEvent.click(selectPage);
    expect(onTogglePage).toHaveBeenCalledWith([firstRow, selectableSecondRow]);

    fireEvent.click(screen.getByRole('checkbox', { name: '选择公司 company-1' }));
    expect(onToggleRow).toHaveBeenCalledWith(firstRow);
    expect(screen.getByRole('checkbox', { name: '选择公司 company-2' })).toBeEnabled();
    expect(screen.getByRole('checkbox', { name: '选择公司 company-3' })).toBeDisabled();
  });

  it('保留旧行并用弱提示表达刷新中', () => {
    render(
      <DataTable
        columns={columns.slice(0, 1)}
        data={rows.slice(0, 1)}
        entityName="公司"
        getRowId={(row) => row.id}
        isRefreshing
      />,
    );

    expect(screen.getByRole('table')).toHaveAttribute('aria-busy', 'true');
    expect(screen.getByText('远航科技')).toBeInTheDocument();
    expect(screen.getByText('更新中…')).toBeInTheDocument();
  });

  it('将状态放在合法 tbody 中并覆盖完整列数', () => {
    render(
      <DataTable
        columns={columns.slice(0, 2)}
        data={[]}
        entityName="公司"
        getRowId={(row) => row.id}
        state={{ kind: 'empty', filtered: true }}
      />,
    );

    const cell = screen.getByRole('cell');
    expect(cell).toHaveAttribute('colspan', '2');
    expect(within(cell).getByText('没有符合当前条件的公司')).toBeInTheDocument();
    expect(cell.closest('tbody')).not.toBeNull();
  });

  it('拒绝多个 actions 列，避免固定列契约歧义', () => {
    const invalidColumns = [columns.at(-1)!, { ...columns.at(-1)!, id: 'more-actions' }];

    expect(() =>
      render(
        <DataTable
          columns={invalidColumns}
          data={rows}
          entityName="公司"
          getRowId={(row) => row.id}
        />,
      ),
    ).toThrow('DataTable 仅支持一个 actions 列');
  });
});
