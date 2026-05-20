'use client';

import { useQuery } from '@tanstack/react-query';
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

  const membersQuery = useQuery({
    queryKey: ['tenant', 'groups', selectedGroupId, 'members'],
    queryFn: async () => (await tenantApi.groups.listMembers(selectedGroupId)).data.data,
    enabled: !!selectedGroupId,
  });

  const groups = groupsQuery.data ?? [];
  const members = membersQuery.data ?? [];

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
                {g.name}（{g.member_count} 人）
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
          {membersQuery.isLoading ? (
            <p className="text-sm text-muted-foreground">加载中...</p>
          ) : members.length === 0 ? (
            <p className="text-sm text-muted-foreground">该群组暂无成员</p>
          ) : (
            <>
              <div className="max-h-64 overflow-auto rounded-md border">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>公司</TableHead>
                      <TableHead>联系人</TableHead>
                      <TableHead>邮箱</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {members.map((m, i) => (
                      <TableRow key={i}>
                        <TableCell>{(m.company_name as string) ?? '-'}</TableCell>
                        <TableCell>{(m.contact_name as string) ?? '-'}</TableCell>
                        <TableCell>{(m.contact_email as string) ?? '-'}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
              <p className="text-sm text-muted-foreground">合计 {members.length} 人</p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
