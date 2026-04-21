import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Input,
  InputNumber,
  Popconfirm,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createApiClient, createTenantApi, queryKeys, type TenantScoringTemplate } from '@shared/api';

const { Text, Title } = Typography;

interface ScoringDimension {
  id: string;
  name: string;
  weight: number;
  criteria: string;
}

type EditableTemplate = Omit<TenantScoringTemplate, 'dimensions'> & {
  id: string;
  dimensions: ScoringDimension[];
  updated_at: string;
};

const api = createTenantApi(createApiClient('tenant'));

function pickActiveTemplate(items: TenantScoringTemplate[]): TenantScoringTemplate | null {
  return items.find((item) => item.is_active) ?? items[0] ?? null;
}

function normalizeTemplate(template: TenantScoringTemplate | null): EditableTemplate | null {
  if (!template) {
    return null;
  }

  return {
    ...template,
    updated_at: template.updated_at ?? new Date().toISOString(),
    dimensions: (template.dimensions ?? []).map((item, index) => ({
      id: `${index}-${item.name}`,
      name: String(item.name ?? ''),
      weight: Number(item.weight ?? 0),
      criteria: typeof item.criteria === 'string' ? item.criteria : '',
    })),
  };
}

export function Component() {
  const queryClient = useQueryClient();
  const [dimensions, setDimensions] = useState<ScoringDimension[]>([]);

  const scoringQuery = useQuery<EditableTemplate | null>({
    queryKey: queryKeys.scoring.all(),
    queryFn: async () => {
      const items = (await api.scoring.get()).data.data;
      return normalizeTemplate(pickActiveTemplate(items));
    },
  });

  useEffect(() => {
    if (scoringQuery.data) {
      setDimensions(scoringQuery.data.dimensions);
    } else {
      setDimensions([]);
    }
  }, [scoringQuery.data]);

  const totalWeight = useMemo(
    () => dimensions.reduce((sum, item) => sum + (Number.isFinite(item.weight) ? item.weight : 0), 0),
    [dimensions],
  );
  const canSave = totalWeight === 100 && dimensions.every((item) => item.name.trim() && item.criteria.trim());

  const updateMutation = useMutation({
    mutationFn: (payload: EditableTemplate) =>
      api.scoring.update(payload.id, {
        name: payload.name,
        grade_thresholds: payload.grade_thresholds,
        dimensions: payload.dimensions.map((item) => ({
          name: item.name.trim(),
          weight: Number(item.weight),
          criteria: item.criteria.trim(),
        })),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.scoring.all() });
      message.success('评分规则已保存');
    },
    onError: () => message.error('保存失败，请稍后重试'),
  });

  const columns: ColumnsType<ScoringDimension> = [
    {
      title: '维度',
      dataIndex: 'name',
      render: (_, record, index) => (
        <Input
          value={record.name}
          placeholder="维度名称"
          onChange={(e) => setDimensions((prev) => prev.map((item, i) => (i === index ? { ...item, name: e.target.value } : item)))}
        />
      ),
    },
    {
      title: '权重',
      dataIndex: 'weight',
      width: 120,
      render: (_, record, index) => (
        <InputNumber
          value={record.weight}
          min={0}
          max={100}
          style={{ width: '100%' }}
          onChange={(value) => setDimensions((prev) => prev.map((item, i) => (i === index ? { ...item, weight: Number(value ?? 0) } : item)))}
        />
      ),
    },
    {
      title: '判定条件',
      dataIndex: 'criteria',
      render: (_, record, index) => (
        <Input
          value={record.criteria}
          placeholder="例如：职位/描述包含 PCB 采购关键词"
          onChange={(e) => setDimensions((prev) => prev.map((item, i) => (i === index ? { ...item, criteria: e.target.value } : item)))}
        />
      ),
    },
    {
      title: '操作',
      width: 100,
      render: (_, __, index) => (
        <Popconfirm
          title="删除该维度？"
          onConfirm={() => setDimensions((prev) => prev.filter((_, i) => i !== index))}
          disabled={dimensions.length <= 1}
        >
          <Button type="link" danger icon={<DeleteOutlined />} disabled={dimensions.length <= 1}>
            删除
          </Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start' }}>
        <div>
          <Title level={5} style={{ marginBottom: 4 }}>评分配置</Title>
          <Text type="secondary">直接从 `/api/v1/scoring-templates` 读取当前启用模板，不再依赖页面内强转。</Text>
        </div>
        <Button
          type="primary"
          onClick={() => {
            if (!scoringQuery.data) {
              message.error('当前没有可编辑的评分模板');
              return;
            }
            if (!canSave) {
              message.error('权重合计必须等于 100，且所有字段都不能为空');
              return;
            }
            updateMutation.mutate({ ...scoringQuery.data, dimensions: [...dimensions] });
          }}
          loading={updateMutation.isPending}
          disabled={!scoringQuery.data}
        >
          保存配置
        </Button>
      </div>

      <Alert
        type="info"
        showIcon
        message="评分模板支持在线编辑维度名称、权重和判定条件。保存后会立即写回当前启用模板。"
      />

      <Card
        size="small"
        title={
          <Space>
            <span>评分维度</span>
            <Tag color={totalWeight === 100 ? 'green' : 'red'}>合计 {totalWeight}%</Tag>
          </Space>
        }
        extra={
          <Button
            icon={<PlusOutlined />}
            onClick={() => setDimensions((prev) => [...prev, { id: `new-${Date.now()}`, name: '', weight: 0, criteria: '' }])}
            disabled={!scoringQuery.data}
          >
            新增维度
          </Button>
        }
      >
        {!scoringQuery.isLoading && !scoringQuery.data && <Empty description="后台暂无评分模板" />}
        {scoringQuery.data && !canSave && dimensions.length > 0 && (
          <Alert
            type="warning"
            showIcon
            message="请确保所有维度都已填写完整，且总权重为 100 才能保存。"
            style={{ marginBottom: 12 }}
          />
        )}
        <Table<ScoringDimension>
          rowKey="id"
          columns={columns}
          dataSource={dimensions}
          loading={scoringQuery.isLoading}
          pagination={false}
          size="middle"
          locale={{ emptyText: '暂无评分维度' }}
        />
      </Card>

      <Card size="small">
        <Space direction="vertical" size={4}>
          <Text strong>同步信息</Text>
          <Text type="secondary">最后同步：{scoringQuery.data ? new Date(scoringQuery.data.updated_at).toLocaleString('zh-CN') : '—'}</Text>
          <Text type="secondary">保存后会影响后续重新评分，不会回写历史结果。</Text>
        </Space>
      </Card>
    </Space>
  );
}

Component.displayName = 'ScoringSettingsPage';
