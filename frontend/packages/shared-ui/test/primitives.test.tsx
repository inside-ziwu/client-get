import { fireEvent, render, screen } from '@testing-library/react';
import type { ComponentProps } from 'react';
import { describe, expect, it, vi } from 'vitest';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
} from '../src/components/alert-dialog';
import { Badge, type BadgeTone } from '../src/components/badge';
import { MultiSelect } from '../src/components/multi-select';

describe('Badge', () => {
  it.each<[BadgeTone, string, string]>([
    ['neutral', 'bg-ui-surface-card', 'text-ui-body'],
    ['success', 'bg-ui-success-surface', 'text-ui-success-foreground'],
    ['warning', 'bg-ui-warning-surface', 'text-ui-warning-foreground'],
    ['info', 'bg-ui-info-surface', 'text-ui-info-foreground'],
    ['danger', 'bg-ui-danger-surface', 'text-ui-danger-foreground'],
  ])('tone=%s 使用对应的语义颜色', (tone, backgroundClass, foregroundClass) => {
    render(<Badge tone={tone}>状态</Badge>);

    expect(screen.getByText('状态')).toHaveClass(backgroundClass, foregroundClass, 'rounded-ui-pill');
  });

  it('不传 tone 时保留旧 default variant 行为', () => {
    render(<Badge>默认状态</Badge>);

    expect(screen.getByText('默认状态')).toHaveClass('bg-primary', 'text-primary-foreground');
  });

  it('保留旧 outline variant 行为', () => {
    render(<Badge variant="outline">旧状态</Badge>);

    expect(screen.getByText('旧状态')).toHaveClass('border-border', 'text-foreground');
  });

  it('类型上禁止同时传 tone 与 legacy variant', () => {
    type BadgeProps = ComponentProps<typeof Badge>;
    const toneProps: BadgeProps = { tone: 'success' };
    const legacyProps: BadgeProps = { variant: 'secondary' };
    // @ts-expect-error tone 与 legacy variant 表达两套互斥的视觉意图
    const conflictingProps: BadgeProps = { tone: 'success', variant: 'secondary' };

    expect(toneProps).toEqual({ tone: 'success' });
    expect(legacyProps).toEqual({ variant: 'secondary' });
    expect(conflictingProps).toEqual({ tone: 'success', variant: 'secondary' });
  });
});

describe('AlertDialogAction', () => {
  function renderAction(variant?: 'default' | 'destructive') {
    render(
      <AlertDialog defaultOpen>
        <AlertDialogContent>
          <AlertDialogTitle>确认操作</AlertDialogTitle>
          <AlertDialogDescription>此操作需要确认。</AlertDialogDescription>
          <AlertDialogAction variant={variant}>确认</AlertDialogAction>
        </AlertDialogContent>
      </AlertDialog>,
    );
  }

  it('默认继续使用主按钮样式', () => {
    renderAction();

    expect(screen.getByRole('button', { name: '确认' })).toHaveClass('bg-primary');
  });

  it('destructive variant 使用危险按钮样式', () => {
    renderAction('destructive');

    expect(screen.getByRole('button', { name: '确认' })).toHaveClass('bg-destructive');
  });
});

describe('MultiSelect', () => {
  const values = ['pcb'] as const;
  const options = [
    { label: 'PCB', value: 'pcb' },
    { label: 'PCBA', value: 'pcba' },
  ] as const;

  it('接受 readonly value/options 并仍能输出可变的新值', () => {
    const onChange = vi.fn();
    render(<MultiSelect value={values} options={options} onChange={onChange} />);

    fireEvent.click(screen.getByRole('button', { name: '移除 pcb' }));

    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange).toHaveBeenCalledWith([]);
  });

  it('disabled 时禁用触发器且不暴露移除操作', () => {
    const onChange = vi.fn();
    render(<MultiSelect value={values} options={options} onChange={onChange} disabled />);

    const trigger = screen.getByRole('button');
    expect(trigger).toBeDisabled();
    expect(screen.queryByRole('button', { name: '移除 pcb' })).not.toBeInTheDocument();

    fireEvent.click(trigger);
    expect(screen.queryByPlaceholderText('选择或输入')).not.toBeInTheDocument();
    expect(onChange).not.toHaveBeenCalled();
  });
});
