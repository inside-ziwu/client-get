import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { useState } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { CompanyListFilterBar } from '@/app/(dashboard)/companies/company-list-filter-bar';
import { EMPTY_FILTERS, type FilterValues } from '@/components/company-filters';

afterEach(() => cleanup());

function ControlledFilterBar({ onSubmit }: { onSubmit: (values: FilterValues) => void }) {
  const [values, setValues] = useState<FilterValues>(EMPTY_FILTERS);

  return (
    <CompanyListFilterBar
      values={values}
      optionsState="ready"
      appliedCount={0}
      isSubmitting={false}
      onChange={setValues}
      onSubmit={onSubmit}
      onReset={vi.fn()}
    />
  );
}

describe('公司列表范围筛选', () => {
  it('把八个底层数值字段合并为四个一体式业务范围组件', () => {
    render(<ControlledFilterBar onSubmit={vi.fn()} />);

    expect(screen.getByTestId('filter-bar-fields').children).toHaveLength(12);

    for (const label of ['进口额', '进口次数', '联系人', '成立年份']) {
      const group = screen.getByRole('group', { name: label });
      expect(within(group).getAllByRole('spinbutton')).toHaveLength(2);
      expect(group).toHaveAttribute('data-filter-kind', 'custom');
      expect(group).toHaveClass('w-full', 'sm:w-64');
      expect(group.querySelector('[data-range-control]')).toHaveClass(
        'border',
        'rounded-ui-md',
      );
    }

    expect(screen.getByLabelText('最低进口额')).toBeVisible();
    expect(screen.getByLabelText('最高进口额')).toBeVisible();
    expect(screen.getByLabelText('成立年份起')).toBeVisible();
    expect(screen.getByLabelText('成立年份止')).toBeVisible();
  });

  it('编辑范围后仍按原有八个字段提交查询', () => {
    const onSubmit = vi.fn();
    render(<ControlledFilterBar onSubmit={onSubmit} />);

    fireEvent.change(screen.getByLabelText('最低进口额'), { target: { value: '1000' } });
    fireEvent.change(screen.getByLabelText('最高进口额'), { target: { value: '9000' } });
    fireEvent.change(screen.getByLabelText('最低进口次数'), { target: { value: '2' } });
    fireEvent.change(screen.getByLabelText('最高进口次数'), { target: { value: '20' } });
    fireEvent.change(screen.getByLabelText('最少联系人'), { target: { value: '1' } });
    fireEvent.change(screen.getByLabelText('最多联系人'), { target: { value: '12' } });
    fireEvent.change(screen.getByLabelText('成立年份起'), { target: { value: '2000' } });
    fireEvent.change(screen.getByLabelText('成立年份止'), { target: { value: '2024' } });
    fireEvent.click(screen.getByRole('button', { name: '查询' }));

    expect(onSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        trade_amount_min: '1000',
        trade_amount_max: '9000',
        trade_count_min: '2',
        trade_count_max: '20',
        contact_count_min: '1',
        contact_count_max: '12',
        founded_year_from: '2000',
        founded_year_to: '2024',
      }),
    );
  });
});
