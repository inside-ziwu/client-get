import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { DataTable, type DataTableColumn } from '../src/components/data-table';

interface Row {
  id: string;
  name: string;
  score: number;
  status: string;
  enabled: boolean;
  country: string;
}

const row: Row = {
  id: 'row-1',
  name: '远航科技',
  score: 98,
  status: 'active',
  enabled: true,
  country: '中国',
};

describe('DataTable 列对齐契约', () => {
  it('按内容类型提供稳定的默认对齐', () => {
    const columns: ReadonlyArray<DataTableColumn<Row>> = [
      { id: 'name', header: '名称', type: 'text', value: 'name' },
      { id: 'score', header: '分数', type: 'number', value: 'score' },
      {
        id: 'status',
        header: '状态',
        type: 'status',
        value: 'status',
        statusMap: { active: { label: '启用', tone: 'success' } },
      },
      {
        id: 'enabled',
        header: '可用',
        type: 'boolean',
        value: 'enabled',
        booleanMode: 'readOnly',
        getBooleanLabel: () => '已启用',
      },
      { id: 'actions', header: '操作', type: 'actions', render: () => '查看' },
    ];

    render(<DataTable columns={columns} data={[row]} entityName="示例" getRowId={(item) => item.id} />);

    expect(screen.getByRole('columnheader', { name: '名称' })).toHaveClass('text-left');
    expect(screen.getByText('远航科技').closest('td')).toHaveClass('text-left');
    expect(screen.getByRole('columnheader', { name: '分数' })).toHaveClass('text-right');
    expect(screen.getByText('98').closest('td')).toHaveClass('text-right');
    expect(screen.getByRole('columnheader', { name: '状态' })).toHaveClass('text-center');
    expect(screen.getByText('启用').closest('td')).toHaveClass('text-center');
    expect(screen.getByRole('columnheader', { name: '可用' })).toHaveClass('text-center');
    expect(screen.getByText('已启用').closest('td')).toHaveClass('text-center');
    expect(screen.getByRole('columnheader', { name: '操作' })).toHaveClass('text-right');
    expect(screen.getByText('查看').closest('td')).toHaveClass('text-right');
  });

  it('允许业务列显式覆盖默认对齐，并保持表头与单元格一致', () => {
    const columns: ReadonlyArray<DataTableColumn<Row>> = [
      { id: 'country', header: '国家', type: 'text', value: 'country', align: 'center' },
    ];

    render(<DataTable columns={columns} data={[row]} entityName="示例" getRowId={(item) => item.id} />);

    expect(screen.getByRole('columnheader', { name: '国家' })).toHaveClass('text-center');
    expect(screen.getByText('中国').closest('td')).toHaveClass('text-center');
  });
});
