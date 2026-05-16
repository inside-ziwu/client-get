import type { SendingPlanStatus } from '@shared/types';
import { Badge } from './components/badge';

const STATUS_CONFIG: Record<SendingPlanStatus, { className: string; label: string }> = {
  draft: { className: 'bg-slate-100 text-slate-700', label: '草稿' },
  scheduled: { className: 'bg-sky-100 text-sky-800', label: '已排期' },
  running: { className: 'bg-emerald-100 text-emerald-800', label: '执行中' },
  paused: { className: 'bg-amber-100 text-amber-800', label: '已暂停' },
  completed: { className: 'bg-blue-100 text-blue-800', label: '已完成' },
  cancelled: { className: 'bg-red-100 text-red-800', label: '已取消' },
};

export interface StatusTagProps {
  status: SendingPlanStatus;
}

export function StatusTag({ status }: StatusTagProps) {
  const config = STATUS_CONFIG[status] ?? { className: 'bg-slate-100 text-slate-700', label: status };
  return (
    <Badge variant="secondary" className={config.className}>
      {config.label}
    </Badge>
  );
}
