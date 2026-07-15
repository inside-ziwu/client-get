import { render, screen } from '@testing-library/react';
import type { ComponentProps } from 'react';
import { describe, expect, it } from 'vitest';
import { CreateButton } from '../src/components/create-button';

describe('CreateButton', () => {
  it('统一使用页面主操作色、40px 高度和 Plus 图标', () => {
    render(<CreateButton>新增公司</CreateButton>);

    const button = screen.getByRole('button', { name: '新增公司' });
    expect(button).toHaveClass(
      'h-10',
      'rounded-ui-md',
      'bg-ui-primary',
      'px-ui-md',
      'text-ui-on-primary',
    );
    expect(button.querySelector('svg')).toHaveAttribute('aria-hidden', 'true');
  });

  it('不允许页面覆盖 variant 和 size 契约', () => {
    type Props = ComponentProps<typeof CreateButton>;
    // @ts-expect-error CreateButton 固定主操作样式
    const invalidVariant: Props = { children: '新增公司', variant: 'outline' };
    // @ts-expect-error CreateButton 固定 40px 高度
    const invalidSize: Props = { children: '新增公司', size: 'sm' };

    expect(invalidVariant).toEqual({ children: '新增公司', variant: 'outline' });
    expect(invalidSize).toEqual({ children: '新增公司', size: 'sm' });
  });
});
