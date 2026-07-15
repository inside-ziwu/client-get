import { cleanup, fireEvent, render, screen, within } from '@testing-library/react';
import { afterEach, beforeAll, describe, expect, it, vi } from 'vitest';
import { EMPTY_FILTERS } from '@/components/company-filters';
import { CompanyListFilterBar } from '@/app/(dashboard)/companies/company-list-filter-bar';

const baseProps = {
  values: EMPTY_FILTERS,
  appliedCount: 0,
  isSubmitting: false,
  onChange: vi.fn(),
  onSubmit: vi.fn(),
  onReset: vi.fn(),
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

afterEach(() => cleanup());

describe('公司筛选选项反馈', () => {
  it('产品标签加载中仍可打开，并在弹层内显示明确状态', () => {
    render(
      <CompanyListFilterBar
        {...baseProps}
        optionsState="loading"
      />,
    );

    const trigger = within(screen.getByRole('group', { name: '产品标签' })).getByRole('button');
    expect(trigger).toBeEnabled();
    fireEvent.click(trigger);

    expect(screen.getByPlaceholderText('搜索产品标签')).toBeDisabled();
    expect(screen.getByRole('status')).toHaveTextContent('正在加载选项…');
  });

  it('未选择时统一显示不限，并为弹层搜索和数值框提供明确提示', () => {
    render(
      <CompanyListFilterBar
        {...baseProps}
        options={{
          countries: ['CHN'],
          sub_industries: ['PCB'],
          product_tags: ['HDI'],
          grades: ['A'],
        }}
        optionsState="ready"
      />,
    );

    const countryTrigger = within(screen.getByRole('group', { name: '国家' })).getByRole('button');
    expect(countryTrigger).toHaveTextContent('不限');
    fireEvent.click(countryTrigger);
    expect(screen.getByPlaceholderText('搜索国家')).toBeEnabled();
    expect(screen.getByLabelText('最低进口额')).toHaveAttribute('placeholder', '不限');
  });
});
