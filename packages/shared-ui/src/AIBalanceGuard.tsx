import React from 'react';
import { Tooltip } from 'antd';

export interface AIBalanceGuardProps {
  balance: number;
  children: React.ReactElement<{ disabled?: boolean }>;
}

export function AIBalanceGuard({ balance, children }: AIBalanceGuardProps) {
  const disabled = balance <= 0;

  if (disabled) {
    return (
      <Tooltip title="AI余额不足，请充值">
        {React.cloneElement(children, { disabled: true })}
      </Tooltip>
    );
  }
  return children;
}
