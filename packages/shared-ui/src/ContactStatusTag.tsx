import type { TenantContactStatus } from '@shared/types';
import { Badge } from './components/badge';

const CONTACT_STATUS_CONFIG: Record<TenantContactStatus, { className: string; label: string }> = {
  available: { className: 'bg-slate-100 text-slate-700', label: '可用' },
  in_plan: { className: 'bg-sky-100 text-sky-800', label: '计划中' },
  contacted: { className: 'bg-cyan-100 text-cyan-800', label: '已联系' },
  replied: { className: 'bg-emerald-100 text-emerald-800', label: '已回复' },
  bounced: { className: 'bg-red-100 text-red-800', label: '已退信' },
  unsubscribed: { className: 'bg-slate-100 text-slate-700', label: '已退订' },
};

export interface ContactStatusTagProps {
  status: TenantContactStatus;
}

export function ContactStatusTag({ status }: ContactStatusTagProps) {
  const config = CONTACT_STATUS_CONFIG[status] ?? { className: 'bg-slate-100 text-slate-700', label: status };
  return (
    <Badge variant="secondary" className={config.className}>
      {config.label}
    </Badge>
  );
}
