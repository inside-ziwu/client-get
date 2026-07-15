'use client';

import type { ScoringTemplate } from '@shared/api';
import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
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
  Dialog,
  DialogContent,
  DialogDescription,
  DialogTitle,
  FilterBar,
  type FilterField,
  Input,
  Label,
  ListPage,
  Sheet,
  SheetContent,
  SheetDescription,
  SheetTitle,
  Switch,
  Textarea,
} from '@shared/ui';
import { adminApi } from '@/lib/api';
import { formatDateTime } from '@/lib/format';

type DimensionCondition = {
  label: string;
  score: string;
  condition: string;
  value?: unknown;
  min?: string;
  max?: string;
};

type Dimension = {
  key: string;
  name: string;
  hint?: string;
  weight: string;
  conditions: DimensionCondition[];
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
  { key: 'company_fit', name: '公司匹配度', weight: '20', conditions: [{ label: '目标行业', score: '20', condition: 'default' }] },
  { key: 'scale', name: '规模', weight: '15', conditions: [{ label: '规模达标', score: '15', condition: 'default' }] },
  { key: 'contact', name: '联系人质量', weight: '15', conditions: [{ label: '有关键联系人', score: '15', condition: 'has_contact' }] },
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

type ScoringTemplateFilters = { industry: string };

const EMPTY_FILTERS: ScoringTemplateFilters = { industry: '' };
const FILTER_FIELDS: ReadonlyArray<FilterField<ScoringTemplateFilters>> = [
  {
    name: 'industry',
    kind: 'text',
    label: '行业',
    placeholder: '输入行业名称',
    width: 'medium',
  },
];

function normalizeDimensions(value: Array<Record<string, unknown>> | undefined): Dimension[] {
  if (!value?.length) return DEFAULT_DIMENSIONS;
  return value.map((item, index) => {
    const rawConditions = Array.isArray(item.conditions) ? item.conditions : (Array.isArray(item.rules) ? item.rules : []);
    return {
      key: String(item.key ?? item.id ?? item.name ?? `dimension_${index + 1}`),
      name: String(item.name ?? item.label ?? `维度 ${index + 1}`),
      hint: item.hint ? String(item.hint) : undefined,
      weight: String(item.weight ?? item.score ?? 0),
      conditions: rawConditions.length
        ? rawConditions.map((condition) => {
            const record = condition as Record<string, unknown>;
            return {
              label: String(record.label ?? record.name ?? ''),
              score: String(record.score ?? 0),
              condition: String(record.condition ?? 'default'),
              value: record.value,
              min: record.min != null ? String(record.min) : undefined,
              max: record.max != null ? String(record.max) : undefined,
            };
          })
        : [{ label: '默认条件', score: String(item.score ?? 0), condition: 'default' }],
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
          onClick={() => onChange([...value, { key: `dimension_${value.length + 1}`, name: '', weight: '0', conditions: [{ label: '', score: '0', condition: 'default' }] }])}
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
              <div key={conditionIndex} className="space-y-1 rounded border border-dashed p-2">
                <div className="grid gap-2 md:grid-cols-[120px_1fr_80px_auto]">
                  <Input placeholder="条件类型" value={condition.condition} onChange={(event) => updateCondition(dimensionIndex, conditionIndex, { condition: event.target.value })} />
                  <Input placeholder="标签" value={condition.label} onChange={(event) => updateCondition(dimensionIndex, conditionIndex, { label: event.target.value })} />
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
                {(condition.min != null || condition.max != null || condition.value != null) && (
                  <div className="grid gap-2 md:grid-cols-3">
                    {condition.value != null && (
                      <Input placeholder="匹配值 (JSON)" value={typeof condition.value === 'string' ? condition.value : JSON.stringify(condition.value)} onChange={(event) => { try { updateCondition(dimensionIndex, conditionIndex, { value: JSON.parse(event.target.value) }); } catch { updateCondition(dimensionIndex, conditionIndex, { value: event.target.value }); } }} />
                    )}
                    {condition.min != null && (
                      <Input placeholder="最小值" value={condition.min} onChange={(event) => updateCondition(dimensionIndex, conditionIndex, { min: event.target.value })} />
                    )}
                    {condition.max != null && (
                      <Input placeholder="最大值" value={condition.max} onChange={(event) => updateCondition(dimensionIndex, conditionIndex, { max: event.target.value })} />
                    )}
                  </div>
                )}
              </div>
            ))}
            <Button
              type="button"
              size="sm"
              variant="outline"
              onClick={() => updateDimension(dimensionIndex, { conditions: [...dimension.conditions, { label: '', score: '0', condition: 'default' }] })}
            >
              添加条件
            </Button>
          </div>
        </div>
      ))}
    </div>
  );
}

export function ScoringTemplatesPage() {
  const [draftFilters, setDraftFilters] = useState<ScoringTemplateFilters>(EMPTY_FILTERS);
  const [appliedFilters, setAppliedFilters] = useState<ScoringTemplateFilters>(EMPTY_FILTERS);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [previewOpen, setPreviewOpen] = useState(false);
  const [editing, setEditing] = useState<ScoringTemplate | null>(null);
  const [form, setForm] = useState<TemplateForm>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [updatingIds, setUpdatingIds] = useState<ReadonlySet<string>>(() => new Set());
  const query = useQuery({
    queryKey: ['admin', 'scoring-templates', appliedFilters.industry],
    queryFn: async () => (
      await adminApi.scoringTemplates.list(appliedFilters.industry || undefined)
    ).data,
    placeholderData: keepPreviousData,
  });

  const load = async () => {
    await query.refetch();
  };

  const items = query.data?.data ?? [];

  useEffect(() => {
    if (query.isError) {
      toast.error('加载评分模板失败');
    }
  }, [query.isError]);

  const openCreate = () => {
    setEditing(null);
    setForm(EMPTY_FORM);
    setDrawerOpen(true);
  };

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
        hint: dimension.hint || undefined,
        weight: Number(dimension.weight || 0),
        conditions: dimension.conditions.map((condition) => {
          const c: Record<string, unknown> = {
            label: condition.label,
            score: Number(condition.score || 0),
            condition: condition.condition || 'default',
          };
          if (condition.value != null) c.value = condition.value;
          if (condition.min != null) c.min = Number(condition.min);
          if (condition.max != null) c.max = Number(condition.max);
          return c;
        }),
      })),
      grade_thresholds: Object.fromEntries(
        Object.entries(form.grade_thresholds).map(([key, value]) => [key, Number(value || 0)]),
      ),
    };
    setSaving(true);
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
    } finally {
      setSaving(false);
    }
  };

  const resetFilters = () => {
    setDraftFilters(EMPTY_FILTERS);
    setAppliedFilters(EMPTY_FILTERS);
  };

  const updateStatus = async (template: ScoringTemplate, checked: boolean) => {
    setUpdatingIds((current) => new Set(current).add(template.id));
    try {
      await adminApi.scoringTemplates.update(template.id, { is_active: checked });
      toast.success('状态已更新');
      await load();
    } catch {
      toast.error('状态更新失败');
    } finally {
      setUpdatingIds((current) => {
        const next = new Set(current);
        next.delete(template.id);
        return next;
      });
    }
  };

  const columns: ReadonlyArray<DataTableColumn<ScoringTemplate>> = [
    {
      id: 'name',
      header: '名称',
      type: 'text',
      value: 'name',
      render: (item) => <span className="font-medium">{item.name}</span>,
    },
    { id: 'industry', header: '行业', type: 'text', value: 'industry' },
    {
      id: 'version',
      header: '版本',
      width: 'small',
      align: 'center',
      type: 'number',
      value: 'version',
      render: (item) => `v${item.version ?? 1}`,
    },
    {
      id: 'thresholds',
      header: '等级阈值',
      width: 'large',
      type: 'text',
      value: 'grade_thresholds',
      format: (value) => JSON.stringify(value ?? {}),
    },
    {
      id: 'status',
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
      id: 'updatedAt',
      header: '更新时间',
      type: 'date',
      value: 'updated_at',
      format: (value) => formatDateTime(String(value)),
    },
    {
      id: 'actions',
      header: '操作',
      width: 'large',
      align: 'center',
      type: 'actions',
      render: (item) => (
        <div className="flex items-center justify-center gap-ui-xxs">
          <Button
            variant="link"
            className="h-8 px-ui-xxs text-ui-foreground"
            onClick={() => void openEdit(item)}
          >
            编辑
          </Button>
          <Button
            variant="link"
            className="h-8 px-ui-xxs text-ui-foreground"
            onClick={() => {
              setForm(toForm(item));
              setPreviewOpen(true);
            }}
          >
            预览
          </Button>
          <DeleteScoringTemplateAction template={item} onDeleted={load} />
        </div>
      ),
    },
  ];

  const tableState = query.isLoading
    ? { kind: 'loading' as const }
    : query.isError
      ? { kind: 'error' as const, description: '加载评分模板失败', onRetry: () => void query.refetch() }
      : items.length === 0
        ? {
            kind: 'empty' as const,
            filtered: Boolean(appliedFilters.industry),
            onResetFilters: appliedFilters.industry ? resetFilters : undefined,
          }
        : undefined;

  return (
    <ListPage
      className="admin-page"
      title="评分模板"
      description="评分模板 CRUD、DimensionEditor、等级阈值和预览。"
      primaryAction={(
        <Button onClick={openCreate}>
          <Plus className="h-4 w-4" />
          新增模板
        </Button>
      )}
      filters={(
        <FilterBar
          values={draftFilters}
          fields={FILTER_FIELDS}
          onChange={setDraftFilters}
          onSubmit={(next) => {
            const industry = next.industry.trim();
            if (industry === appliedFilters.industry) {
              void query.refetch();
              return;
            }
            setAppliedFilters({ industry });
          }}
          onReset={resetFilters}
          isSubmitting={query.isFetching}
          layout="compact"
          collapseAdvanced={false}
          actionsPlacement="inline"
        />
      )}
    >
      <DataTable
        columns={columns}
        data={items}
        entityName="评分模板"
        getRowId={(item) => item.id}
        state={tableState}
        isRefreshing={query.isFetching && !query.isLoading}
      />

      <Sheet open={drawerOpen} onOpenChange={(next) => !saving && setDrawerOpen(next)}>
        <SheetContent className="max-w-5xl overflow-y-auto p-0 sm:w-[960px]">
          <div className="border-b px-5 py-4">
            <SheetTitle>{editing ? '编辑评分模板' : '新增评分模板'}</SheetTitle>
            <SheetDescription>支持旧格式 dimensions 归一化后再编辑。</SheetDescription>
          </div>
          <form className="space-y-5 p-5" onSubmit={save}>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-2"><Label>名称</Label><Input value={form.name} onChange={(event) => setForm((c) => ({ ...c, name: event.target.value }))} /></div>
              <div className="space-y-2"><Label>行业</Label><Input value={form.industry} onChange={(event) => setForm((c) => ({ ...c, industry: event.target.value }))} /></div>
              <div className="space-y-2">
                <Label htmlFor="scoring-template-active">状态</Label>
                <div className="flex h-10 items-center gap-3">
                  <Switch
                    id="scoring-template-active"
                    checked={form.is_active}
                    onCheckedChange={(checked) => setForm((c) => ({ ...c, is_active: checked }))}
                  />
                  <span className="text-sm text-muted-foreground">
                    {form.is_active ? '启用' : '停用'}
                  </span>
                </div>
              </div>
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
              <Button type="submit" disabled={saving}>{saving ? '保存中…' : '保存'}</Button>
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
    </ListPage>
  );
}

function DeleteScoringTemplateAction({
  template,
  onDeleted,
}: {
  template: ScoringTemplate;
  onDeleted: () => Promise<unknown>;
}) {
  const [open, setOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const deleteTemplate = async () => {
    setDeleting(true);
    try {
      await adminApi.scoringTemplates.delete(template.id);
      toast.success('评分模板已删除');
      await onDeleted();
      setOpen(false);
    } catch {
      toast.error('删除评分模板失败');
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
        <AlertDialogDescription>删除后不可恢复。</AlertDialogDescription>
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
