'use client';

import type { AiModel, AiPricingResponse, AiSceneDefault } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Edit2, Plus, Trash2 } from 'lucide-react';
import { FormEvent, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { adminApi } from '@/lib/api';

type ModelFormValues = {
  display_name: string;
  provider: string;
  model_id: string;
  is_active: boolean;
};

const EMPTY_MODEL: ModelFormValues = {
  display_name: '',
  provider: '',
  model_id: '',
  is_active: true,
};

const SCENE_LABELS: Record<string, string> = {
  scoring: '客户评分',
  email_generation: '邮件生成',
  intelligence_summary: '情报摘要',
  data_analysis: '数据分析',
  general: '通用',
};

export function AIConfigPage() {
  const [models, setModels] = useState<AiModel[]>([]);
  const [sceneDefaults, setSceneDefaults] = useState<AiSceneDefault[]>([]);
  const [saving, setSaving] = useState(false);
  const [editingModel, setEditingModel] = useState<AiModel | null>(null);
  const [form, setForm] = useState<ModelFormValues>(EMPTY_MODEL);
  const query = useQuery({
    queryKey: ['admin', 'ai-config'],
    queryFn: async () => (await adminApi.aiConfig.getPricing()).data.data as AiPricingResponse,
  });

  const activeModels = useMemo(() => models.filter((model) => model.is_active), [models]);

  const load = async () => {
    await query.refetch();
  };

  useEffect(() => {
    if (query.isError) {
      toast.error('加载 AI 配置失败');
      return;
    }

    if (!query.data) return;

    setModels(query.data.models ?? []);
    setSceneDefaults(query.data.scene_defaults ?? []);
  }, [query.data, query.isError]);

  const openCreate = () => {
    setEditingModel(null);
    setForm(EMPTY_MODEL);
  };

  const openEdit = (record: AiModel) => {
    setEditingModel(record);
    setForm({
      display_name: record.display_name,
      provider: record.provider,
      model_id: record.model_id,
      is_active: record.is_active,
    });
  };

  const saveModel = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    try {
      const payload = {
        display_name: form.display_name.trim(),
        provider: form.provider.trim(),
        model_id: form.model_id.trim(),
        is_active: form.is_active,
      };
      if (!payload.display_name || !payload.provider || !payload.model_id) {
        toast.error('请填写完整模型信息');
        return;
      }

      if (editingModel) {
        await adminApi.aiConfig.updateModel(editingModel.id, payload);
        toast.success('模型已更新');
      } else {
        await adminApi.aiConfig.createModel(payload);
        toast.success('模型已创建');
      }

      setEditingModel(null);
      setForm(EMPTY_MODEL);
      await load();
    } catch (error: unknown) {
      const axiosDetail = (error as { response?: { data?: { detail?: unknown; message?: string } } })?.response?.data;
      const detail =
        axiosDetail?.message ??
        (typeof axiosDetail?.detail === 'string' ? axiosDetail.detail : undefined) ??
        (error as Error)?.message ??
        '未知错误';
      toast.error(`保存失败：${detail}`);
    } finally {
      setSaving(false);
    }
  };

  const deleteModel = async (id: string) => {
    try {
      await adminApi.aiConfig.deleteModel(id);
      toast.success('模型已删除');
      await load();
    } catch {
      toast.error('删除失败');
    }
  };

  const updateModelActive = async (record: AiModel, checked: boolean) => {
    try {
      await adminApi.aiConfig.updateModel(record.id, { is_active: checked });
      toast.success('状态已更新');
      await load();
    } catch {
      toast.error('状态更新失败');
    }
  };

  const updateSceneDefault = async (scene: string, modelId: string) => {
    const next = sceneDefaults.map((item) =>
      item.scene === scene ? { ...item, model_id: modelId } : item,
    );
    setSceneDefaults(next);

    try {
      await adminApi.aiConfig.updateSceneDefaults(next);
      toast.success('场景默认模型已更新');
    } catch (error) {
      const detail =
        (error as { response?: { data?: { error?: { message?: string } } }; message?: string })?.response?.data?.error
          ?.message ??
        (error as Error)?.message ??
        '未知错误';
      toast.error(`场景默认模型更新失败：${detail}`);
      await load();
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">AI 配置</h1>
          <p className="admin-page-description">模型、价格和场景默认值都直接写入后端。</p>
        </div>
        <Button variant="outline" onClick={openCreate}>
          <Plus className="h-4 w-4" />
          添加模型
        </Button>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1fr_360px]">
        <Card>
          <CardHeader>
            <CardTitle>模型列表</CardTitle>
            <CardDescription>{query.isLoading ? '正在加载...' : `${models.length} 个模型`}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto rounded-md border border-border">
              <table className="w-full min-w-[760px] text-sm">
                <thead className="bg-muted/70 text-left text-xs text-muted-foreground">
                  <tr>
                    <th className="px-3 py-2">名称</th>
                    <th className="w-36 px-3 py-2">Provider</th>
                    <th className="px-3 py-2">Model ID</th>
                    <th className="w-24 px-3 py-2">启用</th>
                    <th className="w-36 px-3 py-2 text-right">操作</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((model) => (
                    <tr key={model.id} className="border-t border-border">
                      <td className="px-3 py-2 font-medium">{model.display_name}</td>
                      <td className="px-3 py-2">
                        <Badge variant="outline">{model.provider}</Badge>
                      </td>
                      <td className="px-3 py-2 font-mono text-xs">{model.model_id}</td>
                      <td className="px-3 py-2">
                        <Switch
                          checked={model.is_active}
                          onCheckedChange={(checked) => void updateModelActive(model, checked)}
                        />
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex justify-end gap-1">
                          <Button variant="ghost" size="icon" aria-label="编辑模型" onClick={() => openEdit(model)}>
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            aria-label="删除模型"
                            onClick={() => void deleteModel(model.id)}
                          >
                            <Trash2 className="h-4 w-4 text-destructive" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>{editingModel ? '编辑模型' : '添加模型'}</CardTitle>
            <CardDescription>保存后会刷新模型列表。</CardDescription>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={saveModel}>
              <div className="space-y-2">
                <Label htmlFor="display_name">显示名称</Label>
                <Input
                  id="display_name"
                  value={form.display_name}
                  onChange={(event) => setForm((current) => ({ ...current, display_name: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="provider">Provider</Label>
                <Input
                  id="provider"
                  value={form.provider}
                  onChange={(event) => setForm((current) => ({ ...current, provider: event.target.value }))}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model_id">Model ID</Label>
                <Input
                  id="model_id"
                  placeholder="openrouter/google/gemini-2.5"
                  value={form.model_id}
                  onChange={(event) => setForm((current) => ({ ...current, model_id: event.target.value }))}
                />
              </div>
              <div className="flex items-center justify-between rounded-md border border-border px-3 py-2">
                <Label htmlFor="is_active">启用</Label>
                <Switch
                  id="is_active"
                  checked={form.is_active}
                  onCheckedChange={(checked) => setForm((current) => ({ ...current, is_active: checked }))}
                />
              </div>
              <Button className="w-full" type="submit" disabled={saving}>
                保存
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>场景默认模型</CardTitle>
          <CardDescription>切换后立即保存到后端。</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {sceneDefaults.map((record) => (
              <div key={record.id ?? record.scene} className="rounded-md border border-border p-3">
                <div className="mb-2 text-sm font-medium">{SCENE_LABELS[record.scene] ?? record.scene}</div>
                <Select
                  value={record.model_id}
                  onValueChange={(value) => void updateSceneDefault(record.scene, value)}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="选择默认模型" />
                  </SelectTrigger>
                  <SelectContent>
                    {[...activeModels, ...models.filter((model) => model.id === record.model_id && !model.is_active)].map(
                      (model) => (
                        <SelectItem key={model.id} value={model.id}>
                          {model.display_name}
                        </SelectItem>
                      ),
                    )}
                  </SelectContent>
                </Select>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
