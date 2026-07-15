'use client';

import type { PlatformEmailTemplate } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Edit2, Eye, Plus, Trash2 } from 'lucide-react';
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
import { EmailRichEditor, type EmailRichEditorHandle } from '@shared/ui';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

type TemplateForm = {
  industry: string;
  name: string;
  subject: string;
  variables_text: string;
  body_html: string;
  is_active: boolean;
};

const EMPTY_FORM: TemplateForm = {
  industry: '',
  name: '',
  subject: '',
  variables_text: 'company_name:公司名称\ncontact_name:联系人姓名\ncontact_email:联系人邮箱\nsender_name:发件人姓名',
  body_html: '<p>你好，{{contact_name}}</p>',
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
    variables_text: variablesToText(template.variables),
    body_html: template.body_html,
    is_active: template.is_active,
  };
}

export function EmailTemplatesPage() {
  const editorRef = useRef<EmailRichEditorHandle | null>(null);
  const [items, setItems] = useState<PlatformEmailTemplate[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [editing, setEditing] = useState<PlatformEmailTemplate | null>(null);
  const [form, setForm] = useState<TemplateForm>(EMPTY_FORM);
  const [editorKey, setEditorKey] = useState(0);
  const [bodyHtml, setBodyHtml] = useState('');
  const [bodyText, setBodyText] = useState('');
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
    setEditorKey((k) => k + 1);
    setDrawerOpen(true);
  };

  const openEdit = async (template: PlatformEmailTemplate) => {
    try {
      const response = await adminApi.emailTemplates.detail(template.id);
      const detail = response.data.data;
      setEditing(detail);
      setForm(templateToForm(detail));
      setEditorKey((k) => k + 1);
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
      const payload = {
        industry: form.industry.trim() || undefined,
        name: form.name.trim(),
        subject: form.subject.trim(),
        variables: parseVariables(form.variables_text),
        body_html: bodyHtml,
        body_text: bodyText,
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


  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">邮件模板管理</h1>
          <p className="admin-page-description">模板 CRUD、变量选择、富文本编辑和预览。</p>
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
            <SheetDescription>编辑邮件模板内容</SheetDescription>
          </div>
          <form className="space-y-5 p-5" onSubmit={save}>
            <div className="space-y-2">
              <Label>模板名称</Label>
              <Input value={form.name} onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))} />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <Switch checked={form.is_active} onCheckedChange={(checked) => setForm((c) => ({ ...c, is_active: checked }))} />
              启用模板
            </label>
            <div className="space-y-2">
              <Label>行业</Label>
              <Input value={form.industry} onChange={(event) => setForm((c) => ({ ...c, industry: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>邮件主题</Label>
              <Input value={form.subject} onChange={(event) => setForm((c) => ({ ...c, subject: event.target.value }))} />
            </div>
            <div className="space-y-2">
              <Label>变量（点击插入）</Label>
              <div className="flex flex-wrap gap-1">
                {parseVariables(form.variables_text).map((variable) => (
                  <Badge key={variable.name} variant="outline" className="cursor-pointer" onClick={() => editorRef.current?.insertVariable(`{{${variable.name}}}`)}>
                    {`{{${variable.name}}}`} {variable.label}
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
            <div className="flex justify-between border-t pt-4">
              <Button type="button" variant="outline" onClick={() => setPreviewOpen(true)}>
                <Eye className="h-4 w-4" />
                预览
              </Button>
              <div className="flex gap-2">
                <Button type="button" variant="outline" onClick={() => setDrawerOpen(false)}>
                  取消
                </Button>
                <Button type="submit" disabled={saving}>
                  保存
                </Button>
              </div>
            </div>
          </form>
        </SheetContent>
      </Sheet>

      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-3xl">
          <DialogTitle>预览</DialogTitle>
          <DialogDescription>{form.subject || '邮件模板预览'}</DialogDescription>
          <div className="max-h-[70vh] overflow-auto rounded-md border bg-white p-4">
            <div dangerouslySetInnerHTML={{ __html: bodyHtml }} />
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
