'use client';

import { useQuery } from '@tanstack/react-query';
import { Plus, Trash2 } from 'lucide-react';
import {
  Button,
  Card,
  CardContent,
  Checkbox,
  Input,
  Label,
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  Textarea,
} from '@shared/ui';
import { tenantApi } from '@/lib/api';
import type { StepConfig } from './page';

const CONDITION_OPTIONS = [
  { value: 'no_reply', label: '未回复' },
  { value: 'opened', label: '已打开' },
  { value: 'clicked', label: '已点击' },
] as const;

interface Props {
  steps: StepConfig[];
  onChange: (steps: StepConfig[]) => void;
  errors: Record<string, string>;
}

export function validateSteps(steps: StepConfig[]): Record<string, string> {
  const errors: Record<string, string> = {};
  steps.forEach((s, i) => {
    if (!s.template_id) errors[`step_${i}_template`] = '请选择邮件模板';
  });
  return errors;
}

export default function StepConfigureSteps({ steps, onChange, errors }: Props) {
  const templatesQuery = useQuery({
    queryKey: ['tenant', 'emailTemplates'],
    queryFn: async () => (await tenantApi.emailTemplates.list()).data.data,
  });

  const templates = templatesQuery.data ?? [];

  const updateStep = (index: number, patch: Partial<StepConfig>) => {
    const next = steps.map((s, i) => (i === index ? { ...s, ...patch } : s));
    onChange(next);
  };

  const addStep = () => {
    onChange([
      ...steps,
      {
        step_number: steps.length + 1,
        template_id: '',
        delay_days: 3,
        condition_type: 'no_reply',
        use_ai_personalization: false,
        ai_instructions: '',
      },
    ]);
  };

  const removeStep = (index: number) => {
    if (steps.length <= 1) return;
    const next = steps.filter((_, i) => i !== index).map((s, i) => ({ ...s, step_number: i + 1 }));
    onChange(next);
  };

  return (
    <div className="max-w-2xl space-y-4">
      {steps.map((step, i) => {
        const isFirst = i === 0;
        return (
          <Card key={step.step_number}>
            <CardContent className="space-y-4 p-4">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium">步骤 {step.step_number}</span>
                {!isFirst && steps.length > 1 && (
                  <Button variant="ghost" size="sm" onClick={() => removeStep(i)}>
                    <Trash2 className="mr-1 h-4 w-4" />
                    删除
                  </Button>
                )}
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>邮件模板 *</Label>
                  <Select value={step.template_id} onValueChange={(v) => updateStep(i, { template_id: v })}>
                    <SelectTrigger>
                      <SelectValue placeholder={templatesQuery.isLoading ? '加载中...' : '选择模板'} />
                    </SelectTrigger>
                    <SelectContent>
                      {templates.map((t) => (
                        <SelectItem key={t.id} value={t.id}>
                          {t.name}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  {errors[`step_${i}_template`] && (
                    <p className="text-sm text-destructive">{errors[`step_${i}_template`]}</p>
                  )}
                </div>

                <div className="space-y-2">
                  <Label>延迟天数</Label>
                  <Input
                    type="number"
                    min={0}
                    value={step.delay_days}
                    onChange={(e) => updateStep(i, { delay_days: Math.max(0, Number(e.target.value)) })}
                    disabled={isFirst}
                  />
                  {isFirst && <p className="text-xs text-muted-foreground">第一步固定为立即发送</p>}
                </div>
              </div>

              <div className="space-y-2">
                <Label>触发条件</Label>
                {isFirst ? (
                  <p className="text-sm text-muted-foreground">始终发送（第一步固定）</p>
                ) : (
                  <Select value={step.condition_type} onValueChange={(v) => updateStep(i, { condition_type: v })}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {CONDITION_OPTIONS.map((o) => (
                        <SelectItem key={o.value} value={o.value}>
                          {o.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                )}
              </div>

              <div className="space-y-2">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id={`ai-${i}`}
                    checked={step.use_ai_personalization}
                    onCheckedChange={(checked) => updateStep(i, { use_ai_personalization: checked === true })}
                  />
                  <Label htmlFor={`ai-${i}`} className="cursor-pointer">
                    启用 AI 个性化
                  </Label>
                </div>
                {step.use_ai_personalization && (
                  <Textarea
                    value={step.ai_instructions}
                    onChange={(e) => updateStep(i, { ai_instructions: e.target.value })}
                    placeholder="AI 个性化指令（可选）"
                    className="mt-2"
                  />
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}

      <Button variant="outline" onClick={addStep} className="w-full">
        <Plus className="mr-1 h-4 w-4" />
        添加步骤
      </Button>
    </div>
  );
}
