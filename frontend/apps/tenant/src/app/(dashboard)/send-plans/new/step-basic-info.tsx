'use client';

import { useQuery } from '@tanstack/react-query';
import { Input, Label, Select, SelectContent, SelectItem, SelectTrigger, SelectValue, Textarea } from '@shared/ui';
import { tenantApi } from '@/lib/api';

export interface PlanBasicInfo {
  name: string;
  description: string;
  sender_name: string;
  sender_email: string;
  domain_id: string;
}

interface Props {
  data: PlanBasicInfo;
  onChange: (data: PlanBasicInfo) => void;
  errors: Record<string, string>;
}

export function validateBasicInfo(data: PlanBasicInfo): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!data.name.trim()) errors.name = '请输入计划名称';
  if (!data.sender_name.trim()) errors.sender_name = '请输入发件人名称';
  if (!data.sender_email.trim()) errors.sender_email = '请输入发件邮箱';
  if (!data.domain_id) errors.domain_id = '请选择发送域名';
  return errors;
}

export default function StepBasicInfo({ data, onChange, errors }: Props) {
  const domainsQuery = useQuery({
    queryKey: ['tenant', 'domains'],
    queryFn: async () => (await tenantApi.domains.list()).data.data,
  });

  const verifiedDomains = (domainsQuery.data ?? []).filter((d) => d.verification_status === 'verified');

  const update = (field: keyof PlanBasicInfo, value: string) => {
    onChange({ ...data, [field]: value });
  };

  return (
    <div className="max-w-2xl space-y-4">
      <div className="space-y-2">
        <Label htmlFor="plan-name">计划名称 *</Label>
        <Input id="plan-name" value={data.name} onChange={(e) => update('name', e.target.value)} placeholder="例：Q3 客户推广" />
        {errors.name && <p className="text-sm text-destructive">{errors.name}</p>}
      </div>

      <div className="space-y-2">
        <Label htmlFor="plan-desc">描述</Label>
        <Textarea id="plan-desc" value={data.description} onChange={(e) => update('description', e.target.value)} placeholder="可选" />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="sender-name">发件人名称 *</Label>
          <Input id="sender-name" value={data.sender_name} onChange={(e) => update('sender_name', e.target.value)} placeholder="例：张三" />
          {errors.sender_name && <p className="text-sm text-destructive">{errors.sender_name}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="sender-email">发件邮箱 *</Label>
          <Input id="sender-email" type="email" value={data.sender_email} onChange={(e) => update('sender_email', e.target.value)} placeholder="例：contact@example.com" />
          {errors.sender_email && <p className="text-sm text-destructive">{errors.sender_email}</p>}
        </div>
      </div>

      <div className="space-y-2">
        <Label>发送域名 *</Label>
        <Select value={data.domain_id} onValueChange={(v) => {
          const selected = verifiedDomains.find((d) => d.id === v);
          onChange({ ...data, domain_id: v, sender_email: selected?.sender_email ?? '' });
        }}>
          <SelectTrigger>
            <SelectValue placeholder={domainsQuery.isLoading ? '加载中...' : verifiedDomains.length === 0 ? '无已验证域名' : '选择域名'} />
          </SelectTrigger>
          <SelectContent>
            {verifiedDomains.map((d) => (
              <SelectItem key={d.id} value={d.id}>{d.domain}</SelectItem>
            ))}
          </SelectContent>
        </Select>
        {errors.domain_id && <p className="text-sm text-destructive">{errors.domain_id}</p>}
      </div>
    </div>
  );
}
