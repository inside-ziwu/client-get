import { useState } from 'react';
import {
  Table,
  Button,
  InputNumber,
  Typography,
  message,
  Alert,
  Form,
  Space,
  Card,
} from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text, Title } = Typography;

interface WarmupStage {
  stage: number;
  daily_limit: number;
  min_delivery_rate: number;
  max_bounce_rate: number;
  min_days: number;
}

const DEFAULT_STAGES: WarmupStage[] = [
  { stage: 1, daily_limit: 20,   min_delivery_rate: 95, max_bounce_rate: 2, min_days: 1 },
  { stage: 2, daily_limit: 50,   min_delivery_rate: 95, max_bounce_rate: 2, min_days: 1 },
  { stage: 3, daily_limit: 100,  min_delivery_rate: 95, max_bounce_rate: 2, min_days: 1 },
  { stage: 4, daily_limit: 200,  min_delivery_rate: 95, max_bounce_rate: 2, min_days: 1 },
  { stage: 5, daily_limit: 500,  min_delivery_rate: 95, max_bounce_rate: 2, min_days: 3 },
  { stage: 6, daily_limit: 1000, min_delivery_rate: 0,  max_bounce_rate: 100, min_days: 0 },
];

export function Component() {
  const [stages, setStages] = useState<WarmupStage[]>(DEFAULT_STAGES);
  const [bounceAlertThreshold, setBounceAlertThreshold] = useState(5);
  const [saving, setSaving] = useState(false);

  const updateStage = (stageNum: number, field: keyof WarmupStage, value: number) => {
    setStages((prev) => prev.map((s) => s.stage === stageNum ? { ...s, [field]: value } : s));
  };

  const handleSave = () => {
    setSaving(true);
    setTimeout(() => {
      setSaving(false);
      message.success('预热规则已保存，全平台生效');
    }, 800);
  };

  const columns: ColumnsType<WarmupStage> = [
    {
      title: '阶段',
      dataIndex: 'stage',
      width: 80,
      render: (v) => <Text strong>阶段 {v}</Text>,
    },
    {
      title: '每日上限（封）',
      dataIndex: 'daily_limit',
      width: 140,
      render: (v, r) => (
        <InputNumber
          value={v}
          min={1}
          size="small"
          style={{ width: 100 }}
          onChange={(val) => updateStage(r.stage, 'daily_limit', val ?? v)}
        />
      ),
    },
    {
      title: '升阶：最低触达率',
      dataIndex: 'min_delivery_rate',
      width: 150,
      render: (v, r) => r.stage === 6 ? (
        <Text type="secondary">— 最高阶段</Text>
      ) : (
        <InputNumber
          value={v}
          min={0}
          max={100}
          size="small"
          style={{ width: 100 }}
          formatter={(v) => `${v}%`}
          parser={(v) => Number(v?.replace('%', '') ?? 0) as unknown as number}
          onChange={(val) => updateStage(r.stage, 'min_delivery_rate', val ?? v)}
        />
      ),
    },
    {
      title: '升阶：最高退信率',
      dataIndex: 'max_bounce_rate',
      width: 150,
      render: (v, r) => r.stage === 6 ? (
        <Text type="secondary">—</Text>
      ) : (
        <InputNumber
          value={v}
          min={0}
          max={100}
          size="small"
          style={{ width: 100 }}
          formatter={(v) => `${v}%`}
          parser={(v) => Number(v?.replace('%', '') ?? 0) as unknown as number}
          onChange={(val) => updateStage(r.stage, 'max_bounce_rate', val ?? v)}
        />
      ),
    },
    {
      title: '最少停留（天）',
      dataIndex: 'min_days',
      width: 130,
      render: (v, r) => r.stage === 6 ? (
        <Text type="secondary">—</Text>
      ) : (
        <InputNumber
          value={v}
          min={1}
          size="small"
          style={{ width: 80 }}
          onChange={(val) => updateStage(r.stage, 'min_days', val ?? v)}
        />
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      {/* 标题 + 保存 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Title level={5} style={{ margin: 0 }}>预热阶段配置</Title>
        <Button
          type="primary"
          icon={<SaveOutlined />}
          loading={saving}
          onClick={handleSave}
        >
          保存
        </Button>
      </div>

      <Alert
        type="warning"
        showIcon
        message="规则全平台生效，所有租户域名共享此预热策略"
      />

      <Table
        rowKey="stage"
        columns={columns}
        dataSource={stages}
        size="middle"
        pagination={false}
      />

      {/* 告警配置 */}
      <Card size="small" title="告警配置">
        <Form layout="inline">
          <Form.Item label="退信率告警阈值">
            <InputNumber
              value={bounceAlertThreshold}
              min={1}
              max={50}
              formatter={(v) => `${v}%`}
              parser={(v) => Number(v?.replace('%', '') ?? 5) as unknown as number}
              onChange={(v) => setBounceAlertThreshold(v ?? 5)}
              style={{ width: 100 }}
            />
          </Form.Item>
          <Form.Item label="触发行为">
            <Text type="secondary">自动降阶 + 通知运营人员（系统固定逻辑）</Text>
          </Form.Item>
        </Form>
      </Card>
    </Space>
  );
}

Component.displayName = 'WarmupRulesPage';
