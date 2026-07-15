import { Plus } from 'lucide-react';
import * as React from 'react';
import { cn } from '../lib/utils';
import { Button, type ButtonProps } from './button';

export type CreateButtonProps = Omit<ButtonProps, 'variant' | 'size'>;

export const CreateButton = React.forwardRef<HTMLButtonElement, CreateButtonProps>(
  ({ children, className, ...props }, ref) => (
    <Button
      ref={ref}
      size="lg"
      className={cn(
        'rounded-ui-md bg-ui-primary px-ui-md text-ui-on-primary hover:bg-ui-primary-active focus-visible:ring-ui-foreground',
        className,
      )}
      {...props}
    >
      <Plus aria-hidden="true" className="h-4 w-4" />
      {children}
    </Button>
  ),
);
CreateButton.displayName = 'CreateButton';
