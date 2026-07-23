'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Sparkles } from 'lucide-react';
import { type FormEvent, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  Badge,
  Button,
  CreateButton,
  DataTable,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  Input,
  Label,
  ListPage,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
  type DataTableColumn,
} from '@shared/ui';
import { EmailRichEditor, type EmailRichEditorHandle } from '@shared/ui';
import type { EmailTemplate, PlatformTemplateListItem } from '@shared/api';
import { tenantApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

// 与后端 TenantMessagingService.KNOWN_TEMPLATE_VARIABLES 对齐：发送渲染只替换这四个
const VARIABLES = [
  { name: 'company_name', label: '公司名称' },
  { name: 'contact_name', label: '联系人姓名' },
  { name: 'contact_email', label: '联系人邮箱' },
  { name: 'sender_name', label: '发件人姓名' },
];

type TemplateForm = {
  name: string;
  subject: string;
  body_html: string;
  body_text: string;
};

const EMPTY_FORM: TemplateForm = {
  name: '',
  subject: '',
  body_html: '<p>你好 {{contact_name}}，</p>',
  body_text: '',
};

export default function TemplatesPage() {
  const queryClient = useQueryClient();
  const editorRef = useRef<EmailRichEditorHandle | null>(null);
  const [activeTab, setActiveTab] = useState('my-templates');

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<TemplateForm>(EMPTY_FORM);
  const [editorKey, setEditorKey] = useState(0);
  const [bodyHtml, setBodyHtml] = useState('');
  const [bodyText, setBodyText] = useState('');
  const [saving, setSaving] = useState(false);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewSubject, setPreviewSubject] = useState('');

  const [aiOpen, setAiOpen] = useState(false);
  const [aiForm, setAiForm] = useState({ name: '', company_name: '', prompt: '', subject: '' });
  const [aiLoading, setAiLoading] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<EmailTemplate | null>(null);

  const [testEmailDialogOpen, setTestEmailDialogOpen] = useState(false);
  const [testEmailInput, setTestEmailInput] = useState('');
  const [testEmailError, setTestEmailError] = useState('');
  const [pendingTestSendId, setPendingTestSendId] = useState<string | null>(null);

  const platformQuery = useQuery({
    queryKey: ['tenant', 'platform-templates'],
    queryFn: async () => (await tenantApi.emailTemplates.platformTemplates.list()).data.data,
  });

  const templatesQuery = useQuery({
    queryKey: ['tenant', 'templates'],
    queryFn: async () => (await tenantApi.emailTemplates.list()).data.data,
  });

  const copyMutation = useMutation({
    mutationFn: async (templateId: string) =>
      (await tenantApi.emailTemplates.platformTemplates.copy(templateId)).data.data,
    onSuccess: async () => {
      toast.success('模板已复制到我的模板');
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'templates'] });
      setActiveTab('my-templates');
    },
    onError: () => toast.error('复制失败'),
  });

  const cloneMutation = useMutation({
    mutationFn: async (id: string) => (await tenantApi.emailTemplates.clone(id)).data.data,
    onSuccess: async () => {
      toast.success('模板已克隆');
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'templates'] });
    },
    onError: () => toast.error('克隆失败'),
  });

  const testSendMutation = useMutation({
    mutationFn: async (templateId: string) => (await tenantApi.emailTemplates.testSend(templateId)).data.data,
    onSuccess: (data) => {
      toast.success(`测试邮件已发送到 ${data.test_email}`);
    },
    onError: (err: any) => {
      const code = err?.response?.data?.error?.code;
      if (code === 'TEST_EMAIL_NOT_SET') {
        setPendingTestSendId(testSendMutation.variables ?? null);
        setTestEmailInput('');
        setTestEmailError('');
        setTestEmailDialogOpen(true);
      } else {
        toast.error(err?.response?.data?.error?.message ?? '发送测试失败');
      }
    },
  });

  const updateTestEmailMutation = useMutation({
    mutationFn: async (email: string) => (await tenantApi.auth.updateTestEmail(email)).data.data,
    onSuccess: () => {
      setTestEmailDialogOpen(false);
      if (pendingTestSendId) {
        testSendMutation.mutate(pendingTestSendId);
        setPendingTestSendId(null);
      }
    },
    onError: () => toast.error('保存测试邮箱失败'),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => tenantApi.emailTemplates.delete(id),
    onSuccess: async () => {
      toast.success('模板已删除');
      setDeleteTarget(null);
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'templates'] });
    },
    onError: () => toast.error('删除失败'),
  });

  const handleSaveAndSend = () => {
    const email = testEmailInput.trim();
    if (!email || !/^.+@.+\..+$/.test(email)) {
      setTestEmailError('请输入正确的邮箱地址');
      return;
    }
    setTestEmailError('');
    updateTestEmailMutation.mutate(email);
  };

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setEditorKey((k) => k + 1);
    setDrawerOpen(true);
  };

  const openEdit = async (template: EmailTemplate) => {
    try {
      const resp = await tenantApi.emailTemplates.detail(template.id);
      const detail = resp.data.data;
      setEditingId(detail.id);
      setForm({
        name: detail.name,
        subject: detail.subject,
        body_html: detail.body_html ?? '',
        body_text: detail.body_text ?? '',
      });
      setEditorKey((k) => k + 1);
      setDrawerOpen(true);
    } catch {
      toast.error('加载模板详情失败');
    }
  };

  const saveTemplate = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.subject.trim()) {
      toast.error('请输入模板名称和主题');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        subject: form.subject.trim(),
        body_html: bodyHtml,
        body_text: bodyText,
      };

      if (editingId) {
        await tenantApi.emailTemplates.update(editingId, payload);
        toast.success('模板已更新');
      } else {
        await tenantApi.emailTemplates.create(payload);
        toast.success('模板已创建');
      }
      setDrawerOpen(false);
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'templates'] });
    } catch {
      toast.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const openPreview = async (id: string) => {
    try {
      const resp = await tenantApi.emailTemplates.preview(id);
      const data = resp.data.data;
      setPreviewSubject(data.subject);
      setPreviewHtml(data.body_html);
      setPreviewOpen(true);
    } catch {
      toast.error('加载预览失败');
    }
  };

  const openPlatformPreview = async (id: string) => {
    try {
      const resp = await tenantApi.emailTemplates.platformTemplates.copy(id);
      const data = resp.data.data;
      setPreviewSubject(data.subject);
      setPreviewHtml(data.body_html);
      setPreviewOpen(true);
    } catch {
      toast.error('暂不支持预览');
    }
  };

  const submitAiGenerate = async (e: FormEvent) => {
    e.preventDefault();
    setAiLoading(true);
    try {
      const resp = await tenantApi.emailTemplates.aiGenerate({
        name: aiForm.name || undefined,
        company_name: aiForm.company_name,
        prompt: aiForm.prompt,
        subject: aiForm.subject || undefined,
      });
      const generated = resp.data.data;
      setAiOpen(false);
      setEditingId(null);
      setForm({
        name: generated.name ?? aiForm.name ?? '',
        subject: generated.subject ?? '',
        body_html: generated.body_html ?? '',
        body_text: '',
      });
      setEditorKey((k) => k + 1);
      setDrawerOpen(true);
      toast.success('AI 已生成模板，请检查并保存');
    } catch {
      toast.error('AI 生成失败');
    } finally {
      setAiLoading(false);
    }
  };

  const handleVariableClick = (name: string) => {
    editorRef.current?.insertVariable(`{{${name}}}`);
  };

  const platformColumns: DataTableColumn<PlatformTemplateListItem>[] = [
    {
      id: 'name',
      header: '名称',
      width: 'medium',
      type: 'text',
      value: 'name',
      render: (row) => <span className="text-ui-body-strong">{row.name}</span>,
    },
    { id: 'subject', header: '主题', width: 'large', type: 'text', value: 'subject' },
    {
      id: 'updated',
      header: '更新时间',
      width: 'medium',
      align: 'center',
      type: 'date',
      value: 'updated_at',
      format: (value) => formatDateTime(value as string | undefined, 'YYYY-MM-DD'),
    },
    {
      id: 'actions',
      header: '操作',
      width: 'medium',
      align: 'center',
      type: 'actions',
      render: (row) => (
        <div className="flex items-center justify-center gap-ui-xxs">
          <Button
            variant="link"
            className="h-8 px-ui-xxs text-ui-foreground"
            onClick={() => void openPlatformPreview(row.id)}
          >
            预览
          </Button>
          <Button
            variant="link"
            className="h-8 px-ui-xxs text-ui-foreground"
            disabled={copyMutation.isPending && copyMutation.variables === row.id}
            onClick={() => copyMutation.mutate(row.id)}
          >
            复制
          </Button>
        </div>
      ),
    },
  ];

  const templateColumns: DataTableColumn<EmailTemplate>[] = [
    {
      id: 'name',
      header: '名称',
      width: 'medium',
      type: 'text',
      value: 'name',
      render: (row) => <span className="text-ui-body-strong">{row.name}</span>,
    },
    { id: 'subject', header: '主题', width: 'large', type: 'text', value: 'subject' },
    {
      id: 'source',
      header: '来源',
      width: 'small',
      align: 'center',
      type: 'text',
      value: 'source_type',
      render: (row) => row.source_type === 'platform_copy'
        ? <Badge variant="secondary">平台</Badge>
        : <Badge variant="outline">自建</Badge>,
    },
    {
      id: 'updated',
      header: '更新时间',
      width: 'medium',
      align: 'center',
      type: 'date',
      value: 'updated_at',
      format: (value) => formatDateTime(value as string | undefined, 'YYYY-MM-DD'),
    },
    {
      id: 'actions',
      header: '操作',
      width: 'large',
      align: 'center',
      type: 'actions',
      render: (row) => (
        <div className="flex items-center justify-center gap-ui-xxs">
          <Button variant="link" className="h-8 px-ui-xxs text-ui-foreground" onClick={() => void openPreview(row.id)}>预览</Button>
          <Button variant="link" className="h-8 px-ui-xxs text-ui-foreground" onClick={() => void openEdit(row)}>编辑</Button>
          <Button
            variant="link"
            className="h-8 px-ui-xxs text-ui-foreground"
            disabled={cloneMutation.isPending && cloneMutation.variables === row.id}
            onClick={() => cloneMutation.mutate(row.id)}
          >
            克隆
          </Button>
          <Button
            variant="link"
            className="h-8 px-ui-xxs text-ui-foreground"
            disabled={testSendMutation.isPending && testSendMutation.variables === row.id}
            onClick={() => testSendMutation.mutate(row.id)}
          >
            发送测试
          </Button>
          <Button
            variant="link"
            className="h-8 px-ui-xxs text-ui-foreground hover:text-ui-danger-foreground focus-visible:text-ui-danger-foreground"
            onClick={() => setDeleteTarget(row)}
          >
            删除
          </Button>
        </div>
      ),
    },
  ];

  const platformTemplates = platformQuery.data ?? [];
  const templates = templatesQuery.data ?? [];
  const platformState = platformQuery.isLoading
    ? { kind: 'loading' as const }
    : platformQuery.isError
      ? { kind: 'error' as const, description: '请检查网络后重试', onRetry: () => void platformQuery.refetch() }
      : platformTemplates.length === 0
        ? { kind: 'empty' as const }
        : undefined;
  const templatesState = templatesQuery.isLoading
    ? { kind: 'loading' as const }
    : templatesQuery.isError
      ? { kind: 'error' as const, description: '请检查网络后重试', onRetry: () => void templatesQuery.refetch() }
      : templates.length === 0
        ? { kind: 'empty' as const }
        : undefined;

  return (
    <ListPage
      className="tenant-page"
      title="邮件模板"
      description="浏览平台模板库或管理自有邮件模板"
      primaryAction={(
        <div className="flex gap-ui-sm">
          <Button variant="outline" onClick={() => setAiOpen(true)}>
            <Sparkles className="mr-1 h-4 w-4" />
            AI 生成
          </Button>
          <CreateButton onClick={openCreate}>
            新建模板
          </CreateButton>
        </div>
      )}
    >
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="platform">平台模板库</TabsTrigger>
          <TabsTrigger value="my-templates">我的模板</TabsTrigger>
        </TabsList>

        <TabsContent value="platform" className="mt-4">
          <DataTable
            columns={platformColumns}
            data={platformTemplates}
            entityName="平台模板"
            getRowId={(row) => row.id}
            isRefreshing={platformQuery.isFetching && !platformQuery.isLoading}
            state={platformState}
          />
        </TabsContent>

        <TabsContent value="my-templates" className="mt-4">
          <DataTable
            columns={templateColumns}
            data={templates}
            entityName="我的模板"
            getRowId={(row) => row.id}
            isRefreshing={templatesQuery.isFetching && !templatesQuery.isLoading}
            state={templatesState}
          />
        </TabsContent>
      </Tabs>

      {/* Drawer 编辑器 */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="max-w-4xl overflow-y-auto p-0 sm:w-[760px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{editingId ? '编辑邮件模板' : '新建邮件模板'}</SheetTitle>
            <SheetDescription>填写模板信息</SheetDescription>
          </div>
          <form className="space-y-5 p-5" onSubmit={saveTemplate}>
            <div className="space-y-2">
              <Label>模板名称</Label>
              <Input value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} required />
            </div>
            <div className="space-y-2">
              <Label>邮件主题</Label>
              <Input value={form.subject} onChange={(e) => setForm((p) => ({ ...p, subject: e.target.value }))} required />
            </div>
            <div className="space-y-2">
              <Label>变量（点击插入）</Label>
              <div className="flex flex-wrap gap-1">
                {VARIABLES.map((v) => (
                  <Badge key={v.name} variant="outline" className="cursor-pointer" onClick={() => handleVariableClick(v.name)}>
                    {`{{${v.name}}}`} {v.label}
                  </Badge>
                ))}
              </div>
            </div>
            <EmailRichEditor
              ref={editorRef}
              key={editorKey}
              initialContent={form.body_html}
              onUpdate={(html, text) => {
                setBodyHtml(html);
                setBodyText(text);
              }}
            />
            <div className="flex justify-end gap-2 border-t pt-4">
              <Button type="button" variant="outline" onClick={() => setDrawerOpen(false)}>取消</Button>
              <Button type="submit" disabled={saving}>保存</Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>

      {/* 预览 Modal */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-[860px]">
          <DialogTitle>预览</DialogTitle>
          <DialogDescription>{previewSubject || '邮件模板预览'}</DialogDescription>
          <div className="max-h-[70vh] overflow-auto rounded-md border bg-white">
            <iframe srcDoc={previewHtml} sandbox="" className="h-[60vh] w-full border-0" title="邮件预览" />
          </div>
        </DialogContent>
      </Dialog>

      {/* AI 生成 Modal */}
      <Dialog open={aiOpen} onOpenChange={setAiOpen}>
        <DialogContent className="max-w-[520px]">
          <DialogTitle>AI 生成邮件模板</DialogTitle>
          <DialogDescription>描述你的需求，AI 将自动生成邮件模板</DialogDescription>
          <form className="space-y-4" onSubmit={submitAiGenerate}>
            <div className="space-y-2">
              <Label>模板名称（可选）</Label>
              <Input value={aiForm.name} onChange={(e) => setAiForm((p) => ({ ...p, name: e.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>公司名称</Label>
              <Input
                value={aiForm.company_name}
                onChange={(e) => setAiForm((p) => ({ ...p, company_name: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>生成要求</Label>
              <Textarea
                value={aiForm.prompt}
                onChange={(e) => setAiForm((p) => ({ ...p, prompt: e.target.value }))}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>主题偏好（可选）</Label>
              <Input value={aiForm.subject} onChange={(e) => setAiForm((p) => ({ ...p, subject: e.target.value }))} />
            </div>
            <div className="flex justify-end gap-2">
              <Button type="button" variant="outline" onClick={() => setAiOpen(false)}>取消</Button>
              <Button type="submit" disabled={aiLoading}>{aiLoading ? '生成中...' : '生成'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* 测试邮箱设置弹窗 */}
      <Dialog open={testEmailDialogOpen} onOpenChange={setTestEmailDialogOpen}>
        <DialogContent className="max-w-[420px]">
          <DialogTitle>设置测试邮箱</DialogTitle>
          <DialogDescription>请输入测试邮箱地址，后续测试邮件将发送到此地址</DialogDescription>
          <div className="space-y-2">
            <Label>测试邮箱</Label>
            <Input
              placeholder="your@email.com"
              value={testEmailInput}
              onChange={(e) => { setTestEmailInput(e.target.value); setTestEmailError(''); }}
            />
            {testEmailError && <p className="text-sm text-destructive">{testEmailError}</p>}
          </div>
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setTestEmailDialogOpen(false)}>取消</Button>
            <Button onClick={handleSaveAndSend} disabled={updateTestEmailMutation.isPending}>
              {updateTestEmailMutation.isPending ? '保存中...' : '保存并发送'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* 删除确认 */}
      <AlertDialog
        open={!!deleteTarget}
        onOpenChange={(open) => {
          if (!open && !deleteMutation.isPending) setDeleteTarget(null);
        }}
      >
        <AlertDialogContent>
          <AlertDialogTitle>确认删除模板？</AlertDialogTitle>
          <AlertDialogDescription>删除后无法恢复，确认要删除「{deleteTarget?.name}」吗？</AlertDialogDescription>
          <div className="flex justify-end gap-2">
            <AlertDialogCancel disabled={deleteMutation.isPending}>取消</AlertDialogCancel>
            <AlertDialogAction
              variant="destructive"
              disabled={deleteMutation.isPending}
              onClick={(event) => {
                event.preventDefault();
                if (deleteTarget) deleteMutation.mutate(deleteTarget.id);
              }}
            >
              {deleteMutation.isPending ? '删除中…' : '删除'}
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </ListPage>
  );
}
