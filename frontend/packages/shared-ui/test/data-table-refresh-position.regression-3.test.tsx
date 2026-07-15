import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DataTable, type DataTableColumn } from '../src/components/data-table';

interface Row {
  id: string;
  name: string;
}

const columns: readonly DataTableColumn<Row>[] = [
  { id: 'name', header: '公司', type: 'text', value: 'name' },
  {
    id: 'actions',
    header: '操作',
    type: 'actions',
    render: () => <button type="button">详情</button>,
  },
];

describe('DataTable 更新提示位置', () => {
  // Regression: 人工 Gate 发现零高度提示层覆盖固定操作表头
  // Found by user acceptance on 2026-07-15
  it('让刷新提示占据独立高度，不再以零高度覆盖表头', () => {
    render(
      <DataTable
        columns={columns}
        data={[{ id: '1', name: '示例公司' }]}
        entityName="公司"
        getRowId={(row) => row.id}
        isRefreshing
      />,
    );

    const status = screen.getByRole('status');
    expect(status).not.toHaveClass('h-0');
    expect(status).toHaveClass('h-8', 'border-b');
    expect(status.nextElementSibling).toBe(screen.getByRole('table'));
  });
});
