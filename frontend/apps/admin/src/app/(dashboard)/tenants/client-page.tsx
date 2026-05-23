'use client';

import type { Tenant, TenantDomain, TenantTeamUser, WarmupRules } from '@shared/api';
import type { AiProviderConfig } from '@shared/types';
import { useQuery } from '@tanstack/react-query';
import { CheckCircle2, Copy, Edit2, Plus, RefreshCw, Search, ShieldCheck, Trash2 } from 'lucide-react';
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
} from '@shared/ui';
import { Badge } from '@shared/ui';
import { Button } from '@shared/ui';
import { Card, CardContent } from '@shared/ui';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@shared/ui';
import { Input } from '@shared/ui';
import { Label } from '@shared/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@shared/ui';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@shared/ui';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@shared/ui';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

type TenantForm = {
  name: string;
  industry: string;
  contact_name: string;
  contact_phone: string;
  contact_email: string;
  admin_email: string;
  admin_name: string;
  admin_password: string;
};

type TenantEditForm = Pick<TenantForm, 'name' | 'industry' | 'contact_name' | 'contact_phone' | 'contact_email'>;

type TenantCreatePayload = Partial<Tenant> & {
  admin_email: string;
  admin_name: string;
  admin_password: string;
};

const EMPTY_TENANT: TenantForm = {
  name: '',
  industry: '',
  contact_name: '',
  contact_phone: '',
  contact_email: '',
  admin_email: '',
  admin_name: '',
  admin_password: '',
};

const EMPTY_TEAM_FORM = { email: '', name: '', roles: 'admin', status: 'active', password: '' };

function statusLabel(status: Tenant['status']) {
  return status === 'active' ? '启用' : status === 'suspended' ? '暂停' : '归档';
}

function userStatusLabel(status: string) {
  return status === 'active' ? '启用' : status === 'disabled' ? '停用' : status;
}

function roleLabel(role: string) {
  const labels: Record<string, string> = { admin: '管理员', operator: '运营', viewer: '查看者' };
  return labels[role] ?? role;
}

function verificationLabel(status: TenantDomain['verification_status']) {
  const labels: Record<TenantDomain['verification_status'], string> = {
    pending: '待验证',
    verifying: '验证中',
    verified: '已验证',
    failed: '验证失败',
  };
  return labels[status] ?? status;
}

function balanceStatusLabel(status?: string) {
  const labels: Record<string, string> = {
    available: '可用',
    insufficient_balance: '余额不足',
    unknown: '未知',
    invalid_api_key: 'Key 无效',
    provider_error: '服务异常',
    not_configured: '未配置',
  };
  return status ? labels[status] ?? status : '-';
}

function getTenantAdminUrl(tenant: Tenant | null) {
  if (!tenant?.slug) return '';
  return `https://tenant.xinanpcb.com/login?slug=${tenant.slug}`;
}

function toEditForm(tenant: Tenant | null): TenantEditForm {
  return {
    name: tenant?.name ?? '',
    industry: tenant?.industry ?? '',
    contact_name: tenant?.contact_name ?? '',
    contact_phone: tenant?.contact_phone ?? '',
    contact_email: tenant?.contact_email ?? '',
  };
}

export function TenantsPage() {
  const [items, setItems] = useState<Tenant[]>([]);
  const [keyword, setKeyword] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [selected, setSelected] = useState<Tenant | null>(null);
  const [tenantForm, setTenantForm] = useState<TenantForm>(EMPTY_TENANT);
  const [tenantEditForm, setTenantEditForm] = useState<TenantEditForm>(toEditForm(null));
  const [domains, setDomains] = useState<TenantDomain[]>([]);
  const [domainText, setDomainText] = useState('');
  const [domainSenderEmail, setDomainSenderEmail] = useState('');
  const [warmupRules, setWarmupRules] = useState<WarmupRules | null>(null);
  const [domainWarmupRuleId, setDomainWarmupRuleId] = useState('');
  const [domainWarmupLevel, setDomainWarmupLevel] = useState('');
  const [editingDomain, setEditingDomain] = useState<TenantDomain | null>(null);
  const [editDomainForm, setEditDomainForm] = useState({ sender_email: '', warmup_rule_id: '', warmup_level: '' });
  const [editDomainLoading, setEditDomainLoading] = useState(false);
  const [deletingDomain, setDeletingDomain] = useState<TenantDomain | null>(null);
  const [deleteDomainLoading, setDeleteDomainLoading] = useState(false);
  const [deleteDomainError, setDeleteDomainError] = useState('');
  const [team, setTeam] = useState<TenantTeamUser[]>([]);
  const [teamForm, setTeamForm] = useState(EMPTY_TEAM_FORM);
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editForm, setEditForm] = useState(EMPTY_TEAM_FORM);
  const [openRouter, setOpenRouter] = useState<AiProviderConfig | null>(null);
  const [apiKey, setApiKey] = useState('');
  const tenantsQuery = useQuery({
    queryKey: ['admin', 'tenants', keyword],
    queryFn: async () => (await adminApi.tenants.list({ keyword: keyword || undefined })).data,
  });
  const warmupRulesQuery = useQuery({
    queryKey: ['admin', 'warmup-rules'],
    queryFn: async () => (await adminApi.warmupRules.get()).data,
  });

  const activeWarmupLevels = useMemo(() => warmupRules?.levels ?? [], [warmupRules]);
  const tenantAdminUrl = getTenantAdminUrl(selected);

  const load = async () => {
    await tenantsQuery.refetch();
  };

  const loadDetail = async (tenant: Tenant) => {
    setSelected(tenant);
    setTenantEditForm(toEditForm(tenant));
    setDrawerOpen(true);
    try {
      const [detailResponse, domainsResponse, teamResponse, openRouterResponse] = await Promise.all([
        adminApi.tenants.detail(tenant.id),
        adminApi.tenants.listDomains(tenant.id),
        adminApi.tenants.listTeam(tenant.id),
        adminApi.tenants.getOpenRouter(tenant.id).catch(() => null),
      ]);
      const detail = detailResponse.data.data;
      setSelected(detail);
      setTenantEditForm(toEditForm(detail));
      setDomains(domainsResponse.data.data);
      setTeam(teamResponse.data.data);
      setOpenRouter(openRouterResponse?.data.data ?? null);
    } catch {
      toast.error('加载用户详情失败');
    }
  };

  useEffect(() => {
    if (tenantsQuery.isError) {
      toast.error('加载用户失败');
      return;
    }

    setItems(tenantsQuery.data?.data ?? []);
  }, [tenantsQuery.data, tenantsQuery.isError]);

  useEffect(() => {
    if (warmupRulesQuery.isError) {
      toast.error('加载预热档位失败');
      return;
    }

    const active = warmupRulesQuery.data?.data.find((rule) => rule.is_active) ?? warmupRulesQuery.data?.data[0] ?? null;
    setWarmupRules(active);
    setDomainWarmupRuleId(active?.id ?? '');
    setDomainWarmupLevel(active?.levels[0]?.level ? String(active.levels[0].level) : '');
  }, [warmupRulesQuery.data, warmupRulesQuery.isError]);

  const createTenant = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    try {
      const payload: TenantCreatePayload = {
        name: tenantForm.name,
        industry: tenantForm.industry,
        contact_name: tenantForm.contact_name || undefined,
        contact_phone: tenantForm.contact_phone || undefined,
        contact_email: tenantForm.contact_email || undefined,
        admin_email: tenantForm.admin_email,
        admin_name: tenantForm.admin_name,
        admin_password: tenantForm.admin_password,
      };
      await adminApi.tenants.create(payload);
      setCreateOpen(false);
      setTenantForm(EMPTY_TENANT);
      toast.success('用户已创建');
      await load();
    } catch {
      toast.error('创建用户失败');
    }
  };

  const updateTenant = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    try {
      const response = await adminApi.tenants.update(selected.id, {
        name: tenantEditForm.name,
        industry: tenantEditForm.industry,
        contact_name: tenantEditForm.contact_name || undefined,
        contact_phone: tenantEditForm.contact_phone || undefined,
        contact_email: tenantEditForm.contact_email || undefined,
      });
      const updated = response.data.data;
      setSelected(updated);
      setTenantEditForm(toEditForm(updated));
      setItems((current) => current.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)));
      toast.success('用户信息已保存');
    } catch {
      toast.error('保存用户信息失败');
    }
  };

  const copyTenantAdminUrl = async () => {
    if (!tenantAdminUrl) return;
    try {
      await navigator.clipboard.writeText(tenantAdminUrl);
      toast.success('后台管理地址已复制');
    } catch {
      toast.error('复制失败，请手动复制');
    }
  };

  const changeStatus = async (tenant: Tenant, action: 'suspend' | 'activate') => {
    try {
      if (action === 'suspend') {
        await adminApi.tenants.suspend(tenant.id);
        toast.success('用户已暂停');
      } else {
        await adminApi.tenants.activate(tenant.id);
        toast.success('用户已启用');
      }
      await load();
      if (selected?.id === tenant.id) {
        await loadDetail({ ...tenant, status: action === 'suspend' ? 'suspended' : 'active' });
      }
    } catch {
      toast.error('更新用户状态失败');
    }
  };

  const deleteTenant = async (tenant: Tenant) => {
    try {
      await adminApi.tenants.delete(tenant.id);
      toast.success('用户已删除');
      if (selected?.id === tenant.id) setDrawerOpen(false);
      await load();
    } catch {
      toast.error('删除用户失败');
    }
  };

  const createDomain = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected || !domainText.trim() || !domainWarmupRuleId || !domainWarmupLevel) return;
    try {
      await adminApi.tenants.createDomain(selected.id, {
        domain: domainText.trim(),
        warmup_rule_id: domainWarmupRuleId,
        warmup_level: Number(domainWarmupLevel),
        sender_email: domainSenderEmail.trim() || undefined,
      });
      setDomainText('');
      setDomainSenderEmail('');
      toast.success('域名已添加');
      await loadDetail(selected);
    } catch {
      toast.error('添加域名失败');
    }
  };

  const verifyDomain = async (domain: TenantDomain) => {
    if (!selected) return;
    try {
      await adminApi.tenants.verifyDomain(selected.id, domain.id);
      toast.success('已触发验证域名');
      await loadDetail(selected);
    } catch {
      toast.error('验证域名失败');
    }
  };

  const startEditDomain = (domain: TenantDomain) => {
    setEditingDomain(domain);
    setEditDomainForm({
      sender_email: domain.sender_email ?? '',
      warmup_rule_id: domain.warmup_rule_id ?? '',
      warmup_level: String(domain.warmup_level ?? ''),
    });
  };

  const saveEditDomain = async () => {
    if (!selected || !editingDomain) return;
    setEditDomainLoading(true);
    try {
      await adminApi.tenants.updateDomain(selected.id, editingDomain.id, {
        sender_email: editDomainForm.sender_email || null,
        warmup_rule_id: editDomainForm.warmup_rule_id || undefined,
        warmup_level: editDomainForm.warmup_level ? Number(editDomainForm.warmup_level) : undefined,
      });
      toast.success('域名配置已更新');
      setEditingDomain(null);
      await loadDetail(selected);
    } catch {
      toast.error('更新域名失败');
    } finally {
      setEditDomainLoading(false);
    }
  };

  const confirmDeleteDomain = async () => {
    if (!selected || !deletingDomain) return;
    setDeleteDomainLoading(true);
    setDeleteDomainError('');
    try {
      await adminApi.tenants.deleteDomain(selected.id, deletingDomain.id);
      toast.success('域名已删除');
      setDeletingDomain(null);
      await loadDetail(selected);
    } catch (error: unknown) {
      const axiosError = error as { response?: { status?: number } };
      if (axiosError.response?.status === 409) {
        setDeleteDomainError('该域名存在关联数据，无法删除');
      } else {
        toast.error('删除域名失败');
      }
    } finally {
      setDeleteDomainLoading(false);
    }
  };

  const startEditTeamUser = (user: TenantTeamUser) => {
    setEditingUserId(user.id);
    setEditForm({
      email: user.email,
      name: user.name,
      roles: user.roles[0] ?? 'viewer',
      status: user.status,
      password: '',
    });
  };

  const cancelEditTeamUser = () => {
    setEditingUserId(null);
  };

  const addTeamUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    try {
      await adminApi.tenants.createTeamUser(selected.id, {
        email: teamForm.email,
        name: teamForm.name,
        roles: [teamForm.roles],
        status: 'active',
        password: teamForm.password || undefined,
        must_change_pwd: Boolean(teamForm.password),
      } as Partial<TenantTeamUser>);
      toast.success('团队成员已创建');
      setTeamForm(EMPTY_TEAM_FORM);
      await loadDetail(selected);
    } catch {
      toast.error('创建团队成员失败');
    }
  };

  const updateTeamUser = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected || !editingUserId) return;
    try {
      await adminApi.tenants.updateTeamUser(selected.id, editingUserId, {
        email: editForm.email,
        name: editForm.name,
        roles: [editForm.roles],
        status: editForm.status,
        password: editForm.password || undefined,
        must_change_pwd: Boolean(editForm.password),
      } as Partial<TenantTeamUser>);
      toast.success('团队成员已更新');
      cancelEditTeamUser();
      await loadDetail(selected);
    } catch {
      toast.error('更新团队成员失败');
    }
  };

  const deleteTeamUser = async (user: TenantTeamUser) => {
    if (!selected) return;
    try {
      await adminApi.tenants.deleteTeamUser(selected.id, user.id);
      toast.success('团队成员已删除');
      await loadDetail(selected);
    } catch {
      toast.error('删除团队成员失败');
    }
  };

  const updateOpenRouter = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!selected) return;
    try {
      const response = await adminApi.tenants.updateOpenRouter(selected.id, { api_key: apiKey });
      setOpenRouter(response.data.data);
      setApiKey('');
      toast.success('OpenRouter 配置已保存');
    } catch {
      toast.error('保存 OpenRouter 配置失败');
    }
  };

  const refreshBalance = async () => {
    if (!selected) return;
    try {
      const response = await adminApi.tenants.refreshOpenRouterBalance(selected.id);
      setOpenRouter(response.data.data);
      toast.success('OpenRouter 余额已刷新');
    } catch {
      toast.error('刷新余额失败');
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">用户管理</h1>
          <p className="admin-page-description">管理用户基础信息、后台入口、发件域名、团队和 OpenRouter 配置。</p>
        </div>
        <Button onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          创建用户
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="grid gap-3 lg:grid-cols-[minmax(280px,520px)_auto_1fr] lg:items-end">
            <div className="space-y-2">
              <Label htmlFor="tenant-search">搜索</Label>
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  id="tenant-search"
                  className="pl-9"
                  placeholder="输入用户名称、联系人或行业"
                  value={keyword}
                  onChange={(event) => setKeyword(event.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === 'Enter') void load();
                  }}
                />
              </div>
            </div>
            <Button variant="outline" onClick={() => void load()}>查询</Button>
            <div className="text-sm text-muted-foreground lg:text-right">共 {items.length} 个用户</div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto" aria-label="用户列表，可横向滚动查看更多列">
            <table className="w-full min-w-[1100px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  {['用户', '后台管理地址', '行业', '联系人', '状态', '创建时间', '操作'].map((label) => (
                    <th key={label} className="px-4 py-3 font-medium">{label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {items.map((tenant) => (
                  <tr key={tenant.id} className="border-b last:border-0 hover:bg-muted/30">
                    <td className="px-4 py-3">
                      <div className="font-medium">{tenant.name}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{tenant.slug}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{getTenantAdminUrl(tenant)}</td>
                    <td className="px-4 py-3">{tenant.industry ?? '-'}</td>
                    <td className="px-4 py-3">
                      <div>{tenant.contact_name ?? '-'}</div>
                      <div className="mt-1 text-xs text-muted-foreground">{tenant.contact_email ?? tenant.contact_phone ?? '-'}</div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={tenant.status === 'active' ? 'secondary' : 'outline'}>{statusLabel(tenant.status)}</Badge>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDateTime(tenant.created_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Button size="sm" variant="outline" onClick={() => void loadDetail(tenant)}>详情</Button>
                        {tenant.status === 'active' ? (
                          <Button size="sm" variant="outline" onClick={() => void changeStatus(tenant, 'suspend')}>暂停</Button>
                        ) : (
                          <Button size="sm" variant="outline" onClick={() => void changeStatus(tenant, 'activate')}>启用</Button>
                        )}
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="ghost" size="icon" aria-label="删除用户"><Trash2 className="h-4 w-4 text-destructive" /></Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogTitle>确认删除用户？</AlertDialogTitle>
                            <AlertDialogDescription>删除动作不可恢复。</AlertDialogDescription>
                            <div className="flex justify-end gap-2">
                              <AlertDialogCancel>取消</AlertDialogCancel>
                              <AlertDialogAction onClick={() => void deleteTenant(tenant)}>删除</AlertDialogAction>
                            </div>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </td>
                  </tr>
                ))}
                {items.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-10 text-center text-muted-foreground">暂无用户</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent className="sm:max-w-2xl">
          <DialogTitle>创建用户</DialogTitle>
          <DialogDescription>只填写开户必需信息。Slug、发件域名和预热档位在系统或详情页处理。</DialogDescription>
          <form className="space-y-4" onSubmit={createTenant}>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>名称</Label>
                <Input value={tenantForm.name} onChange={(event) => setTenantForm((current) => ({ ...current, name: event.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>行业</Label>
                <Input value={tenantForm.industry} onChange={(event) => setTenantForm((current) => ({ ...current, industry: event.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>联系人</Label>
                <Input value={tenantForm.contact_name} onChange={(event) => setTenantForm((current) => ({ ...current, contact_name: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>电话</Label>
                <Input value={tenantForm.contact_phone} onChange={(event) => setTenantForm((current) => ({ ...current, contact_phone: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>邮箱</Label>
                <Input type="email" value={tenantForm.contact_email} onChange={(event) => setTenantForm((current) => ({ ...current, contact_email: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>管理员邮箱</Label>
                <Input type="email" value={tenantForm.admin_email} onChange={(event) => setTenantForm((current) => ({ ...current, admin_email: event.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>管理员姓名</Label>
                <Input value={tenantForm.admin_name} onChange={(event) => setTenantForm((current) => ({ ...current, admin_name: event.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>管理员密码</Label>
                <Input type="password" value={tenantForm.admin_password} onChange={(event) => setTenantForm((current) => ({ ...current, admin_password: event.target.value }))} required />
              </div>
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setCreateOpen(false)}>取消</Button>
              <Button type="submit">创建</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="w-full overflow-y-auto p-0 sm:max-w-6xl">
          <div className="border-b px-6 py-5 pr-12">
            <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
              <div>
                <SheetTitle>{selected?.name ?? '用户详情'}</SheetTitle>
                <SheetDescription className="mt-1">编辑基础资料，维护发件域名、团队成员和 OpenRouter。</SheetDescription>
              </div>
              {selected && <Badge variant={selected.status === 'active' ? 'secondary' : 'outline'}>{statusLabel(selected.status)}</Badge>}
            </div>
          </div>

          <Tabs defaultValue="base" className="p-6">
            <TabsList className="grid h-auto w-full grid-cols-2 lg:w-[520px] lg:grid-cols-4">
              <TabsTrigger value="base">基础信息</TabsTrigger>
              <TabsTrigger value="domains">域名</TabsTrigger>
              <TabsTrigger value="team">团队</TabsTrigger>
              <TabsTrigger value="openrouter">OpenRouter</TabsTrigger>
            </TabsList>

            <TabsContent value="base" className="mt-5 space-y-5">
              <div className="rounded-md border bg-card p-4">
                <div className="mb-3 text-sm font-medium">后台管理地址</div>
                <div className="grid gap-2 lg:grid-cols-[1fr_auto]">
                  <Input readOnly value={tenantAdminUrl} />
                  <Button type="button" variant="outline" onClick={() => void copyTenantAdminUrl()} disabled={!tenantAdminUrl}>
                    <Copy className="h-4 w-4" />
                    复制
                  </Button>
                </div>
              </div>

              <form className="space-y-4 rounded-md border bg-card p-4" onSubmit={updateTenant}>
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">基础信息</div>
                    <div className="mt-1 text-xs text-muted-foreground">Slug 由系统生成，不支持手动编辑。</div>
                  </div>
                  <Button type="submit">保存</Button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>名称</Label>
                    <Input value={tenantEditForm.name} onChange={(event) => setTenantEditForm((current) => ({ ...current, name: event.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>Slug</Label>
                    <Input readOnly value={selected?.slug ?? ''} />
                  </div>
                  <div className="space-y-2">
                    <Label>行业</Label>
                    <Input value={tenantEditForm.industry} onChange={(event) => setTenantEditForm((current) => ({ ...current, industry: event.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>联系人</Label>
                    <Input value={tenantEditForm.contact_name} onChange={(event) => setTenantEditForm((current) => ({ ...current, contact_name: event.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>电话</Label>
                    <Input value={tenantEditForm.contact_phone} onChange={(event) => setTenantEditForm((current) => ({ ...current, contact_phone: event.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>邮箱</Label>
                    <Input value={tenantEditForm.contact_email} onChange={(event) => setTenantEditForm((current) => ({ ...current, contact_email: event.target.value }))} />
                  </div>
                  <div className="space-y-2">
                    <Label>创建时间</Label>
                    <Input readOnly value={formatDateTime(selected?.created_at)} />
                  </div>
                  <div className="space-y-2">
                    <Label>更新时间</Label>
                    <Input readOnly value={formatDateTime(selected?.updated_at)} />
                  </div>
                </div>
              </form>
            </TabsContent>

            <TabsContent value="domains" className="mt-5 space-y-5">
              <form className="rounded-md border bg-card p-4" onSubmit={createDomain}>
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">添加域名</div>
                    <div className="mt-1 text-xs text-muted-foreground">预热档位来自预热规则配置，不支持自定义。</div>
                  </div>
                  <Button type="submit" disabled={!domainText.trim() || !domainWarmupRuleId || !domainWarmupLevel}>添加</Button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>域名</Label>
                    <Input placeholder="example.com" value={domainText} onChange={(event) => setDomainText(event.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>发件邮箱</Label>
                    <Input placeholder="sales@example.com" value={domainSenderEmail} onChange={(event) => setDomainSenderEmail(event.target.value)} />
                  </div>
                  <div className="space-y-2">
                    <Label>预热档位</Label>
                    <Select value={domainWarmupLevel} onValueChange={setDomainWarmupLevel}>
                      <SelectTrigger>
                        <SelectValue placeholder="选择预热档位" />
                      </SelectTrigger>
                      <SelectContent>
                        {activeWarmupLevels.map((level) => (
                          <SelectItem key={level.level} value={String(level.level)}>
                            档位 {level.level} · 每日 {level.daily_limit}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              </form>

              <div className="overflow-x-auto rounded-md border bg-card" aria-label="域名列表，可横向滚动查看更多列">
                <table className="w-full min-w-[880px] text-sm">
                  <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                    <tr>
                      {['域名', '发件邮箱', '验证状态', '预热档位', '每日上限', '已发送', '操作'].map((label) => (
                        <th key={label} className="px-4 py-3 font-medium">{label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {domains.map((domain) => (
                      <tr key={domain.id} className="border-b last:border-0">
                        <td className="px-4 py-3 font-medium">{domain.domain}</td>
                        <td className="px-4 py-3 text-muted-foreground">{domain.sender_email || '—'}</td>
                        <td className="px-4 py-3">
                          <Badge variant={domain.verification_status === 'verified' ? 'secondary' : 'outline'}>
                            {domain.verification_status === 'verified' && <CheckCircle2 className="mr-1 h-3 w-3" />}
                            {verificationLabel(domain.verification_status)}
                          </Badge>
                        </td>
                        <td className="px-4 py-3">档位 {domain.warmup_level ?? '-'}</td>
                        <td className="px-4 py-3">{domain.daily_limit ?? '-'}</td>
                        <td className="px-4 py-3">{domain.total_sent ?? 0}</td>
                        <td className="px-4 py-3 text-right space-x-1">
                          <Button variant="ghost" size="sm" onClick={() => void verifyDomain(domain)}>
                            <ShieldCheck className="mr-1 h-4 w-4" />验证
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => startEditDomain(domain)}>
                            <Edit2 className="mr-1 h-4 w-4" />编辑
                          </Button>
                          <Button variant="ghost" size="sm" className="text-destructive hover:text-destructive" onClick={() => { setDeletingDomain(domain); setDeleteDomainError(''); }}>
                            <Trash2 className="mr-1 h-4 w-4" />删除
                          </Button>
                        </td>
                      </tr>
                    ))}
                    {domains.length === 0 && (
                      <tr>
                        <td colSpan={7} className="px-4 py-8 text-center text-muted-foreground">暂无域名</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {/* 编辑域名弹窗 */}
              <Dialog open={!!editingDomain} onOpenChange={(open) => { if (!open) setEditingDomain(null); }}>
                <DialogContent>
                  <DialogTitle>编辑域名</DialogTitle>
                  <DialogDescription>编辑 {editingDomain?.domain} 的配置</DialogDescription>
                  <div className="space-y-4 pt-2">
                    <div className="space-y-2">
                      <Label>发件邮箱</Label>
                      <Input
                        placeholder="sales@example.com"
                        value={editDomainForm.sender_email}
                        onChange={(e) => setEditDomainForm((f) => ({ ...f, sender_email: e.target.value }))}
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>预热规则</Label>
                      <Select
                        value={editDomainForm.warmup_rule_id}
                        onValueChange={(v) => setEditDomainForm((f) => ({ ...f, warmup_rule_id: v }))}
                      >
                        <SelectTrigger><SelectValue placeholder="选择预热规则" /></SelectTrigger>
                        <SelectContent>
                          {warmupRulesQuery.data?.data.map((rule) => (
                            <SelectItem key={rule.id!} value={rule.id!}>{rule.name}</SelectItem>
                          )) ?? <SelectItem value="" disabled>加载中...</SelectItem>}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>预热档位</Label>
                      <Select
                        value={editDomainForm.warmup_level}
                        onValueChange={(v) => setEditDomainForm((f) => ({ ...f, warmup_level: v }))}
                      >
                        <SelectTrigger><SelectValue placeholder="选择档位" /></SelectTrigger>
                        <SelectContent>
                          {activeWarmupLevels.map((level) => (
                            <SelectItem key={level.level} value={String(level.level)}>
                              档位 {level.level} · 每日 {level.daily_limit}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="flex justify-end gap-2 pt-2">
                      <Button variant="outline" onClick={() => setEditingDomain(null)}>取消</Button>
                      <Button onClick={() => void saveEditDomain()} disabled={editDomainLoading}>
                        {editDomainLoading ? '保存中...' : '保存'}
                      </Button>
                    </div>
                  </div>
                </DialogContent>
              </Dialog>

              {/* 删除域名确认弹窗 */}
              <AlertDialog open={!!deletingDomain} onOpenChange={(open) => { if (!open) { setDeletingDomain(null); setDeleteDomainError(''); } }}>
                <AlertDialogContent>
                  <AlertDialogTitle>删除域名</AlertDialogTitle>
                  <AlertDialogDescription>
                    确定要删除域名 {deletingDomain?.domain} 吗？此操作不可恢复。
                  </AlertDialogDescription>
                  {deleteDomainError && (
                    <p className="text-sm text-destructive">{deleteDomainError}</p>
                  )}
                  <div className="flex justify-end gap-2">
                    <AlertDialogCancel onClick={() => { setDeletingDomain(null); setDeleteDomainError(''); }}>取消</AlertDialogCancel>
                    <Button variant="destructive" onClick={() => void confirmDeleteDomain()} disabled={deleteDomainLoading}>
                      {deleteDomainLoading ? '删除中...' : '删除'}
                    </Button>
                  </div>
                </AlertDialogContent>
              </AlertDialog>
            </TabsContent>

            <TabsContent value="team" className="mt-5 space-y-5">
              <form className="rounded-md border bg-card p-4" onSubmit={addTeamUser}>
                <div className="mb-4 flex items-center justify-between gap-3">
                  <div>
                    <div className="text-sm font-medium">添加团队成员</div>
                    <div className="mt-1 text-xs text-muted-foreground">新成员默认启用，修改密码时会要求成员下次登录更新。</div>
                  </div>
                  <Button type="submit">添加成员</Button>
                </div>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <div className="space-y-2">
                    <Label>邮箱</Label>
                    <Input type="email" value={teamForm.email} onChange={(event) => setTeamForm((current) => ({ ...current, email: event.target.value }))} required />
                  </div>
                  <div className="space-y-2">
                    <Label>姓名</Label>
                    <Input value={teamForm.name} onChange={(event) => setTeamForm((current) => ({ ...current, name: event.target.value }))} required />
                  </div>
                  <div className="space-y-2">
                    <Label>角色</Label>
                    <Select value={teamForm.roles} onValueChange={(value) => setTeamForm((current) => ({ ...current, roles: value }))}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="admin">管理员</SelectItem>
                        <SelectItem value="operator">运营</SelectItem>
                        <SelectItem value="viewer">查看者</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>初始密码</Label>
                    <Input
                      type="password"
                      placeholder="默认可填写临时密码"
                      value={teamForm.password}
                      onChange={(event) => setTeamForm((current) => ({ ...current, password: event.target.value }))}
                    />
                  </div>
                </div>
              </form>

              <div className="overflow-x-auto rounded-md border bg-card" aria-label="团队成员列表，可横向滚动查看更多列">
                <table className="w-full min-w-[760px] text-sm">
                  <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                    <tr>
                      {['成员', '角色', '状态', '创建时间', '操作'].map((label) => (
                        <th key={label} className="px-4 py-3 font-medium">{label}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {team.map((user) => (
                      <tr key={user.id} className="border-b last:border-0">
                        <td className="px-4 py-3">
                          <div className="font-medium">{user.name}</div>
                          <div className="mt-1 text-xs text-muted-foreground">{user.email}</div>
                        </td>
                        <td className="px-4 py-3">{user.roles.map(roleLabel).join(', ')}</td>
                        <td className="px-4 py-3">{userStatusLabel(user.status)}</td>
                        <td className="px-4 py-3 text-muted-foreground">{formatDateTime(user.created_at)}</td>
                        <td className="px-4 py-3">
                          <div className="flex justify-end gap-1">
                            <Button variant="ghost" size="icon" aria-label="编辑成员" onClick={() => startEditTeamUser(user)}>
                              <Edit2 className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" aria-label="删除成员" onClick={() => void deleteTeamUser(user)}>
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </div>
                        </td>
                      </tr>
                    ))}
                    {team.length === 0 && (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">暂无团队成员</td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              <Dialog open={editingUserId !== null} onOpenChange={(open) => { if (!open) cancelEditTeamUser(); }}>
                <DialogContent>
                  <DialogTitle>编辑团队成员</DialogTitle>
                  <DialogDescription>修改成员信息。留空密码则不修改。</DialogDescription>
                  <form className="space-y-4" onSubmit={updateTeamUser}>
                    <div className="grid gap-3 sm:grid-cols-2">
                      <div className="space-y-2">
                        <Label>邮箱</Label>
                        <Input type="email" value={editForm.email} onChange={(event) => setEditForm((current) => ({ ...current, email: event.target.value }))} required />
                      </div>
                      <div className="space-y-2">
                        <Label>姓名</Label>
                        <Input value={editForm.name} onChange={(event) => setEditForm((current) => ({ ...current, name: event.target.value }))} required />
                      </div>
                      <div className="space-y-2">
                        <Label>角色</Label>
                        <Select value={editForm.roles} onValueChange={(value) => setEditForm((current) => ({ ...current, roles: value }))}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="admin">管理员</SelectItem>
                            <SelectItem value="operator">运营</SelectItem>
                            <SelectItem value="viewer">查看者</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2">
                        <Label>状态</Label>
                        <Select value={editForm.status} onValueChange={(value) => setEditForm((current) => ({ ...current, status: value }))}>
                          <SelectTrigger><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="active">启用</SelectItem>
                            <SelectItem value="disabled">停用</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-2 sm:col-span-2">
                        <Label>重置密码</Label>
                        <Input type="password" placeholder="不填写则不修改" value={editForm.password} onChange={(event) => setEditForm((current) => ({ ...current, password: event.target.value }))} />
                      </div>
                    </div>
                    <div className="flex justify-end gap-2">
                      <Button type="button" variant="outline" onClick={cancelEditTeamUser}>取消</Button>
                      <Button type="submit">保存</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </TabsContent>

            <TabsContent value="openrouter" className="mt-5 space-y-5">
              <div className="grid gap-3 sm:grid-cols-3">
                <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">配置状态</div><div className="mt-1 font-semibold">{openRouter?.is_configured ? '已配置' : '未配置'}</div></CardContent></Card>
                <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">余额状态</div><div className="mt-1 font-semibold">{balanceStatusLabel(openRouter?.balance.status)}</div></CardContent></Card>
                <Card><CardContent className="p-4"><div className="text-xs text-muted-foreground">余额</div><div className="mt-1 font-semibold">{openRouter?.balance.amount ?? '-'} {openRouter?.balance.currency ?? ''}</div></CardContent></Card>
              </div>
              <form className="grid gap-2 rounded-md border bg-card p-4 lg:grid-cols-[1fr_auto_auto]" onSubmit={updateOpenRouter}>
                <Input type="password" placeholder={openRouter?.secret_masked ?? 'OpenRouter API Key'} value={apiKey} onChange={(event) => setApiKey(event.target.value)} />
                <Button type="submit">保存</Button>
                <Button type="button" variant="outline" onClick={() => void refreshBalance()}>
                  <RefreshCw className="h-4 w-4" />
                  刷新余额
                </Button>
              </form>
            </TabsContent>
          </Tabs>
        </SheetContent>
      </Sheet>
    </div>
  );
}
