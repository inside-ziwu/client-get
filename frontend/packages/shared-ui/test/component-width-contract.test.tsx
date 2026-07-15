import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { DataTable, type DataTableColumn } from '../src/components/data-table';
import { FilterBar, type FilterField } from '../src/components/filter-bar';

type FilterDraft = {
  defaultField: string;
  smallField: string;
  largeField: string;
  customField: string;
};

const filterValues: FilterDraft = {
  defaultField: '',
  smallField: '',
  largeField: '',
  customField: '',
};

const filterFields: ReadonlyArray<FilterField<FilterDraft>> = [
  { name: 'defaultField', kind: 'text', label: '默认字段' },
  {
    name: 'smallField',
    kind: 'select',
    label: '小字段',
    width: 'small',
    options: [{ label: '选项', value: 'option' }],
  },
  { name: 'largeField', kind: 'text', label: '大字段', width: 'large' },
  {
    name: 'customField',
    kind: 'text',
    label: '自定义字段',
    width: { custom: 256 },
  },
];

interface Row {
  id: string;
  defaultValue: string;
  smallValue: string;
  largeValue: string;
  customValue: string;
}

const tableColumns: ReadonlyArray<DataTableColumn<Row>> = [
  { id: 'default', header: '默认列', type: 'text', value: 'defaultValue' },
  { id: 'small', header: '小列', type: 'text', value: 'smallValue', width: 'small' },
  { id: 'large', header: '大列', type: 'text', value: 'largeValue', width: 'large' },
  {
    id: 'custom',
    header: '自定义列',
    type: 'text',
    value: 'customValue',
    width: { custom: 256 },
  },
];

describe('共享组件宽度契约', () => {
  it('FilterBar 默认使用 medium，并支持三个预设与显式自定义宽度', () => {
    render(
      <FilterBar
        values={filterValues}
        fields={filterFields}
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onReset={vi.fn()}
        layout="compact"
        collapseAdvanced={false}
      />,
    );

    const defaultField = screen.getByLabelText('默认字段').closest('[data-filter-kind="text"]');
    const smallField = screen.getByLabelText('小字段').closest('[data-filter-kind="select"]');
    const largeField = screen.getByLabelText('大字段').closest('[data-filter-kind="text"]');
    const customField = screen.getByLabelText('自定义字段').closest('[data-filter-kind="text"]');

    expect(defaultField).toHaveClass('sm:w-ui-control-medium');
    expect(smallField).toHaveClass('sm:w-ui-control-small');
    expect(largeField).toHaveClass('sm:w-ui-control-large');
    expect(customField).toHaveClass('sm:w-[var(--filter-field-width)]');
    expect((customField as HTMLElement).style.getPropertyValue('--filter-field-width')).toBe(
      '256px',
    );
    expect([defaultField, smallField, largeField, customField].flatMap((field) => [
      ...(field?.classList ?? []),
    ])).not.toContain('sm:!w-56');
  });

  it('DataTable 默认使用 medium，并支持三个预设与显式自定义宽度', () => {
    render(
      <DataTable
        columns={tableColumns}
        data={[
          {
            id: 'row-1',
            defaultValue: '默认',
            smallValue: '小',
            largeValue: '大',
            customValue: '自定义',
          },
        ]}
        entityName="示例"
        getRowId={(row) => row.id}
      />,
    );

    const columns = screen.getByRole('table').querySelectorAll('col');
    expect(columns[0]).toHaveClass(
      'w-ui-table-medium',
      'min-w-ui-table-medium',
      'max-w-ui-table-medium',
    );
    expect(columns[1]).toHaveClass(
      'w-ui-table-small',
      'min-w-ui-table-small',
      'max-w-ui-table-small',
    );
    expect(columns[2]).toHaveClass(
      'w-ui-table-large',
      'min-w-ui-table-large',
      'max-w-ui-table-large',
    );
    expect(columns[3]).toHaveStyle({ width: '256px', minWidth: '256px', maxWidth: '256px' });
  });
});
