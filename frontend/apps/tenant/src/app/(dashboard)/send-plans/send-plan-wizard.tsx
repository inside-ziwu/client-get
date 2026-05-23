'use client';

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import { useState } from 'react';
import { toast } from 'sonner';
import { Button, Card, CardContent } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import StepBasicInfo, { type PlanBasicInfo, validateBasicInfo } from './new/step-basic-info';
import StepConfigureSteps, { validateSteps } from './new/step-configure-steps';
import StepRecipients, { validateRecipients } from './new/step-recipients';
import StepConfirmation from './new/step-confirmation';

const STEPS = ['基本信息', '配置步骤', '收件人', '确认'] as const;

export interface StepConfig {
  step_number: number;
  template_id: string;
  delay_days: number;
  condition_type: string;
  use_ai_personalization: boolean;
  ai_instructions: string;
}

export interface WizardFormData {
  plan: PlanBasicInfo & {
    recipient_source: string;
    recipient_config: Record<string, string>;
  };
  steps: StepConfig[];
  lock_recipients: boolean;
}

function defaultFormData(): WizardFormData {
  return {
    plan: {
      name: '',
      description: '',
      sender_name: '',
      sender_email: '',
      domain_id: '',
      recipient_source: 'group',
      recipient_config: {},
    },
    steps: [
      {
        step_number: 1,
        template_id: '',
        delay_days: 0,
        condition_type: 'always',
        use_ai_personalization: false,
        ai_instructions: '',
      },
    ],
    lock_recipients: true,
  };
}

interface SendPlanWizardProps {
  mode: 'create' | 'edit';
  planId?: string;
  initialData?: WizardFormData;
}

export default function SendPlanWizard({ mode, planId, initialData }: SendPlanWizardProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [currentStep, setCurrentStep] = useState(0);
  const [formData, setFormData] = useState<WizardFormData>(initialData ?? defaultFormData);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const isEdit = mode === 'edit';

  const submitMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        plan: {
          name: formData.plan.name,
          description: formData.plan.description,
          sender_name: formData.plan.sender_name,
          sender_email: formData.plan.sender_email,
          domain_id: formData.plan.domain_id,
          recipient_source: formData.plan.recipient_source,
          recipient_config: formData.plan.recipient_config,
        },
        steps: formData.steps.map((s) => ({
          step_number: s.step_number,
          template_id: s.template_id,
          delay_days: s.delay_days,
          condition_type: s.condition_type,
          use_ai_personalization: s.use_ai_personalization,
          ai_instructions: s.ai_instructions || undefined,
        })),
        ...(isEdit ? {} : { lock_recipients: formData.lock_recipients }),
      };

      if (isEdit && planId) {
        return (await tenantApi.sendingPlans.completeUpdate(planId, payload)).data.data;
      }
      return (await tenantApi.sendingPlans.completeCreate({ ...payload, lock_recipients: formData.lock_recipients })).data.data;
    },
    onSuccess: (plan) => {
      toast.success(isEdit ? '计划已保存' : '发送计划创建成功');
      queryClient.invalidateQueries({ queryKey: ['tenant', 'sendingPlans'] });
      router.push(isEdit ? '/send-plans' : `/send-plans/${plan.id}`);
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: { message?: string } } };
      toast.error(axiosErr.response?.data?.message || (isEdit ? '保存失败' : '创建失败'));
    },
  });

  const validateCurrentStep = (): boolean => {
    if (currentStep === 0) {
      const errs = validateBasicInfo(formData.plan);
      setErrors(errs);
      return Object.keys(errs).length === 0;
    }
    if (currentStep === 1) {
      const errs = validateSteps(formData.steps);
      setErrors(errs);
      return Object.keys(errs).length === 0;
    }
    if (currentStep === 2) {
      const errs = validateRecipients(formData.plan.recipient_config);
      setErrors(errs);
      return Object.keys(errs).length === 0;
    }
    return true;
  };

  const goNext = () => {
    if (!validateCurrentStep()) return;
    setErrors({});
    setCurrentStep((s) => Math.min(s + 1, 3));
  };

  const goPrev = () => {
    setErrors({});
    setCurrentStep((s) => Math.max(s - 1, 0));
  };

  const handleSubmit = () => {
    if (!validateCurrentStep()) return;
    submitMutation.mutate();
  };

  return (
    <>
      {/* 步骤指示器 */}
      <div className="mb-6 flex items-center gap-2">
        {STEPS.map((label, i) => (
          <div key={label} className="flex items-center gap-2">
            {i > 0 && <div className="h-px w-8 bg-border" />}
            <button
              type="button"
              onClick={() => {
                if (i < currentStep) {
                  setErrors({});
                  setCurrentStep(i);
                }
              }}
              className={`flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                i === currentStep
                  ? 'bg-primary text-primary-foreground'
                  : i < currentStep
                    ? 'bg-muted text-foreground cursor-pointer hover:bg-muted/80'
                    : 'bg-muted/50 text-muted-foreground cursor-default'
              }`}
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-background/20 text-xs">
                {i + 1}
              </span>
              {label}
            </button>
          </div>
        ))}
      </div>

      <Card>
        <CardContent className="p-6">
          {currentStep === 0 && (
            <StepBasicInfo
              data={formData.plan}
              onChange={(plan) => setFormData((prev) => ({ ...prev, plan: { ...prev.plan, ...plan } }))}
              errors={errors}
            />
          )}
          {currentStep === 1 && (
            <StepConfigureSteps
              steps={formData.steps}
              onChange={(steps) => setFormData((prev) => ({ ...prev, steps }))}
              errors={errors}
            />
          )}
          {currentStep === 2 && (
            <StepRecipients
              recipientConfig={formData.plan.recipient_config}
              lockRecipients={formData.lock_recipients}
              onChange={(patch) =>
                setFormData((prev) => ({
                  ...prev,
                  plan: patch.recipient_config ? { ...prev.plan, recipient_config: patch.recipient_config } : prev.plan,
                  lock_recipients: patch.lock_recipients ?? prev.lock_recipients,
                }))
              }
              errors={errors}
            />
          )}
          {currentStep === 3 && <StepConfirmation formData={formData} />}
        </CardContent>
      </Card>

      {/* 底部导航 */}
      <div className="mt-4 flex justify-end gap-3">
        {currentStep > 0 && (
          <Button variant="outline" onClick={goPrev}>
            上一步
          </Button>
        )}
        {currentStep < 3 ? (
          <Button onClick={goNext}>下一步</Button>
        ) : (
          <Button onClick={handleSubmit} disabled={submitMutation.isPending}>
            {submitMutation.isPending
              ? (isEdit ? '保存中...' : '创建中...')
              : (isEdit ? '保存修改' : '创建计划')}
          </Button>
        )}
      </div>
    </>
  );
}
