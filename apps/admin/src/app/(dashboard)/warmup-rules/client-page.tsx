'use client';

import type { WarmupRuleLevel, WarmupRules } from '@shared/api';
import { useQuery } from '@tanstack/react-query';
import { Plus, Save, Trash2 } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { adminApi } from '@/lib/api';

const numericFields: Array<{
  key: keyof WarmupRuleLevel;
  label: string;
  step: string;
  min: string;
  max?: string;
}> = [
  { key: 'daily_limit', label: '每日上限', step: '1', min: '1' },
  { key: 'min_stay_days', label: '最少停留天数', step: '1', min: '1' },
  { key: 'min_delivery_rate', label: '最低送达率', step: '0.01', min: '0', max: '1' },
  { key: 'max_bounce_rate', label: '最高退信率', step: '0.001', min: '0', max: '1' },
  { key: 'max_complaint_rate', label: '最高投诉率', step: '0.0001', min: '0', max: '1' },
];

const emptyRule: WarmupRules = {
  name: '',
  min_observation_emails: 20,
  bounce_alert_rate: 0.02,
  levels: [],
};

export function WarmupRulesClientPage() {
  const [rule, setRule] = useState<WarmupRules>(emptyRule);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ['admin', 'warmup-rules'],
    queryFn: async () => (await adminApi.warmupRules.get()).data,
  });

  useEffect(() => {
    if (query.isLoading) return;

    if (query.isError) {
      setLoadError('预热规则加载失败，请检查接口与配置初始化状态');
      setRule(emptyRule);
      return;
    }

    const nextRule = query.data?.data[0];
    if (!nextRule) {
      setLoadError('后台暂无预热规则，请先初始化后端配置');
      setRule(emptyRule);
      return;
    }

    setLoadError(null);
    setRule({
      ...nextRule,
      min_observation_emails: nextRule.min_observation_emails ?? 20,
      levels: nextRule.levels ?? [],
    });
  }, [query.data, query.isError, query.isLoading]);

  const updateRule = (patch: Partial<WarmupRules>) => {
    setRule((current) => ({ ...current, ...patch }));
  };

  const updateLevel = (level: number, field: keyof WarmupRuleLevel, value: number) => {
    setRule((current) => ({
      ...current,
      levels: current.levels.map((item) =>
        item.level === level ? { ...item, [field]: value } : item,
      ),
    }));
  };

  const addLevel = () => {
    setRule((current) => {
      const maxLevel = current.levels.length > 0 ? Math.max(...current.levels.map((l) => l.level)) : 0;
      return {
        ...current,
        levels: [
          ...current.levels,
          {
            level: maxLevel + 1,
            daily_limit: 50,
            min_stay_days: 7,
            min_delivery_rate: 0.95,
            max_bounce_rate: 0.02,
            max_complaint_rate: 0.001,
          },
        ],
      };
    });
  };

  const removeLevel = (level: number) => {
    setRule((current) => ({
      ...current,
      levels: current.levels.filter((item) => item.level !== level),
    }));
  };

  const onSave = async () => {
    if (!rule.id) {
      toast.error('规则 ID 丢失，请刷新页面后重试');
      return;
    }
    if (!rule.name.trim()) {
      toast.error('请输入规则名称');
      return;
    }

    setSaving(true);
    try {
      await adminApi.warmupRules.update(rule);
      toast.success('预热规则已保存');
    } catch (error: unknown) {
      const detail = (error as { response?: { data?: { message?: string } } })?.response?.data?.message;
      toast.error(detail ?? '保存失败，请检查控制台');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <div>
          <h1 className="admin-page-title">预热规则</h1>
          <p className="admin-page-description">直接编辑并保存到后端。</p>
        </div>
        <Button onClick={onSave} disabled={Boolean(loadError) || saving}>
          <Save className="h-4 w-4" />
          保存
        </Button>
      </div>

      <div className="rounded-md border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
        这里是全局配置，保存后会影响所有用户域名的预热策略。
      </div>
      {loadError && (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {loadError}
        </div>
      )}

      <Card>
        <CardHeader>
          <CardTitle>规则配置</CardTitle>
          <CardDescription>{query.isLoading ? '正在加载...' : `当前共有 ${rule.levels.length} 个预热档位`}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5">
          <div className="grid gap-4 md:grid-cols-3">
            <div className="space-y-2 md:col-span-2">
              <Label htmlFor="name">规则名称</Label>
              <Input
                id="name"
                value={rule.name}
                onChange={(event) => updateRule({ name: event.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="bounce_alert_rate">退信报警阈值</Label>
              <Input
                id="bounce_alert_rate"
                type="number"
                min="0"
                max="1"
                step="0.001"
                value={rule.bounce_alert_rate}
                onChange={(event) => updateRule({ bounce_alert_rate: Number(event.target.value) })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="min_observation_emails">最小观察样本数</Label>
              <Input
                id="min_observation_emails"
                type="number"
                min="1"
                value={rule.min_observation_emails ?? 20}
                onChange={(event) => updateRule({ min_observation_emails: Number(event.target.value) })}
              />
            </div>
          </div>

          <div className="flex items-center justify-between">
            <div className="text-sm font-medium">档位规则</div>
            <Button variant="outline" size="sm" onClick={addLevel}>
              <Plus className="h-4 w-4" />
              新增档位
            </Button>
          </div>

          <div className="overflow-x-auto rounded-md border border-border">
            <table className="w-full min-w-[860px] text-sm">
              <thead className="bg-muted/70 text-left text-xs text-muted-foreground">
                <tr>
                  <th className="w-20 px-3 py-2">档位</th>
                  {numericFields.map((field) => (
                    <th key={field.key} className="px-3 py-2">
                      {field.label}
                    </th>
                  ))}
                  <th className="w-16 px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {rule.levels.map((level) => (
                  <tr key={level.level} className="border-t border-border">
                    <td className="px-3 py-2">
                      <Badge variant="secondary">L{level.level}</Badge>
                    </td>
                    {numericFields.map((field) => (
                      <td key={field.key} className="px-3 py-2">
                        <Input
                          type="number"
                          min={field.min}
                          max={field.max}
                          step={field.step}
                          value={level[field.key]}
                          onChange={(event) => updateLevel(level.level, field.key, Number(event.target.value))}
                        />
                      </td>
                    ))}
                    <td className="px-3 py-2 text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        aria-label="删除档位"
                        onClick={() => removeLevel(level.level)}
                      >
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
