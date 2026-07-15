'use client';

import type { PlatformEmailTemplate } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Eye } from 'lucide-react';
import { FormEvent, useRef, useState } from 'react';
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
import { Button, CreateButton } from '@shared/ui';
import { DataTable, type DataTableColumn, ListPage } from '@shared/ui';
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

  const items = query.data?.data ?? [];

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

  const columns: ReadonlyArray<DataTableColumn<PlatformEmailTemplate>> = [
    { id: 'name', header: '模板', type: 'text', value: 'name' },
    { id: 'industry', header: '行业', type: 'text', value: 'industry' },
    { id: 'subject', header: '主题', width: 'large', type: 'text', value: 'subject' },
    {
      id: 'variables', header: '变量', width: 'large', type: 'text', value: 'variables',
      render: (item) => (
        <div className="flex flex-wrap gap-ui-xxs">
          {(item.variables ?? []).slice(0, 3).map((variable) => (
            <Badge key={variable.name} tone="neutral">{`{{ ${variable.name} }}`}</Badge>
          ))}
        </div>
      ),
    },
    { id: 'status', header: '状态', width: 'small', type: 'boolean', value: 'is_active', booleanMode: 'readOnly', getBooleanLabel: (item) => item.is_active ? '启用' : '停用' },
    { id: 'updatedAt', header: '更新时间', type: 'date', value: 'updated_at', format: (value) => formatDateTime(value as string) },
    {
      id: 'actions', header: '操作', width: 'medium', align: 'center', type: 'actions',
      render: (item) => (
        <div className="flex items-center justify-center gap-ui-xxs">
          <Button variant="link" className="h-8 px-ui-xxs text-ui-foreground" onClick={() => void openEdit(item)}>编辑</Button>
          <DeleteTemplateAction template={item} onDeleted={load} />
        </div>
      ),
    },
  ];

  const tableState = query.isLoading
    ? { kind: 'loading' as const }
    : query.isError
      ? { kind: 'error' as const, description: '加载邮件模板失败', onRetry: () => void query.refetch() }
      : items.length === 0
        ? { kind: 'empty' as const }
        : undefined;


  return (
    <ListPage
      className="admin-page"
      title="邮件模板管理"
      description="模板 CRUD、变量选择、富文本编辑和预览。"
      primaryAction={(
        <CreateButton onClick={openCreate}>
          新增模板
        </CreateButton>
      )}
    >
      <DataTable
        columns={columns}
        data={items}
        entityName="邮件模板"
        getRowId={(item) => item.id}
        state={tableState}
        isRefreshing={query.isFetching && !query.isLoading}
      />

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
                  <button
                    key={variable.name}
                    type="button"
                    aria-label={`插入变量 ${variable.label}`}
                    className="rounded-md focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    onClick={() => editorRef.current?.insertVariable(`{{${variable.name}}}`)}
                  >
                    <Badge variant="outline">
                      {`{{${variable.name}}}`} {variable.label}
                    </Badge>
                  </button>
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
    </ListPage>
  );
}

function DeleteTemplateAction({
  template,
  onDeleted,
}: {
  template: PlatformEmailTemplate;
  onDeleted: () => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const deleteTemplate = async () => {
    setDeleting(true);
    try {
      await adminApi.emailTemplates.delete(template.id);
      toast.success('邮件模板已删除');
      await onDeleted();
      setOpen(false);
    } catch {
      toast.error('删除邮件模板失败');
    } finally {
      setDeleting(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={(next) => !deleting && setOpen(next)}>
      <AlertDialogTrigger asChild>
        <Button
          variant="link"
          className="h-8 px-ui-xxs text-ui-foreground hover:text-ui-danger-foreground focus-visible:text-ui-danger-foreground"
        >
          删除
        </Button>
      </AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogTitle>确认删除「{template.name}」？</AlertDialogTitle>
        <AlertDialogDescription>删除后用户将无法继续选择该平台模板。</AlertDialogDescription>
        <div className="flex justify-end gap-2">
          <AlertDialogCancel disabled={deleting}>取消</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={deleting}
            onClick={(event) => {
              event.preventDefault();
              void deleteTemplate();
            }}
          >
            {deleting ? '删除中…' : '删除'}
          </AlertDialogAction>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
}
