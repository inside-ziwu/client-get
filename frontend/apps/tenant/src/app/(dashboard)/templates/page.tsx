'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Copy, Edit2, Eye, Plus, Sparkles, Trash2 } from 'lucide-react';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
  Textarea,
} from '@shared/ui';
import { GrapesEmailEditor, type GrapesEmailEditorHandle } from '@shared/ui';
import type { EmailTemplate, PlatformTemplateListItem } from '@shared/api/src/tenant/email-templates';
import { tenantApi } from '@/lib/api';
import { DataTable, PageHeader } from '@/components/pages/page-kit';

const CATEGORIES = [
  { value: 'cold_outreach', label: '开发信' },
  { value: 'follow_up', label: '跟进' },
  { value: 'promotion', label: '推广' },
  { value: 'festival', label: '节日' },
];

const VARIABLES = [
  { name: 'company_name', label: '公司名称' },
  { name: 'contact_name', label: '联系人姓名' },
  { name: 'contact_email', label: '联系人邮箱' },
  { name: 'product_name', label: '产品名称' },
  { name: 'sender_name', label: '发件人姓名' },
];

type TemplateForm = {
  name: string;
  category: string;
  subject: string;
  body_html: string;
  body_text: string;
  body_design: unknown;
};

const EMPTY_FORM: TemplateForm = {
  name: '',
  category: 'cold_outreach',
  subject: '',
  body_html: '<p>你好 {{contact_name}}，</p>',
  body_text: '',
  body_design: null,
};

export default function TemplatesPage() {
  const queryClient = useQueryClient();
  const editorRef = useRef<GrapesEmailEditorHandle | null>(null);
  const [activeTab, setActiveTab] = useState('my-templates');

  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<TemplateForm>(EMPTY_FORM);
  const [editorMode, setEditorMode] = useState<'visual' | 'html' | 'text'>('html');
  const [saving, setSaving] = useState(false);

  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewHtml, setPreviewHtml] = useState('');
  const [previewSubject, setPreviewSubject] = useState('');

  const [aiOpen, setAiOpen] = useState(false);
  const [aiForm, setAiForm] = useState({ name: '', category: 'cold_outreach', company_name: '', prompt: '', subject: '' });
  const [aiLoading, setAiLoading] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<EmailTemplate | null>(null);

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

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => tenantApi.emailTemplates.delete(id),
    onSuccess: async () => {
      toast.success('模板已删除');
      setDeleteTarget(null);
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'templates'] });
    },
    onError: () => toast.error('删除失败'),
  });

  const openCreate = () => {
    setEditingId(null);
    setForm(EMPTY_FORM);
    setEditorMode('html');
    setDrawerOpen(true);
  };

  const openEdit = async (template: EmailTemplate) => {
    try {
      const resp = await tenantApi.emailTemplates.detail(template.id);
      const detail = resp.data.data;
      setEditingId(detail.id);
      setForm({
        name: detail.name,
        category: detail.category ?? 'cold_outreach',
        subject: detail.subject,
        body_html: detail.body_html ?? '',
        body_text: detail.body_text ?? '',
        body_design: detail.body_design ?? null,
      });
      setEditorMode(detail.body_design ? 'visual' : 'html');
      setDrawerOpen(true);
    } catch {
      toast.error('加载模板详情失败');
    }
  };

  const handleEditorModeChange = (newMode: string) => {
    if (editorMode === 'visual' && editorRef.current) {
      setForm((prev) => ({
        ...prev,
        body_html: editorRef.current?.getHtml() ?? prev.body_html,
        body_design: editorRef.current?.getDesign() ?? prev.body_design,
      }));
    }
    setEditorMode(newMode as 'visual' | 'html' | 'text');
  };

  const saveTemplate = async (e: FormEvent) => {
    e.preventDefault();
    if (!form.name.trim() || !form.subject.trim()) {
      toast.error('请输入模板名称和主题');
      return;
    }
    setSaving(true);
    try {
      const body_html = editorMode === 'visual' ? (editorRef.current?.getHtml() ?? form.body_html) : form.body_html;
      const body_design = editorMode === 'visual' ? (editorRef.current?.getDesign() ?? null) : null;
      const payload = {
        name: form.name.trim(),
        category: form.category,
        subject: form.subject.trim(),
        body_html,
        body_text: editorMode === 'text' ? form.body_text : undefined,
        body_design,
        variables: VARIABLES.filter((v) => body_html.includes(`{{${v.name}}}`)),
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
        category: aiForm.category,
        company_name: aiForm.company_name,
        prompt: aiForm.prompt,
        subject: aiForm.subject || undefined,
      });
      const generated = resp.data.data;
      setAiOpen(false);
      setEditingId(null);
      setForm({
        name: generated.name ?? aiForm.name ?? '',
        category: generated.category ?? aiForm.category,
        subject: generated.subject ?? '',
        body_html: generated.body_html ?? '',
        body_text: '',
        body_design: null,
      });
      setEditorMode('html');
      setDrawerOpen(true);
      toast.success('AI 已生成模板，请检查并保存');
    } catch {
      toast.error('AI 生成失败');
    } finally {
      setAiLoading(false);
    }
  };

  const copyVariable = (name: string) => {
    void navigator.clipboard.writeText(`{{${name}}}`);
    toast.success(`已复制 {{${name}}}`);
  };

  return (
    <div className="tenant-page">
      <PageHeader
        title="邮件模板"
        description="浏览平台模板库或管理自有邮件模板"
        action={
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => setAiOpen(true)}>
              <Sparkles className="mr-1 h-4 w-4" />
              AI 生成
            </Button>
            <Button onClick={openCreate}>
              <Plus className="mr-1 h-4 w-4" />
              新建模板
            </Button>
          </div>
        }
      />

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="platform">平台模板库</TabsTrigger>
          <TabsTrigger value="my-templates">我的模板</TabsTrigger>
        </TabsList>

        <TabsContent value="platform" className="mt-4">
          <DataTable<PlatformTemplateListItem>
            rows={platformQuery.data}
            emptyText="暂无平台模板"
            columns={[
              { key: 'name', title: '名称', render: (row) => <span className="font-medium">{row.name}</span> },
              { key: 'category', title: '分类', render: (row) => <Badge variant="outline">{row.category ?? '-'}</Badge> },
              { key: 'subject', title: '主题', render: (row) => <span className="max-w-[260px] truncate">{row.subject}</span> },
              {
                key: 'updated',
                title: '更新时间',
                render: (row) => <span className="text-muted-foreground">{row.updated_at?.slice(0, 10) ?? '-'}</span>,
              },
              {
                key: 'actions',
                title: '操作',
                render: (row) => (
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" aria-label="预览" onClick={() => void openPlatformPreview(row.id)}>
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="复制到我的模板"
                      disabled={copyMutation.isPending}
                      onClick={() => copyMutation.mutate(row.id)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                ),
              },
            ]}
          />
        </TabsContent>

        <TabsContent value="my-templates" className="mt-4">
          <DataTable<EmailTemplate>
            rows={templatesQuery.data}
            emptyText="暂无模板，从平台模板库复制或新建一个"
            columns={[
              { key: 'name', title: '名称', render: (row) => <span className="font-medium">{row.name}</span> },
              { key: 'category', title: '分类', render: (row) => <Badge variant="outline">{row.category ?? '-'}</Badge> },
              { key: 'subject', title: '主题', render: (row) => <span className="max-w-[260px] truncate">{row.subject}</span> },
              {
                key: 'source',
                title: '来源',
                render: (row) =>
                  row.source_type === 'platform_copy' ? (
                    <Badge variant="secondary">平台</Badge>
                  ) : (
                    <Badge variant="outline">自建</Badge>
                  ),
              },
              {
                key: 'updated',
                title: '更新时间',
                render: (row) => <span className="text-muted-foreground">{row.updated_at?.slice(0, 10) ?? '-'}</span>,
              },
              {
                key: 'actions',
                title: '操作',
                render: (row) => (
                  <div className="flex gap-1">
                    <Button variant="ghost" size="icon" aria-label="预览" onClick={() => void openPreview(row.id)}>
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" aria-label="编辑" onClick={() => void openEdit(row)}>
                      <Edit2 className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      aria-label="克隆"
                      disabled={cloneMutation.isPending}
                      onClick={() => cloneMutation.mutate(row.id)}
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                    <Button variant="ghost" size="icon" aria-label="删除" onClick={() => setDeleteTarget(row)}>
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                ),
              },
            ]}
          />
        </TabsContent>
      </Tabs>

      {/* Drawer 编辑器 */}
      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="max-w-4xl overflow-y-auto p-0 sm:w-[760px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{editingId ? '编辑邮件模板' : '新建邮件模板'}</SheetTitle>
            <SheetDescription>填写模板信息并选择编辑模式</SheetDescription>
          </div>
          <form className="space-y-5 p-5" onSubmit={saveTemplate}>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="space-y-2">
                <Label>模板名称</Label>
                <Input value={form.name} onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))} required />
              </div>
              <div className="space-y-2">
                <Label>分类</Label>
                <Select value={form.category} onValueChange={(v) => setForm((p) => ({ ...p, category: v }))}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {CATEGORIES.map((c) => (
                      <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-2">
              <Label>邮件主题</Label>
              <Input value={form.subject} onChange={(e) => setForm((p) => ({ ...p, subject: e.target.value }))} required />
            </div>
            <div className="space-y-2">
              <Label>变量（点击复制）</Label>
              <div className="flex flex-wrap gap-1">
                {VARIABLES.map((v) => (
                  <Badge key={v.name} variant="outline" className="cursor-pointer" onClick={() => copyVariable(v.name)}>
                    {`{{${v.name}}}`} {v.label}
                  </Badge>
                ))}
              </div>
            </div>
            <Tabs value={editorMode} onValueChange={handleEditorModeChange}>
              <TabsList>
                <TabsTrigger value="visual">可视化</TabsTrigger>
                <TabsTrigger value="html">HTML</TabsTrigger>
                <TabsTrigger value="text">纯文本</TabsTrigger>
              </TabsList>
              <TabsContent value="visual">
                <GrapesEmailEditor ref={editorRef} html={form.body_html} design={form.body_design} />
              </TabsContent>
              <TabsContent value="html">
                <Textarea
                  className="min-h-[400px] font-mono text-xs"
                  value={form.body_html}
                  onChange={(e) => setForm((p) => ({ ...p, body_html: e.target.value }))}
                />
              </TabsContent>
              <TabsContent value="text">
                <Textarea
                  className="min-h-[400px] font-mono text-xs"
                  value={form.body_text}
                  onChange={(e) => setForm((p) => ({ ...p, body_text: e.target.value }))}
                />
              </TabsContent>
            </Tabs>
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
              <Label>分类</Label>
              <Select value={aiForm.category} onValueChange={(v) => setAiForm((p) => ({ ...p, category: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map((c) => (
                    <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
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

      {/* 删除确认 */}
      <AlertDialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialogContent>
          <AlertDialogTitle>确认删除模板？</AlertDialogTitle>
          <AlertDialogDescription>删除后无法恢复，确认要删除「{deleteTarget?.name}」吗？</AlertDialogDescription>
          <div className="flex justify-end gap-2">
            <AlertDialogCancel>取消</AlertDialogCancel>
            <AlertDialogAction onClick={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}>删除</AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
