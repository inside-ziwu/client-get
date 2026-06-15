'use client';

import { useState } from 'react';
import { Edit2 } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, Input, Label, Badge, Button } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { PageHeader } from '@/components/pages/page-kit';

const GRADE_ORDER = ['S', 'A', 'B', 'C', 'D'] as const;

type TemplateState = {
  grade_thresholds: Record<string, string>;
  dimensions: Array<{ conditions: Array<{ score: string }> }>;
};

export default function ScoringPage() {
  const queryClient = useQueryClient();
  const templatesQuery = useQuery({
    queryKey: ['tenant', 'scoring'],
    queryFn: async () => (await tenantApi.scoring.get()).data.data,
  });

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editState, setEditState] = useState<TemplateState | null>(null);

  const updateMutation = useMutation({
    mutationFn: async ({ id, state }: { id: string; state: TemplateState }) => {
      return tenantApi.scoring.update(id, {
        grade_thresholds: Object.fromEntries(Object.entries(state.grade_thresholds).map(([k, v]) => [k, Number(v || 0)])),
        dimensions: state.dimensions.map((dim) => ({
          conditions: dim.conditions.map((c) => ({ score: Number(c.score || 0) })),
        })),
      });
    },
    onSuccess: async () => {
      toast.success('评分配置已更新');
      setEditingId(null);
      setEditState(null);
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'scoring'] });
    },
  });

  function startEditing(template: Record<string, any>) {
    const rawThresholds = (template.grade_thresholds ?? {}) as Record<string, number | string>;
    const rawDims = (template.dimensions ?? []) as Array<Record<string, any>>;
    setEditingId(template.id as string);
    setEditState({
      grade_thresholds: Object.fromEntries(GRADE_ORDER.map((g) => [g, String(rawThresholds[g] ?? 0)])),
      dimensions: rawDims.map((dim) => ({
        conditions: ((dim.conditions ?? dim.rules ?? []) as Array<Record<string, any>>).map((c) => ({
          score: String(c.score ?? 0),
        })),
      })),
    });
  }

  function cancelEditing() {
    setEditingId(null);
    setEditState(null);
  }

  return (
    <div className="tenant-page">
      <PageHeader title="评分配置" description="查看评分规则，调整评分分值和等级阈值" />
      <div className="grid gap-4">
        {(templatesQuery.data ?? []).map((template: Record<string, any>) => {
          const tid = template.id as string;
          const isEditing = editingId === tid;
          const rawDims = (template.dimensions ?? []) as Array<Record<string, any>>;
          const rawThresholds = (template.grade_thresholds ?? {}) as Record<string, number | string>;

          return (
            <Card key={tid}>
              <CardContent className="space-y-5 p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="font-medium">{String(template.name ?? '评分模板')}</h2>
                    <p className="text-sm text-muted-foreground">版本 {String(template.version ?? '-')}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    {template.is_active ? <Badge>启用中</Badge> : <Badge variant="secondary">停用</Badge>}
                    {!isEditing && (
                      <Button size="sm" variant="outline" onClick={() => startEditing(template)}>
                        <Edit2 className="mr-1 h-3.5 w-3.5" />
                        编辑
                      </Button>
                    )}
                  </div>
                </div>

                <div>
                  <Label className="mb-2 block text-sm font-medium">评分维度</Label>
                  <div className="space-y-3">
                    {rawDims.map((dim, dimIdx) => {
                      const conditions = (dim.conditions ?? dim.rules ?? []) as Array<Record<string, any>>;
                      return (
                        <div key={dimIdx} className="rounded-md border border-border p-3">
                          <div className="mb-2 text-sm font-medium">{String(dim.name ?? dim.key ?? `维度 ${dimIdx + 1}`)}</div>
                          <div className="space-y-1">
                            {conditions.map((cond, condIdx) => (
                              <div key={condIdx} className="flex items-center gap-2 text-sm">
                                <span className="flex-1 text-muted-foreground">{String(cond.label ?? cond.condition ?? '')}</span>
                                {isEditing ? (
                                  <>
                                    <Input
                                      type="number"
                                      className="w-20"
                                      value={editState?.dimensions[dimIdx]?.conditions[condIdx]?.score ?? String(cond.score ?? 0)}
                                      onChange={(e) => {
                                        if (!editState) return;
                                        const dims = editState.dimensions.map((d, di) =>
                                          di === dimIdx ? { ...d, conditions: d.conditions.map((c, ci) => ci === condIdx ? { ...c, score: e.target.value } : c) } : d,
                                        );
                                        setEditState({ ...editState, dimensions: dims });
                                      }}
                                    />
                                    <span className="text-xs text-muted-foreground">分</span>
                                  </>
                                ) : (
                                  <span className="text-sm font-medium">{cond.score ?? 0} 分</span>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div>
                  <Label className="mb-2 block text-sm font-medium">等级阈值</Label>
                  <div className="grid gap-2 sm:grid-cols-5">
                    {GRADE_ORDER.map((grade) => (
                      <div key={grade} className="space-y-1">
                        <Label className="text-xs">{grade} 级 ≥</Label>
                        {isEditing ? (
                          <Input
                            type="number"
                            value={editState?.grade_thresholds[grade] ?? '0'}
                            onChange={(e) => {
                              if (!editState) return;
                              setEditState({ ...editState, grade_thresholds: { ...editState.grade_thresholds, [grade]: e.target.value } });
                            }}
                          />
                        ) : (
                          <div className="flex h-9 items-center rounded-md border border-border bg-muted/30 px-3 text-sm">
                            {rawThresholds[grade] ?? 0}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

                {isEditing && editState && (
                  <div className="flex justify-end gap-2 border-t pt-3">
                    <Button size="sm" variant="outline" onClick={cancelEditing}>
                      取消
                    </Button>
                    <Button size="sm" onClick={() => updateMutation.mutate({ id: tid, state: editState })} disabled={updateMutation.isPending}>
                      保存
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
