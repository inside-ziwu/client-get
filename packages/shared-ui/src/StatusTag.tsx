import { Tag } from 'antd';
import type { SendingPlanStatus } from '@shared/types';

const STATUS_CONFIG: Record<SendingPlanStatus, { color: string; label: string }> = {
  draft: { color: 'default', label: '草稿' },
  scheduled: { color: 'blue', label: '已排期' },
  running: { color: 'processing', label: '执行中' },
  paused: { color: 'warning', label: '已暂停' },
  completed: { color: 'success', label: '已完成' },
  cancelled: { color: 'error', label: '已取消' },
};

export interface StatusTagProps {
  status: SendingPlanStatus;
}

export function StatusTag({ status }: StatusTagProps) {
  const config = STATUS_CONFIG[status] ?? { color: 'default', label: status };
  return <Tag color={config.color}>{config.label}</Tag>;
}
