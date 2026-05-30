'use client';

import { Fragment, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { ChevronDown, ChevronRight } from 'lucide-react';
import {
  Checkbox,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import type { PreviewRecipientCompany } from '@shared/api';

interface Props {
  recipientConfig: Record<string, string>;
  lockRecipients: boolean;
  onChange: (patch: { recipient_config?: Record<string, string>; lock_recipients?: boolean }) => void;
  errors: Record<string, string>;
}

export function validateRecipients(recipientConfig: Record<string, string>): Record<string, string> {
  const errors: Record<string, string> = {};
  if (!recipientConfig.group_id) errors.group_id = '请选择群组';
  return errors;
}

export default function StepRecipients({ recipientConfig, lockRecipients, onChange, errors }: Props) {
  const groupsQuery = useQuery({
    queryKey: ['tenant', 'groups'],
    queryFn: async () => (await tenantApi.groups.list()).data.data,
  });

  const selectedGroupId = recipientConfig.group_id ?? '';

  const previewQuery = useQuery({
    queryKey: ['tenant', 'sending-plans', 'preview-recipients', selectedGroupId],
    queryFn: async () => (await tenantApi.sendingPlans.previewGroupRecipients(selectedGroupId)).data.data,
    enabled: !!selectedGroupId,
  });

  const groups = groupsQuery.data ?? [];
  const preview = previewQuery.data;

  return (
    <div className="max-w-2xl space-y-4">
      <div className="space-y-2">
        <Label>收件人来源</Label>
        <p className="text-sm text-muted-foreground">按群组</p>
      </div>

      <div className="space-y-2">
        <Label>选择群组 *</Label>
        <Select
          value={selectedGroupId}
          onValueChange={(v) => onChange({ recipient_config: { group_id: v } })}
        >
          <SelectTrigger>
            <SelectValue placeholder={groupsQuery.isLoading ? '加载中...' : groups.length === 0 ? '无可用群组' : '选择群组'} />
          </SelectTrigger>
          <SelectContent>
            {groups.map((g) => (
              <SelectItem key={g.id} value={g.id}>
                {g.name}（{g.member_count} 家公司）
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {errors.group_id && <p className="text-sm text-destructive">{errors.group_id}</p>}
      </div>

      <div className="flex items-center gap-2">
        <Checkbox
          id="lock-recipients"
          checked={lockRecipients}
          onCheckedChange={(checked) => onChange({ lock_recipients: checked === true })}
        />
        <Label htmlFor="lock-recipients" className="cursor-pointer">
          创建后立即锁定收件人
        </Label>
      </div>

      {selectedGroupId && (
        <div className="space-y-2">
          <Label>收件人预览</Label>
          {previewQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">加载中...</p>
          ) : !preview || preview.companies.length === 0 ? (
            <p className="text-sm text-muted-foreground">该群组暂无有效收件人</p>
          ) : (
            <>
              <div className="max-h-80 overflow-auto rounded-md border">
                <CompanyRecipientList companies={preview.companies} />
              </div>
              <p className="text-sm text-muted-foreground">
                合计 {preview.summary.company_count} 家公司，{preview.summary.recipient_count} 位收件人
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function CompanyRecipientList({ companies }: { companies: PreviewRecipientCompany[] }) {
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead className="w-8" />
          <TableHead>公司</TableHead>
          <TableHead className="text-right">收件人数</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {companies.map((co) => {
          const isOpen = expanded[co.tenant_company_id] ?? false;
          const validRecipients = co.recipients.filter((r) => r.excluded_reason === null);
          return (
            <Fragment key={co.tenant_company_id}>
              <TableRow
                className="cursor-pointer hover:bg-muted/50"
                onClick={() => setExpanded((prev) => ({ ...prev, [co.tenant_company_id]: !isOpen }))}
              >
                <TableCell className="w-8 px-2">
                  {isOpen ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </TableCell>
                <TableCell className="font-medium">{co.company_name}</TableCell>
                <TableCell className="text-right">{co.recipient_count} 人</TableCell>
              </TableRow>
              {isOpen && validRecipients.map((r, i) => (
                <TableRow key={`${co.tenant_company_id}-${i}`} className="bg-muted/30">
                  <TableCell />
                  <TableCell className="pl-8 text-sm text-muted-foreground">
                    {r.contact_name ?? '-'}
                    {r.level_name && (
                      <span className="ml-2 rounded bg-primary/10 px-1.5 py-0.5 text-xs">{r.level_name}</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right text-sm text-muted-foreground">{r.contact_email}</TableCell>
                </TableRow>
              ))}
            </Fragment>
          );
        })}
      </TableBody>
    </Table>
  );
}
