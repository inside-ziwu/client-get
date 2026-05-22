'use client';

import type { PlatformEmailTemplate } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Code2, Edit2, Eye, FileText, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { FormEvent, useEffect, useRef, useState } from 'react';
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
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@shared/ui';
import { Switch } from '@shared/ui';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@shared/ui';
import { Textarea } from '@shared/ui';
import { GrapesEmailEditor, type GrapesEmailEditorHandle } from '@/components/grapes-email-editor';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

type TemplateForm = {
  industry: string;
  name: string;
  subject: string;
  category: string;
  variables_text: string;
  body_html: string;
  body_design?: unknown;
  is_active: boolean;
};

const EMPTY_FORM: TemplateForm = {
  industry: '',
  name: '',
  subject: '',
  category: 'default',
  variables_text: 'company_name:公司名称\ncontact_name:联系人姓名',
  body_html: '<p>你好，{{ contact_name }}</p>',
  body_design: undefined,
  is_active: true,
};

function variablesToText(value: PlatformEmailTemplate['variables']) {
  return (value ?? []).map((item) => `${item.name}:${item.label}`).join('\n');
}

function parseVariables(text: string) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const [name, ...labelParts] = line.split(':');
      return { name: (name ?? '').trim(), label: (labelParts.join(':') || name || '').trim() };
    })
    .filter((item) => item.name);
}

function templateToForm(template: PlatformEmailTemplate): TemplateForm {
  return {
    industry: template.industry ?? '',
    name: template.name,
    subject: template.subject,
    category: template.category,
    variables_text: variablesToText(template.variables),
    body_html: template.body_html,
    body_design: template.body_design,
    is_active: template.is_active,
  };
}

export function EmailTemplatesPage() {
  const editorRef = useRef<GrapesEmailEditorHandle | null>(null);
  const [items, setItems] = useState<PlatformEmailTemplate[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [editing, setEditing] = useState<PlatformEmailTemplate | null>(null);
  const [form, setForm] = useState<TemplateForm>(EMPTY_FORM);
  const [mode, setMode] = useState<'visual' | 'html'>('html');
  const [saving, setSaving] = useState(false);
  const query = useQuery({
    queryKey: ['admin', 'email-templates'],
    queryFn: async () => (await adminApi.emailTemplates.list()).data,
  });

  const load = async () => {
    await query.refetch();
  };

  useEffect(() => {
    if (query.isError) {
      toast.error('加载邮件模板失败');
      return;
    }

    setItems(query.data?.data ?? []);
  }, [query.data, query.isError]);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setMode('html');
    setDrawerOpen(true);
  };

  const openEdit = async (template: PlatformEmailTemplate) => {
    try {
      const response = await adminApi.emailTemplates.detail(template.id);
      const detail = response.data.data;
      setEditing(detail);
      setForm(templateToForm(detail));
      setMode('html');
      setDrawerOpen(true);
    } catch {
      toast.error('加载模板详情失败');
    }
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!form.name.trim() || !form.subject.trim()) {
      toast.error('请输入模板名称和主题');
      return;
    }
    setSaving(true);
    try {
      const body_html = mode === 'visual' ? (editorRef.current?.getHtml() ?? form.body_html) : form.body_html;
      const body_design = mode === 'visual' ? editorRef.current?.getDesign() : form.body_design;
      const payload = {
        industry: form.industry.trim() || undefined,
        name: form.name.trim(),
        subject: form.subject.trim(),
        category: form.category.trim() || 'default',
        variables: parseVariables(form.variables_text),
        body_html,
        body_design,
        is_active: form.is_active,
      };

      if (editing) {
        await adminApi.emailTemplates.update(editing.id, payload);
        toast.success('邮件模板已更新');
      } else {
        await adminApi.emailTemplates.create(payload);
        toast.success('邮件模板已创建');
      }
      setDrawerOpen(false);
      await load();
    } catch {
      toast.error('保存邮件模板失败');
    } finally {
      setSaving(false);
    }
  };

  const deleteTemplate = async (template: PlatformEmailTemplate) => {
    try {
      await adminApi.emailTemplates.delete(template.id);
      toast.success('邮件模板已删除');
      await load();
    } catch {
      toast.error('删除邮件模板失败');
    }
  };

  const [syncing, setSyncing] = useState<string | null>(null);

  const syncTemplate = async (template: PlatformEmailTemplate) => {
    setSyncing(template.id);
    try {
      const response = await adminApi.emailTemplates.sync(template.id);
      const result = response.data.data;
      toast.success(`同步完成：${result.created.length} 个租户新增，${result.skipped.length} 个已跳过`);
    } catch {
      toast.error('同步邮件模板失败');
    } finally {
      setSyncing(null);
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">邮件模板管理</h1>
          <p className="admin-page-description">模板 CRUD、变量选择、HTML/可视化模式和预览。</p>
        </div>
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          新增模板
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">模板</th>
                  <th className="px-4 py-3">行业</th>
                  <th className="px-4 py-3">主题</th>
                  <th className="px-4 py-3">变量</th>
                  <th className="px-4 py-3">状态</th>
                  <th className="px-4 py-3">更新时间</th>
                  <th className="px-4 py-3 text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b last:border-0">
                    <td className="px-4 py-3 font-medium">{item.name}</td>
                    <td className="px-4 py-3">{item.industry || '-'}</td>
                    <td className="max-w-[260px] truncate px-4 py-3">{item.subject}</td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {(item.variables ?? []).slice(0, 3).map((variable) => (
                          <Badge key={variable.name} variant="outline">{`{{ ${variable.name} }}`}</Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant={item.is_active ? 'secondary' : 'outline'}>{item.is_active ? '启用' : '停用'}</Badge>
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDateTime(item.updated_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" aria-label="编辑模板" onClick={() => void openEdit(item)}>
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        {item.is_active && (
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="同步到租户"
                            disabled={syncing === item.id}
                            onClick={() => void syncTemplate(item)}
                          >
                            <RefreshCw className={`h-4 w-4${syncing === item.id ? ' animate-spin' : ''}`} />
                          </Button>
                        )}
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="ghost" size="icon" aria-label="删除模板">
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogTitle>确认删除该邮件模板？</AlertDialogTitle>
                            <AlertDialogDescription>删除后用户将无法继续选择该平台模板。</AlertDialogDescription>
                            <div className="flex justify-end gap-2">
                              <AlertDialogCancel>取消</AlertDialogCancel>
                              <AlertDialogAction onClick={() => void deleteTemplate(item)}>删除</AlertDialogAction>
                            </div>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!items.length && <div className="py-10 text-center text-sm text-muted-foreground">暂无邮件模板</div>}
          </div>
        </CardContent>
      </Card>

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="max-w-5xl overflow-y-auto p-0 sm:w-[980px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{editing ? '编辑邮件模板' : '新增邮件模板'}</SheetTitle>
            <SheetDescription>可视化模式会保存 GrapesJS body_design，HTML 模式直接保存 body_html。</SheetDescription>
          </div>
          <form className="space-y-5 p-5" onSubmit={save}>
            <div className="grid gap-3 md:grid-cols-2">
              <div className="space-y-2">
                <Label>模板名称</Label>
                <Input value={form.name} onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>行业</Label>
                <Input value={form.industry} onChange={(event) => setForm((c) => ({ ...c, industry: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>主题</Label>
                <Input value={form.subject} onChange={(event) => setForm((c) => ({ ...c, subject: event.target.value }))} />
              </div>
              <div className="space-y-2">
                <Label>分类</Label>
                <Input value={form.category} onChange={(event) => setForm((c) => ({ ...c, category: event.target.value }))} />
              </div>
            </div>
            <div className="grid gap-4 xl:grid-cols-[280px_1fr]">
              <div className="space-y-3">
                <div className="space-y-2">
                  <Label>变量</Label>
                  <Textarea
                    className="min-h-36 font-mono text-xs"
                    value={form.variables_text}
                    onChange={(event) => setForm((c) => ({ ...c, variables_text: event.target.value }))}
                  />
                  <div className="flex flex-wrap gap-1">
                    {parseVariables(form.variables_text).map((variable) => (
                      <Badge key={variable.name} variant="outline">{`{{ ${variable.name} }}`}</Badge>
                    ))}
                  </div>
                </div>
                <label className="flex items-center gap-2 text-sm">
                  <Switch checked={form.is_active} onCheckedChange={(checked) => setForm((c) => ({ ...c, is_active: checked }))} />
                  启用模板
                </label>
                <Button type="button" variant="outline" onClick={() => setPreviewOpen(true)}>
                  <Eye className="h-4 w-4" />
                  预览
                </Button>
              </div>
              <Tabs value={mode} onValueChange={(value) => setMode(value as 'visual' | 'html')}>
                <TabsList>
                  <TabsTrigger value="html">
                    <Code2 className="mr-2 h-4 w-4" />
                    HTML 模式
                  </TabsTrigger>
                  <TabsTrigger value="visual">
                    <FileText className="mr-2 h-4 w-4" />
                    可视化模式
                  </TabsTrigger>
                </TabsList>
                <TabsContent value="html">
                  <Textarea
                    className="min-h-[520px] font-mono text-xs"
                    value={form.body_html}
                    onChange={(event) => setForm((c) => ({ ...c, body_html: event.target.value }))}
                  />
                </TabsContent>
                <TabsContent value="visual">
                  <GrapesEmailEditor
                    ref={editorRef}
                    html={form.body_html}
                    design={form.body_design}
                    onReady={() => toast.success('GrapesJS 编辑器已加载')}
                  />
                </TabsContent>
              </Tabs>
            </div>
            <div className="flex justify-end gap-2 border-t pt-4">
              <Button type="button" variant="outline" onClick={() => setDrawerOpen(false)}>
                取消
              </Button>
              <Button type="submit" disabled={saving}>
                保存
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>

      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-3xl">
          <DialogTitle>预览</DialogTitle>
          <DialogDescription>{form.subject || '邮件模板预览'}</DialogDescription>
          <div className="max-h-[70vh] overflow-auto rounded-md border bg-white p-4">
            <div dangerouslySetInnerHTML={{ __html: form.body_html }} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
