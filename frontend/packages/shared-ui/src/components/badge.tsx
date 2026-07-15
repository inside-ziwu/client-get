import * as React from 'react';
import { cva, type VariantProps } from 'class-variance-authority';
import { cn } from '../lib/utils';

const badgeVariants = cva('inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium', {
  variants: {
    variant: {
      default: 'bg-primary text-primary-foreground',
      secondary: 'bg-secondary text-secondary-foreground',
      outline: 'border border-border text-foreground',
      destructive: 'bg-destructive text-destructive-foreground',
    },
  },
  defaultVariants: {
    variant: 'default',
  },
});

export type BadgeTone = 'neutral' | 'success' | 'warning' | 'info' | 'danger';

const badgeToneVariants: Record<BadgeTone, string> = {
  neutral: 'bg-ui-surface-card text-ui-body',
  success: 'bg-ui-success-surface text-ui-success-foreground',
  warning: 'bg-ui-warning-surface text-ui-warning-foreground',
  info: 'bg-ui-info-surface text-ui-info-foreground',
  danger: 'bg-ui-danger-surface text-ui-danger-foreground',
};

type LegacyBadgeVariant = VariantProps<typeof badgeVariants>['variant'];

export type BadgeProps = React.HTMLAttributes<HTMLDivElement> &
  (
    | { tone: BadgeTone; variant?: never }
    | { tone?: never; variant?: LegacyBadgeVariant }
  );

export function Badge({ className, tone, variant, ...props }: BadgeProps) {
  const classes = tone
    ? cn(
        'inline-flex items-center rounded-ui-pill px-2 py-0.5 text-ui-caption',
        badgeToneVariants[tone],
      )
    : badgeVariants({ variant });

  return <div className={cn(classes, className)} {...props} />;
}
