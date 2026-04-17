import { Tag } from 'antd';
import type { TenantContactStatus } from '@shared/types';

const CONTACT_STATUS_CONFIG: Record<TenantContactStatus, { color: string; label: string }> = {
  available: { color: 'default', label: '可用' },
  in_plan: { color: 'blue', label: '计划中' },
  contacted: { color: 'cyan', label: '已联系' },
  replied: { color: 'green', label: '已回复' },
  bounced: { color: 'error', label: '已退信' },
  unsubscribed: { color: 'default', label: '已退订' },
};

export interface ContactStatusTagProps {
  status: TenantContactStatus;
}

export function ContactStatusTag({ status }: ContactStatusTagProps) {
  const config = CONTACT_STATUS_CONFIG[status] ?? { color: 'default', label: status };
  return <Tag color={config.color}>{config.label}</Tag>;
}
