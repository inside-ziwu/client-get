'use client';

import type { ScoringTemplate } from '@shared/api';
import { Edit2, Eye, Plus, Trash2 } from 'lucide-react';
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
} from '@/components/ui/alert-dialog';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet';
import { Switch } from '@/components/ui/switch';
import { Textarea } from '@/components/ui/textarea';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

type Dimension = {
  key: string;
  name: string;
  weight: string;
  conditions: Array<{ label: string; score: string }>;
};

type TemplateForm = {
  industry: string;
  name: string;
  description: string;
  dimensions: Dimension[];
  grade_thresholds: Record<'S' | 'A' | 'B' | 'C' | 'D', string>;
  is_active: boolean;
};

const DEFAULT_DIMENSIONS: Dimension[] = [
  { key: 'company_fit', name: '公司匹配度', weight: '20', conditions: [{ label: '目标行业', score: '20' }] },
  { key: 'scale', name: '规模', weight: '15', conditions: [{ label: '规模达标', score: '15' }] },
  { key: 'contact', name: '联系人质量', weight: '15', conditions: [{ label: '有关键联系人', score: '15' }] },
];

const EMPTY_FORM: TemplateForm = {
  industry: '',
  name: '',
  description: '',
  dimensions: DEFAULT_DIMENSIONS,
  grade_thresholds: { S: '90', A: '80', B: '70', C: '60', D: '0' },
  is_active: true,
};

const GRADE_LABELS: Record<'S' | 'A' | 'B' | 'C' | 'D', string> = {
  S: 'S 级',
  A: 'A 级',
  B: 'B 级',
  C: 'C 级',
  D: 'D 级',
};

function normalizeDimensions(value: Array<Record<string, unknown>> | undefined): Dimension[] {
  if (!value?.length) return DEFAULT_DIMENSIONS;
  return value.map((item, index) => {
    const rawConditions = Array.isArray(item.conditions) ? item.conditions : [];
    return {
      key: String(item.key ?? item.name ?? `dimension_${index + 1}`),
      name: String(item.name ?? item.label ?? `维度 ${index + 1}`),
      weight: String(item.weight ?? item.score ?? 0),
      conditions: rawConditions.length
        ? rawConditions.map((condition) => {
            const record = condition as Record<string, unknown>;
            return { label: String(record.label ?? record.name ?? ''), score: String(record.score ?? 0) };
          })
        : [{ label: '默认条件', score: String(item.score ?? 0) }],
    };
  });
}

function toForm(template: ScoringTemplate): TemplateForm {
  return {
    industry: template.industry ?? '',
    name: template.name,
    description: template.description ?? '',
    dimensions: normalizeDimensions(template.dimensions),
    grade_thresholds: {
      S: String(template.grade_thresholds?.S ?? 90),
      A: String(template.grade_thresholds?.A ?? 80),
      B: String(template.grade_thresholds?.B ?? 70),
      C: String(template.grade_thresholds?.C ?? 60),
      D: String(template.grade_thresholds?.D ?? 0),
    },
    is_active: template.is_active ?? true,
  };
}

function DimensionEditor({
  value,
  onChange,
}: {
  value: Dimension[];
  onChange: (value: Dimension[]) => void;
}) {
  const updateDimension = (index: number, patch: Partial<Dimension>) => {
    onChange(value.map((item, current) => (current === index ? { ...item, ...patch } : item)));
  };
  const updateCondition = (dimensionIndex: number, conditionIndex: number, patch: Partial<Dimension['conditions'][number]>) => {
    onChange(
      value.map((dimension, current) =>
        current === dimensionIndex
          ? {
              ...dimension,
              conditions: dimension.conditions.map((condition, index) =>
                index === conditionIndex ? { ...condition, ...patch } : condition,
              ),
            }
          : dimension,
      ),
    );
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label>评分维度</Label>
        <Button
          type="button"
          size="sm"
          variant="outline"
          onClick={() => onChange([...value, { key: `dimension_${value.length + 1}`, name: '', weight: '0', conditions: [] }])}
        >
          <Plus className="h-4 w-4" />
          添加维度
        </Button>
      </div>
      {value.map((dimension, dimensionIndex) => (
        <div key={dimensionIndex} className="space-y-3 rounded-md border p-3">
          <div className="grid gap-2 md:grid-cols-[1fr_1fr_100px_auto]">
            <Input placeholder="key" value={dimension.key} onChange={(event) => updateDimension(dimensionIndex, { key: event.target.value })} />
            <Input placeholder="名称" value={dimension.name} onChange={(event) => updateDimension(dimensionIndex, { name: event.target.value })} />
            <Input placeholder="权重" value={dimension.weight} onChange={(event) => updateDimension(dimensionIndex, { weight: event.target.value })} />
            <Button type="button" variant="ghost" size="icon" onClick={() => onChange(value.filter((_, index) => index !== dimensionIndex))}>
              <Trash2 className="h-4 w-4 text-destructive" />
            </Button>
          </div>
          <div className="space-y-2">
            {dimension.conditions.map((condition, conditionIndex) => (
              <div key={conditionIndex} className="grid gap-2 md:grid-cols-[1fr_100px_auto]">
                <Input placeholder="条件" value={condition.label} onChange={(event) => updateCondition(dimensionIndex, conditionIndex, { label: event.target.value })} />
                <Input placeholder="分数" value={condition.score} onChange={(event) => updateCondition(dimensionIndex, conditionIndex, { score: event.target.value })} />
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  onClick={() => updateDimension(dimensionIndex, { conditions: dimension.conditions.filter((_, index) => index !== conditionIndex) })}
                >
                  <Trash2 className="h-4 w-4 text-destructive" />
                </Button>
              </div>
            ))}
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => updateDimension(dimensionIndex, { conditions: [...dimension.conditions, { label: '', score: '0' }] })}
            >
              添加条件
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ScoringTemplatesPage() {
  const [items, setItems] = useState<ScoringTemplate[]>([]);
  const [industry, setIndustry] = useState('');
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [editing, setEditing] = useState<ScoringTemplate | null>(null);
  const [form, setForm] = useState<TemplateForm>(EMPTY_FORM);

  const load = async () => {
    try {
      const response = await adminApi.scoringTemplates.list(industry || undefined);
      setItems(response.data.data);
    } catch {
      toast.error('加载评分模板失败');
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const openEdit = async (template: ScoringTemplate) => {
    try {
      const response = await adminApi.scoringTemplates.detail(template.id);
      setEditing(response.data.data);
      setForm(toForm(response.data.data));
      setDrawerOpen(true);
    } catch {
      toast.error('加载模板详情失败');
    }
  };

  const save = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const payload = {
      industry: form.industry.trim() || undefined,
      name: form.name.trim(),
      description: form.description.trim() || undefined,
      is_active: form.is_active,
      dimensions: form.dimensions.map((dimension) => ({
        key: dimension.key,
        name: dimension.name,
        weight: Number(dimension.weight || 0),
        conditions: dimension.conditions.map((condition) => ({
          label: condition.label,
          score: Number(condition.score || 0),
        })),
      })),
      grade_thresholds: Object.fromEntries(
        Object.entries(form.grade_thresholds).map(([key, value]) => [key, Number(value || 0)]),
      ),
    };
    try {
      if (editing) {
        await adminApi.scoringTemplates.update(editing.id, payload);
        toast.success('评分模板已更新');
      } else {
        await adminApi.scoringTemplates.create(payload);
        toast.success('评分模板已创建');
      }
      setDrawerOpen(false);
      await load();
    } catch {
      toast.error('保存评分模板失败');
    }
  };

  const deleteTemplate = async (template: ScoringTemplate) => {
    try {
      await adminApi.scoringTemplates.delete(template.id);
      toast.success('评分模板已删除');
      await load();
    } catch {
      toast.error('删除评分模板失败');
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">评分模板</h1>
          <p className="admin-page-description">评分模板 CRUD、DimensionEditor、等级阈值和预览。</p>
        </div>
        <Button onClick={() => { setEditing(null); setForm(EMPTY_FORM); setDrawerOpen(true); }}>
          <Plus className="h-4 w-4" />
          新增模板
        </Button>
      </div>

      <Card>
        <CardContent className="p-4">
          <div className="flex gap-2">
            <Input placeholder="按行业筛选" value={industry} onChange={(event) => setIndustry(event.target.value)} />
            <Button variant="outline" onClick={() => void load()}>查询</Button>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[980px] text-sm">
              <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  {['名称', '行业', '版本', '等级阈值', '状态', '更新时间', '操作'].map((label) => <th key={label} className="px-4 py-3">{label}</th>)}
                </tr>
              </thead>
              <tbody>
                {items.map((item) => (
                  <tr key={item.id} className="border-b last:border-0">
                    <td className="px-4 py-3 font-medium">{item.name}</td>
                    <td className="px-4 py-3">{item.industry || '-'}</td>
                    <td className="px-4 py-3">v{item.version ?? 1}</td>
                    <td className="px-4 py-3 text-xs text-muted-foreground">{JSON.stringify(item.grade_thresholds ?? {})}</td>
                    <td className="px-4 py-3"><Badge variant={item.is_active ? 'secondary' : 'outline'}>{item.is_active ? '启用' : '停用'}</Badge></td>
                    <td className="px-4 py-3 text-muted-foreground">{formatDateTime(item.updated_at)}</td>
                    <td className="px-4 py-3">
                      <div className="flex justify-end gap-1">
                        <Button variant="ghost" size="icon" onClick={() => void openEdit(item)}><Edit2 className="h-4 w-4" /></Button>
                        <Button variant="ghost" size="icon" onClick={() => { setForm(toForm(item)); setPreviewOpen(true); }}><Eye className="h-4 w-4" /></Button>
                        <AlertDialog>
                          <AlertDialogTrigger asChild><Button variant="ghost" size="icon"><Trash2 className="h-4 w-4 text-destructive" /></Button></AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogTitle>确认删除评分模板？</AlertDialogTitle>
                            <AlertDialogDescription>删除后不可恢复。</AlertDialogDescription>
                            <div className="flex justify-end gap-2"><AlertDialogCancel>取消</AlertDialogCancel><AlertDialogAction onClick={() => void deleteTemplate(item)}>删除</AlertDialogAction></div>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <Sheet open={drawerOpen} onOpenChange={setDrawerOpen}>
        <SheetContent className="max-w-5xl overflow-y-auto p-0 sm:w-[960px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{editing ? '编辑评分模板' : '新增评分模板'}</SheetTitle>
            <SheetDescription>支持旧格式 dimensions 归一化后再编辑。</SheetDescription>
          </div>
          <form className="space-y-5 p-5" onSubmit={save}>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-2"><Label>名称</Label><Input value={form.name} onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))} /></div>
              <div className="space-y-2"><Label>行业</Label><Input value={form.industry} onChange={(event) => setForm((c) => ({ ...c, industry: event.target.value }))} /></div>
              <label className="flex items-end gap-2 pb-2 text-sm"><Switch checked={form.is_active} onCheckedChange={(checked) => setForm((c) => ({ ...c, is_active: checked }))} />启用</label>
            </div>
            <div className="space-y-2"><Label>描述</Label><Textarea value={form.description} onChange={(event) => setForm((c) => ({ ...c, description: event.target.value }))} /></div>
            <DimensionEditor value={form.dimensions} onChange={(dimensions) => setForm((c) => ({ ...c, dimensions }))} />
            <div className="space-y-2">
              <Label>等级阈值</Label>
              <div className="grid gap-2 sm:grid-cols-5">
                {(['S', 'A', 'B', 'C', 'D'] as const).map((grade) => (
                  <div key={grade} className="space-y-1">
                    <Label>{GRADE_LABELS[grade]}</Label>
                    <Input value={form.grade_thresholds[grade]} onChange={(event) => setForm((c) => ({ ...c, grade_thresholds: { ...c.grade_thresholds, [grade]: event.target.value } }))} />
                  </div>
                ))}
              </div>
            </div>
            <div className="flex justify-end gap-2 border-t pt-4">
              <Button type="button" variant="outline" onClick={() => setPreviewOpen(true)}>预览</Button>
              <Button type="submit">保存</Button>
            </div>
          </form>
        </SheetContent>
      </Sheet>

      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-2xl">
          <DialogTitle>预览</DialogTitle>
          <DialogDescription>{form.name || '评分模板预览'}</DialogDescription>
          <pre className="max-h-[70vh] overflow-auto rounded-md bg-muted p-3 text-xs">{JSON.stringify(form, null, 2)}</pre>
        </DialogContent>
      </Dialog>
    </div>
  );
}
