'use client';

import type { IntelligenceSource } from '@shared/api';
import type { ImportResult } from '@shared/types';
import { useQuery } from '@tanstack/react-query';
import { Edit2, FileJson, Plus, Trash2 } from 'lucide-react';
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
} from '@shared/ui';
import { Badge } from '@shared/ui';
import { Button } from '@shared/ui';
import { Card, CardContent } from '@shared/ui';
import { Input } from '@shared/ui';
import { Label } from '@shared/ui';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@shared/ui';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@shared/ui';
import { Switch } from '@shared/ui';
import { Textarea } from '@shared/ui';
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

function sourceTypeLabel(type: IntelligenceSource['source_type']) {
  return SOURCE_TYPES.find((item) => item.value === type)?.label ?? type;
}

export function IntelligenceSourcesPage() {
  const [items, setItems] = useState<IntelligenceSource[]>([]);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [saving, setSaving] = useState(false);
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

  useEffect(() => {
    if (query.isError) {
      toast.error('加载情报源失败');
      return;
    }

    setItems(query.data?.data ?? []);
  }, [query.data, query.isError]);

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
    try {
      await adminApi.intelligenceSources.update(record.id, { is_active: checked });
      toast.success('状态已更新');
      await load();
    } catch {
      toast.error('状态更新失败');
    }
  };

  const deleteSource = async (id: string) => {
    try {
      await adminApi.intelligenceSources.delete(id);
      toast.success('情报源已删除');
      await load();
    } catch {
      toast.error('删除失败');
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

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">情报源管理</h1>
          <p className="admin-page-description">仅保留后端支持的来源类型、启停、导入和删除。</p>
        </div>
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
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  <th className="px-4 py-3">名称</th>
                  <th className="w-24 px-4 py-3">类型</th>
                  <th className="px-4 py-3">URL</th>
                  <th className="w-24 px-4 py-3">启用</th>
                  <th className="w-40 px-4 py-3">最后采集</th>
                  <th className="w-40 px-4 py-3">更新时间</th>
                  <th className="w-28 px-4 py-3 text-right">操作</th>
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b last:border-0">
                    <td className="px-4 py-3 font-medium">{item.name}</td>
                    <td className="px-4 py-3">
                      <Badge variant="secondary">{sourceTypeLabel(item.source_type)}</Badge>
                    </td>
                    <td className="max-w-[320px] truncate px-4 py-3 text-xs text-muted-foreground">
                      {item.url || '-'}
                    </td>
                    <td className="px-4 py-3">
                      <Switch checked={item.is_active} onCheckedChange={(checked) => void updateStatus(item, checked)} />
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">
                      {item.last_fetched_at ? formatDateTime(item.last_fetched_at) : '从未'}
                    </td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDateTime(item.updated_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" aria-label="编辑情报源" onClick={() => openEdit(item)}>
                          <Edit2 className="h-4 w-4" />
                        </Button>
                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button variant="ghost" size="icon" aria-label="删除情报源">
                              <Trash2 className="h-4 w-4 text-destructive" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogTitle>确认删除该情报源？</AlertDialogTitle>
                            <AlertDialogDescription>删除后该情报源不会再参与采集。</AlertDialogDescription>
                            <div className="flex justify-end gap-2">
                              <AlertDialogCancel>取消</AlertDialogCancel>
                              <AlertDialogAction onClick={() => void deleteSource(item.id)}>删除</AlertDialogAction>
                            </div>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!items.length && (
              <div className="py-10 text-center text-sm text-muted-foreground">
                {query.isLoading ? '正在加载情报源...' : '暂无情报源'}
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="p-0">
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
              <div className="flex items-center justify-between rounded-md border px-3 py-2">
                <Label htmlFor="source-active">启用</Label>
                <Switch
                  id="source-active"
                  checked={sourceForm.is_active}
                  onCheckedChange={(checked) => setSourceForm((current) => ({ ...current, is_active: checked }))}
                />
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t p-4">
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

      <AlertDialog open={importOpen} onOpenChange={setImportOpen}>
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
            <AlertDialogAction onClick={() => void saveImport()} disabled={importing}>
              开始导入
            </AlertDialogAction>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
