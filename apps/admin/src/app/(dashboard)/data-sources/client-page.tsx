'use client';

import type { DataSource, DataSourceCredential } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Edit2, KeyRound, Plus, Save, Trash2 } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Textarea } from '@/components/ui/textarea';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

type SourceForm = {
  source_type: string;
  name: string;
  alias_code: string;
  purpose: string;
  config_json: string;
  landing_rules_json: string;
};

type CredentialForm = {
  id?: string;
  account_no: string;
  username: string;
  secret: string;
  rotation_order: string;
  daily_quota: string;
  is_active: boolean;
  raw_config: Record<string, string>;
};

const SOURCE_TYPES = [
  { value: 'waimao_tong', label: '外贸通' },
  { value: 'tendata', label: '腾道' },
  { value: 'lixiaoyun', label: '励销云' },
];

const CREDENTIAL_FIELDS_BY_TYPE: Record<string, Array<{ key: string; label: string; placeholder?: string }>> = {
  waimao_tong: [
    { key: 'cookie', label: 'Cookie' },
    { key: 'user_agent', label: 'User Agent' },
  ],
  tendata: [
    { key: 'api_key', label: 'API Key' },
    { key: 'endpoint', label: 'Endpoint' },
  ],
  lixiaoyun: [
    { key: 'token', label: 'Token' },
    { key: 'company_id', label: '企业 ID' },
  ],
};

const EMPTY_SOURCE: SourceForm = {
  source_type: 'waimao_tong',
  name: '',
  alias_code: '',
  purpose: '',
  config_json: '{}',
  landing_rules_json: '{}',
};

const EMPTY_CREDENTIAL: CredentialForm = {
  account_no: '',
  username: '',
  secret: '',
  rotation_order: '0',
  daily_quota: '',
  is_active: true,
  raw_config: {},
};

function parseJson(text: string) {
  const trimmed = text.trim();
  return trimmed ? JSON.parse(trimmed) : {};
}

function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

function sourceLabel(type: string) {
  return SOURCE_TYPES.find((item) => item.value === type)?.label ?? type;
}

function sourceToForm(source: DataSource): SourceForm {
  return {
    source_type: source.source_type,
    name: source.name,
    alias_code: source.alias_code ?? '',
    purpose: source.purpose ?? '',
    config_json: formatJson(source.config ?? {}),
    landing_rules_json: formatJson(source.landing_rules ?? {}),
  };
}

function credentialToForm(credential: DataSourceCredential): CredentialForm {
  const raw = credential.raw_config ?? {};
  return {
    id: credential.id,
    account_no: credential.account_no,
    username: credential.username,
    secret: '',
    rotation_order: String(credential.rotation_order ?? 0),
    daily_quota: credential.daily_quota == null ? '' : String(credential.daily_quota),
    is_active: credential.is_active,
    raw_config: Object.fromEntries(Object.entries(raw).map(([key, value]) => [key, String(value ?? '')])),
  };
}

export function DataSourcesPage() {
  const [items, setItems] = useState<DataSource[]>([]);
  const [sourceOpen, setSourceOpen] = useState(false);
  const [credentialOpen, setCredentialOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [selected, setSelected] = useState<DataSource | null>(null);
  const [editingSource, setEditingSource] = useState<DataSource | null>(null);
  const [sourceForm, setSourceForm] = useState<SourceForm>(EMPTY_SOURCE);
  const [credentials, setCredentials] = useState<DataSourceCredential[]>([]);
  const [credentialForm, setCredentialForm] = useState<CredentialForm>(EMPTY_CREDENTIAL);

  const selectedType = selected?.source_type ?? sourceForm.source_type;
  const dynamicFields = useMemo(() => CREDENTIAL_FIELDS_BY_TYPE[selectedType] ?? [], [selectedType]);
  const query = useQuery({
    queryKey: ['admin', 'data-sources'],
    queryFn: async () => (await adminApi.dataSources.list()).data,
  });

  const load = async () => {
    await query.refetch();
  };

  const loadCredentials = async (source: DataSource) => {
    setSelected(source);
    setCredentialOpen(true);
    try {
      const response = await adminApi.dataSources.getCredentials(source.source_type);
      setCredentials(response.data.data);
    } catch {
      toast.error('加载凭证失败');
      setCredentials([]);
    }
  };

  useEffect(() => {
    if (query.isError) {
      toast.error('加载数据源失败');
      return;
    }

    setItems(query.data?.data ?? []);
  }, [query.data, query.isError]);

  const openCreate = () => {
    setEditingSource(null);
    setSourceForm(EMPTY_SOURCE);
    setSourceOpen(true);
  };

  const openEdit = (source: DataSource) => {
    setEditingSource(source);
    setSourceForm(sourceToForm(source));
    setSourceOpen(true);
  };

  const saveSource = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sourceForm.name.trim() || !sourceForm.source_type.trim()) {
      toast.error('请输入来源类型和名称');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        source_type: sourceForm.source_type.trim(),
        name: sourceForm.name.trim(),
        alias_code: sourceForm.alias_code.trim() || undefined,
        purpose: sourceForm.purpose.trim() || undefined,
        config: parseJson(sourceForm.config_json),
        landing_rules: parseJson(sourceForm.landing_rules_json),
      };

      if (editingSource) {
        await adminApi.dataSources.update(editingSource.source_type, payload);
        toast.success('数据源已更新');
      } else {
        await adminApi.dataSources.create(payload);
        toast.success('数据源已创建');
      }

      setSourceOpen(false);
      await load();
    } catch (error) {
      toast.error(error instanceof SyntaxError ? '配置 JSON 格式不正确' : '保存数据源失败');
    } finally {
      setSaving(false);
    }
  };

  const patchConfig = async (source: DataSource) => {
    try {
      await adminApi.dataSources.patchConfig(source.source_type, source.config ?? {});
      toast.success('配置已保存');
    } catch {
      toast.error('保存配置失败');
    }
  };

  const saveCredential = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    setSaving(true);
    try {
      const payload = {
        account_no: credentialForm.account_no.trim(),
        username: credentialForm.username.trim(),
        secret: credentialForm.secret.trim() || undefined,
        rotation_order: Number(credentialForm.rotation_order || 0),
        daily_quota: credentialForm.daily_quota ? Number(credentialForm.daily_quota) : undefined,
        is_active: credentialForm.is_active,
        raw_config: credentialForm.raw_config,
      };
      if (credentialForm.id) {
        await adminApi.dataSources.updateCredential(selected.source_type, credentialForm.id, payload);
        toast.success('凭证已更新');
      } else {
        await adminApi.dataSources.createCredential(selected.source_type, payload);
        toast.success('凭证已创建');
      }
      setCredentialForm(EMPTY_CREDENTIAL);
      await loadCredentials(selected);
    } catch {
      toast.error('保存凭证失败');
    } finally {
      setSaving(false);
    }
  };

  const deleteCredential = async (credential: DataSourceCredential) => {
    if (!selected) return;
    try {
      await adminApi.dataSources.deleteCredential(selected.source_type, credential.id);
      toast.success('凭证已删除');
      await loadCredentials(selected);
    } catch {
      toast.error('删除凭证失败');
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">数据源管理</h1>
          <p className="admin-page-description">管理外贸通、腾道、励销云的数据源配置和轮换凭证。</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          新增数据源
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">名称</th>
                  <th className="px-4 py-3">来源类型</th>
                  <th className="px-4 py-3">别名</th>
                  <th className="px-4 py-3">用途</th>
                  <th className="px-4 py-3">配置 JSON</th>
                  <th className="px-4 py-3 text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b last:border-0">
                    <td className="px-4 py-3 font-medium">{item.name}</td>
                    <td className="px-4 py-3">
                      <Badge variant="secondary">{sourceLabel(item.source_type)}</Badge>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{item.alias_code || '-'}</td>
                    <td className="max-w-[260px] truncate px-4 py-3 text-muted-foreground">{item.purpose || '-'}</td>
                    <td className="max-w-[260px] truncate px-4 py-3 text-xs text-muted-foreground">
                      {formatJson(item.config ?? {})}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" aria-label="编辑数据源" onClick={() => openEdit(item)}>
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <Button variant="ghost" size="icon" aria-label="保存配置" onClick={() => void patchConfig(item)}>
                          <Save className="h-4 w-4" />
                        </Button>
                        <Button variant="outline" size="sm" onClick={() => void loadCredentials(item)}>
                          <KeyRound className="h-4 w-4" />
                          凭证
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!items.length && (
              <div className="py-10 text-center text-sm text-muted-foreground">
                {query.isLoading ? '正在加载数据源...' : '暂无数据源'}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Sheet open={sourceOpen} onOpenChange={setSourceOpen}>
        <SheetContent className="overflow-y-auto p-0 sm:w-[620px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{editingSource ? '编辑数据源' : '新增数据源'}</SheetTitle>
            <SheetDescription>配置 JSON 会在保存前进行格式校验。</SheetDescription>
          </div>
          <form className="space-y-4 p-5" onSubmit={saveSource}>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>来源类型</Label>
                <Select
                  value={sourceForm.source_type}
                  onValueChange={(value) => setSourceForm((current) => ({ ...current, source_type: value }))}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SOURCE_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>名称</Label>
                <Input value={sourceForm.name} onChange={(event) => setSourceForm((c) => ({ ...c, name: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>别名</Label>
                <Input value={sourceForm.alias_code} onChange={(event) => setSourceForm((c) => ({ ...c, alias_code: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>用途</Label>
                <Input value={sourceForm.purpose} onChange={(event) => setSourceForm((c) => ({ ...c, purpose: event.target.value }))} />
              </div>
            </div>
            <div className="space-y-2">
              <Label>配置 JSON</Label>
              <Textarea className="min-h-40 font-mono text-xs" value={sourceForm.config_json} onChange={(event) => setSourceForm((c) => ({ ...c, config_json: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>落库规则 JSON</Label>
              <Textarea className="min-h-32 font-mono text-xs" value={sourceForm.landing_rules_json} onChange={(event) => setSourceForm((c) => ({ ...c, landing_rules_json: event.target.value }))} />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setSourceOpen(false)}>
                取消
              </Button>
              <Button type="submit" disabled={saving}>
                保存
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>

      <Sheet open={credentialOpen} onOpenChange={setCredentialOpen}>
        <SheetContent className="max-w-3xl overflow-y-auto p-0 sm:w-[760px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{selected ? `${selected.name} · 凭证` : '凭证管理'}</SheetTitle>
            <SheetDescription>按来源类型展示动态凭证表单，敏感字段留空表示不更新。</SheetDescription>
          </div>
          <div className="space-y-5 p-5">
            <form className="space-y-3 rounded-md border p-4" onSubmit={saveCredential}>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="space-y-2">
                  <Label>账号编号</Label>
                  <Input value={credentialForm.account_no} onChange={(event) => setCredentialForm((c) => ({ ...c, account_no: event.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>用户名</Label>
                  <Input value={credentialForm.username} onChange={(event) => setCredentialForm((c) => ({ ...c, username: event.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>Secret</Label>
                  <Input type="password" value={credentialForm.secret} onChange={(event) => setCredentialForm((c) => ({ ...c, secret: event.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>轮换顺序</Label>
                  <Input type="number" value={credentialForm.rotation_order} onChange={(event) => setCredentialForm((c) => ({ ...c, rotation_order: event.target.value }))} />
                </div>
                <div className="space-y-2">
                  <Label>每日额度</Label>
                  <Input type="number" value={credentialForm.daily_quota} onChange={(event) => setCredentialForm((c) => ({ ...c, daily_quota: event.target.value }))} />
                </div>
                <label className="flex items-end gap-2 pb-2 text-sm">
                  <Checkbox checked={credentialForm.is_active} onCheckedChange={(checked) => setCredentialForm((c) => ({ ...c, is_active: checked === true }))} />
                  启用
                </label>
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                {dynamicFields.map((field) => (
                  <div key={field.key} className="space-y-2">
                    <Label>{field.label}</Label>
                    <Input
                      placeholder={field.placeholder}
                      value={credentialForm.raw_config[field.key] ?? ''}
                      onChange={(event) =>
                        setCredentialForm((current) => ({
                          ...current,
                          raw_config: { ...current.raw_config, [field.key]: event.target.value },
                        }))
                      }
                    />
                  </div>
                ))}
              </div>
              <div className="flex justify-end gap-2">
                <Button type="button" variant="outline" onClick={() => setCredentialForm(EMPTY_CREDENTIAL)}>
                  清空
                </Button>
                <Button type="submit" disabled={saving}>
                  保存凭证
                </Button>
              </div>
            </form>

            <div className="overflow-x-auto rounded-md border">
              <table className="w-full min-w-[720px] text-sm">
                <thead className="bg-muted/70 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">账号编号</th>
                    <th className="px-3 py-2">用户名</th>
                    <th className="px-3 py-2">Secret</th>
                    <th className="px-3 py-2">今日用量</th>
                    <th className="px-3 py-2">每日额度</th>
                    <th className="px-3 py-2">创建时间</th>
                    <th className="px-3 py-2 text-right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {credentials.map((credential) => (
                    <tr key={credential.id} className="border-t">
                      <td className="px-3 py-2 font-medium">{credential.account_no}</td>
                      <td className="px-3 py-2">{credential.username}</td>
                      <td className="px-3 py-2 text-muted-foreground">{credential.secret_masked ?? '-'}</td>
                      <td className="px-3 py-2">{credential.current_day_used}</td>
                      <td className="px-3 py-2">{credential.daily_quota ?? '-'}</td>
                      <td className="px-3 py-2 text-muted-foreground">{formatDateTime(credential.created_at)}</td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" onClick={() => setCredentialForm(credentialToForm(credential))}>
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <AlertDialog>
                            <AlertDialogTrigger asChild>
                              <Button variant="ghost" size="icon" aria-label="删除凭证">
                                <Trash2 className="h-4 w-4 text-destructive" />
                              </Button>
                            </AlertDialogTrigger>
                            <AlertDialogContent>
                              <AlertDialogTitle>确认删除该凭证？</AlertDialogTitle>
                              <AlertDialogDescription>删除后采集轮换不会再使用该账号。</AlertDialogDescription>
                              <div className="flex justify-end gap-2">
                                <AlertDialogCancel>取消</AlertDialogCancel>
                                <AlertDialogAction onClick={() => void deleteCredential(credential)}>删除</AlertDialogAction>
                              </div>
                            </AlertDialogContent>
                          </AlertDialog>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
