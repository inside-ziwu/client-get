'use client';

import type { IntelligenceSource } from '@shared/api';
import type { ImportResult } from '@shared/types';
import { useQuery } from '@tanstack/react-query';
import { FileJson, Plus } from 'lucide-react';
import { FormEvent, useEffect, useState } from 'react';
import { toast } from 'sonner';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogTitle,
  AlertDialogTrigger,
  Button,
  DataTable,
  type DataTableColumn,
  Input,
  Label,
  ListPage,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  Switch,
  Textarea,
} from '@shared/ui';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

type SourceFormValues = {
  name: string;
  source_type: IntelligenceSource['source_type'];
  url: string;
  config_json: string;
  is_active: boolean;
};

const EMPTY_SOURCE: SourceFormValues = {
  name: '',
  source_type: 'rss',
  url: '',
  config_json: '{}',
  is_active: true,
};

const SOURCE_TYPES: Array<{ label: string; value: IntelligenceSource['source_type'] }> = [
  { label: 'RSS', value: 'rss' },
  { label: '网站', value: 'website' },
  { label: '手工', value: 'manual' },
];

function parseJson(text: string) {
  const trimmed = text.trim();
  return trimmed ? JSON.parse(trimmed) : {};
}

function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

const SOURCE_TYPE_STATUS_MAP: Record<string, { label: string; tone: 'neutral' }> = {
  rss: { label: 'RSS', tone: 'neutral' },
  website: { label: '网站', tone: 'neutral' },
  manual: { label: '手工', tone: 'neutral' },
};

export function IntelligenceSourcesPage() {
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [updatingIds, setUpdatingIds] = useState<ReadonlySet<string>>(() => new Set());
  const [editing, setEditing] = useState<IntelligenceSource | null>(null);
  const [sourceForm, setSourceForm] = useState<SourceFormValues>(EMPTY_SOURCE);
  const [importOpen, setImportOpen] = useState(false);
  const [importing, setImporting] = useState(false);
  const [itemsJson, setItemsJson] = useState('');
  const query = useQuery({
    queryKey: ['admin', 'intelligence-sources'],
    queryFn: async () => (await adminApi.intelligenceSources.list()).data,
  });

  const load = async () => {
    await query.refetch();
  };

  const items = query.data?.data ?? [];

  useEffect(() => {
    if (query.isError) {
      toast.error('加载情报源失败');
    }
  }, [query.isError]);

  const openCreate = () => {
    setEditing(null);
    setSourceForm(EMPTY_SOURCE);
    setDrawerOpen(true);
  };

  const openEdit = (record: IntelligenceSource) => {
    setEditing(record);
    setSourceForm({
      name: record.name,
      source_type: record.source_type,
      url: record.url ?? '',
      config_json: formatJson(record.fetch_config ?? {}),
      is_active: record.is_active,
    });
    setDrawerOpen(true);
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!sourceForm.name.trim()) {
      toast.error('请输入名称');
      return;
    }

    setSaving(true);
    try {
      const payload = {
        name: sourceForm.name.trim(),
        source_type: sourceForm.source_type,
        url: sourceForm.url.trim() || undefined,
        fetch_config: parseJson(sourceForm.config_json),
        is_active: sourceForm.is_active,
      };

      if (editing) {
        await adminApi.intelligenceSources.update(editing.id, payload);
        toast.success('情报源已更新');
      } else {
        await adminApi.intelligenceSources.create(payload);
        toast.success('情报源已创建');
      }

      setDrawerOpen(false);
      setEditing(null);
      setSourceForm(EMPTY_SOURCE);
      await load();
    } catch (error) {
      if (error instanceof SyntaxError) {
        toast.error('配置 JSON 格式不正确');
        return;
      }
      const detail =
        (error as { response?: { data?: { detail?: string } }; message?: string })?.response?.data?.detail ??
        (error as Error)?.message ??
        '未知错误';
      toast.error(`保存失败：${detail}`);
    } finally {
      setSaving(false);
    }
  };

  const updateStatus = async (record: IntelligenceSource, checked: boolean) => {
    setUpdatingIds((current) => new Set(current).add(record.id));
    try {
      await adminApi.intelligenceSources.update(record.id, { is_active: checked });
      toast.success('状态已更新');
      await load();
    } catch {
      toast.error('状态更新失败');
    } finally {
      setUpdatingIds((current) => {
        const next = new Set(current);
        next.delete(record.id);
        return next;
      });
    }
  };

  const fillExample = () => {
    setItemsJson(
      JSON.stringify(
        [{ name: '行业动态 RSS', source_type: 'rss', url: 'https://example.com/rss', fetch_config: {} }],
        null,
        2,
      ),
    );
  };

  const saveImport = async () => {
    setImporting(true);
    try {
      const parsed = JSON.parse(itemsJson) as Array<Partial<IntelligenceSource>>;
      if (!Array.isArray(parsed)) {
        throw new Error('invalid');
      }
      const response = await adminApi.intelligenceSources.batchImport(parsed);
      const result = response.data.data as ImportResult;
      toast.success(`导入完成：成功 ${result.success} 条，失败 ${result.failed} 条`);
      setImportOpen(false);
      setItemsJson('');
      await load();
    } catch (error) {
      if (error instanceof SyntaxError || (error instanceof Error && error.message === 'invalid')) {
        toast.error('请粘贴合法的 JSON 数组');
        return;
      }
      toast.error('导入失败');
    } finally {
      setImporting(false);
    }
  };

  const columns: ReadonlyArray<DataTableColumn<IntelligenceSource>> = [
    {
      id: 'name',
      header: '名称',
      type: 'text',
      value: 'name',
      render: (item) => <span className="font-medium">{item.name}</span>,
    },
    {
      id: 'sourceType',
      header: '类型',
      width: 'small',
      type: 'status',
      value: 'source_type',
      statusMap: SOURCE_TYPE_STATUS_MAP,
    },
    { id: 'url', header: 'URL', width: 'large', type: 'text', value: 'url' },
    {
      id: 'active',
      header: '状态',
      width: 'small',
      type: 'boolean',
      value: 'is_active',
      booleanMode: 'interactive',
      getBooleanLabel: (item) => `${item.name}${item.is_active ? '已启用' : '已停用'}`,
      onBooleanChange: (item, checked) => void updateStatus(item, checked),
      isBooleanDisabled: (item) => updatingIds.has(item.id),
    },
    {
      id: 'lastFetchedAt',
      header: '最后采集',
      type: 'date',
      value: 'last_fetched_at',
      format: (value) => value ? formatDateTime(String(value)) : '从未',
    },
    {
      id: 'updatedAt',
      header: '更新时间',
      type: 'date',
      value: 'updated_at',
      format: (value) => formatDateTime(String(value)),
    },
    {
      id: 'actions',
      header: '操作',
      width: 'medium',
      align: 'center',
      type: 'actions',
      render: (item) => (
        <div className="flex items-center justify-center gap-ui-xxs">
          <Button
            variant="link"
            className="h-8 px-ui-xxs text-ui-foreground"
            onClick={() => openEdit(item)}
          >
            编辑
          </Button>
          <DeleteSourceAction source={item} onDeleted={load} />
        </div>
      ),
    },
  ];

  const tableState = query.isLoading
    ? { kind: 'loading' as const }
    : query.isError
      ? { kind: 'error' as const, description: '加载情报源失败', onRetry: () => void query.refetch() }
      : items.length === 0
        ? { kind: 'empty' as const }
        : undefined;

  return (
    <ListPage
      className="admin-page"
      title="情报源管理"
      description="仅保留后端支持的来源类型、启停、导入和删除。"
      primaryAction={(
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setImportOpen(true)}>
            <FileJson className="h-4 w-4" />
            批量导入
          </Button>
          <Button onClick={openCreate}>
            <Plus className="h-4 w-4" />
            新增情报源
          </Button>
        </div>
      )}
    >
      <DataTable
        columns={columns}
        data={items}
        entityName="情报源"
        getRowId={(item) => item.id}
        state={tableState}
        isRefreshing={query.isFetching && !query.isLoading}
      />

      <Sheet open={drawerOpen} onOpenChange={(next) => !saving && setDrawerOpen(next)}>
        <SheetContent className="max-w-xl overflow-y-auto p-0">
          <div className="border-b px-5 py-4">
            <SheetTitle>{editing ? `编辑情报源 - ${editing.name}` : '新增情报源'}</SheetTitle>
            <SheetDescription>配置来源类型、URL 与后端抓取参数。</SheetDescription>
          </div>
          <form className="flex min-h-0 flex-1 flex-col" onSubmit={save}>
            <div className="flex-1 space-y-4 overflow-y-auto p-5">
              <div className="space-y-2">
                <Label htmlFor="source-name">名称</Label>
                <Input
                  id="source-name"
                  value={sourceForm.name}
                  onChange={(event) => setSourceForm((current) => ({ ...current, name: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label>来源类型</Label>
                <Select
                  value={sourceForm.source_type}
                  onValueChange={(value: IntelligenceSource['source_type']) =>
                    setSourceForm((current) => ({ ...current, source_type: value }))
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {SOURCE_TYPES.map((item) => (
                      <SelectItem key={item.value} value={item.value}>
                        {item.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="source-url">URL</Label>
                <Input
                  id="source-url"
                  placeholder="https://example.com/rss"
                  value={sourceForm.url}
                  onChange={(event) => setSourceForm((current) => ({ ...current, url: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="source-config">配置 JSON</Label>
                <Textarea
                  id="source-config"
                  className="min-h-[180px] font-mono text-xs"
                  placeholder='{"category":"行业动态"}'
                  value={sourceForm.config_json}
                  onChange={(event) =>
                    setSourceForm((current) => ({ ...current, config_json: event.target.value }))
                  }
                />
              </div>
              <div className="flex h-10 items-center gap-4">
                <Label className="shrink-0" htmlFor="source-active">状态</Label>
                <div className="flex items-center gap-3">
                  <Switch
                    id="source-active"
                    checked={sourceForm.is_active}
                    onCheckedChange={(checked) => setSourceForm((current) => ({ ...current, is_active: checked }))}
                  />
                  <span className="text-sm text-muted-foreground">
                    {sourceForm.is_active ? '启用' : '停用'}
                  </span>
                </div>
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t p-4">
              <Button type="button" variant="outline" disabled={saving} onClick={() => setDrawerOpen(false)}>
                取消
              </Button>
              <Button type="submit" disabled={saving}>
                {saving ? '保存中…' : '保存'}
              </Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>

      <AlertDialog open={importOpen} onOpenChange={(next) => !importing && setImportOpen(next)}>
        <AlertDialogContent className="max-w-2xl">
          <AlertDialogTitle>批量导入情报源</AlertDialogTitle>
          <AlertDialogDescription>粘贴 JSON 数组后导入到后端。</AlertDialogDescription>
          <div className="space-y-3">
            <Button variant="outline" size="sm" onClick={fillExample}>
              填入示例
            </Button>
            <Textarea
              className="min-h-[260px] font-mono text-xs"
              placeholder='[{"name":"行业动态 RSS","source_type":"rss","url":"https://example.com/rss","fetch_config":{}}]'
              value={itemsJson}
              onChange={(event) => setItemsJson(event.target.value)}
            />
          </div>
          <div className="flex justify-end gap-2">
            <AlertDialogCancel disabled={importing}>取消</AlertDialogCancel>
            <AlertDialogAction
              disabled={importing}
              onClick={(event) => {
                event.preventDefault();
                void saveImport();
              }}
            >
              {importing ? '导入中…' : '开始导入'}
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </ListPage>
  );
}

function DeleteSourceAction({
  source,
  onDeleted,
}: {
  source: IntelligenceSource;
  onDeleted: () => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const deleteSource = async () => {
    setDeleting(true);
    try {
      await adminApi.intelligenceSources.delete(source.id);
      toast.success('情报源已删除');
      await onDeleted();
      setOpen(false);
    } catch {
      toast.error('删除失败');
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
        <AlertDialogTitle>确认删除「{source.name}」？</AlertDialogTitle>
        <AlertDialogDescription>删除后该情报源不会再参与采集。</AlertDialogDescription>
        <div className="flex justify-end gap-2">
          <AlertDialogCancel disabled={deleting}>取消</AlertDialogCancel>
          <AlertDialogAction
            variant="destructive"
            disabled={deleting}
            onClick={(event) => {
              event.preventDefault();
              void deleteSource();
            }}
          >
            {deleting ? '删除中…' : '删除'}
          </AlertDialogAction>
        </div>
      </AlertDialogContent>
    </AlertDialog>
  );
}
