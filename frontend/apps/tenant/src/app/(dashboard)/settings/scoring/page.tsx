'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { Card, CardContent, Input, Label, Badge } from '@shared/ui';
import { tenantApi } from '@/lib/api';
import { PageHeader } from '@/components/pages/page-kit';

export default function ScoringPage() {
  const queryClient = useQueryClient();
  const templatesQuery = useQuery({
    queryKey: ['tenant', 'scoring'],
    queryFn: async () => (await tenantApi.scoring.get()).data.data,
  });
  const updateMutation = useMutation({
    mutationFn: async ({ id, weight }: { id: string; weight: number }) => {
      const template = templatesQuery.data?.find((item) => item.id === id);
      if (!template) throw new Error('template not found');
      return tenantApi.scoring.update(id, {
        ...template,
        dimensions: template.dimensions.map((item, index) => (index === 0 ? { ...item, weight } : item)),
      });
    },
    onSuccess: async () => {
      toast.success('评分配置已更新');
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'scoring'] });
    },
  });

  return (
    <div className="tenant-page">
      <PageHeader title="评分配置" description="调整评分维度和阈值" />
      <div className="grid gap-4">
        {(templatesQuery.data ?? []).map((template) => (
          <Card key={template.id}>
            <CardContent className="space-y-4 p-5">
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="font-medium">{template.name ?? '评分模板'}</h2>
                  <p className="text-sm text-muted-foreground">版本 {template.version ?? '-'}</p>
                </div>
                {template.is_active ? <Badge>启用中</Badge> : <Badge variant="secondary">停用</Badge>}
              </div>
              <div className="grid gap-3 md:grid-cols-2">
                {template.dimensions.map((dimension) => (
                  <div key={dimension.name} className="rounded-md border border-border p-3">
                    <Label>{dimension.name}</Label>
                    <div className="mt-2 flex items-center gap-2">
                      <Input
                        type="number"
                        defaultValue={dimension.weight}
                        onBlur={(event) => updateMutation.mutate({ id: template.id, weight: Number(event.target.value) })}
                      />
                      <span className="text-sm text-muted-foreground">权重</span>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
