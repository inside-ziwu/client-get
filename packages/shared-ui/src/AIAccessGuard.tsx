import React from 'react';
import { Tooltip } from 'antd';
import type { AiCapabilityFeatureState } from '@shared/types';

export interface AIAccessGuardProps {
  feature?: AiCapabilityFeatureState | null;
  fallbackTitle?: string;
  children: React.ReactElement<{ disabled?: boolean }>;
}

const REASON_MESSAGES: Record<string, string> = {
  insufficient_permission: '当前账号没有执行该 AI 操作的权限。',
  not_configured: '当前租户尚未配置 OpenRouter API key。',
  insufficient_balance: '当前租户的 OpenRouter 余额不足。',
  balance_unknown: '当前无法判定 OpenRouter 剩余额度。',
  invalid_api_key: '当前租户配置的 OpenRouter API key 无效。',
  provider_error: 'OpenRouter 服务暂时不可用，请稍后重试。',
  unavailable: '当前 AI 能力暂不可用。',
};

export function AIAccessGuard({ feature, fallbackTitle, children }: AIAccessGuardProps) {
  const disabled = feature ? !feature.available : true;
  const title = fallbackTitle ?? (feature?.reason ? REASON_MESSAGES[feature.reason] : '当前 AI 能力暂不可用。');

  if (disabled) {
    return (
      <Tooltip title={title}>
        {React.cloneElement(children, { disabled: true })}
      </Tooltip>
    );
  }
  return children;
}
