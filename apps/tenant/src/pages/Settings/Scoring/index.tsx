import { useState } from 'react';
import {
  Card,
  Table,
  InputNumber,
  Select,
  Button,
  Space,
  Typography,
  Tag,
  Alert,
  Descriptions,
  message,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { RatingTag } from '@shared/ui';

const { Text, Title } = Typography;
const { Option } = Select;

interface Dimension {
  key: string;
  name: string;
  weight: number;
  method: 'keyword' | 'range' | 'boolean';
  description: string;
}

interface GradeThreshold {
  grade: 'S' | 'A' | 'B' | 'C' | 'D';
  min: number;
  max: number;
  color: string;
}

const INITIAL_DIMENSIONS: Dimension[] = [
  { key: 'scale', name: '公司规模', weight: 25, method: 'range', description: '员工数 / 营收规模' },
  { key: 'procurement', name: '采购相关性', weight: 30, method: 'keyword', description: '职位/公司描述含PCB采购关键词' },
  { key: 'activity', name: '近期活跃度', weight: 20, method: 'range', description: '近90天采购记录/发布动态次数' },
  { key: 'contact', name: '决策层联系人', weight: 15, method: 'boolean', description: '是否有Purchasing/Sourcing职级联系人' },
  { key: 'geography', name: '地区优先级', weight: 10, method: 'keyword', description: '目标国家/地区匹配程度' },
];

const INITIAL_THRESHOLDS: GradeThreshold[] = [
  { grade: 'S', min: 85, max: 100, color: 'gold' },
  { grade: 'A', min: 70, max: 84, color: 'green' },
  { grade: 'B', min: 55, max: 69, color: 'blue' },
  { grade: 'C', min: 40, max: 54, color: 'orange' },
  { grade: 'D', min: 0, max: 39, color: 'default' },
];

const METHOD_LABELS: Record<string, string> = {
  keyword: '关键词匹配',
  range: '数值范围',
  boolean: '是/否',
};

export function Component() {
  const [dimensions, setDimensions] = useState<Dimension[]>(INITIAL_DIMENSIONS);
  const [thresholds, setThresholds] = useState<GradeThreshold[]>(INITIAL_THRESHOLDS);
  const [curatedThreshold, setCuratedThreshold] = useState<'S' | 'A' | 'B' | 'C'>('A');

  const totalWeight = dimensions.reduce((s, d) => s + d.weight, 0);
  const weightOk = totalWeight === 100;

  const updateWeight = (key: string, val: number | null) => {
    setDimensions((prev) =>
      prev.map((d) => d.key === key ? { ...d, weight: val ?? 0 } : d)
    );
  };

  const updateThreshold = (grade: string, field: 'min' | 'max', val: number | null) => {
    setThresholds((prev) =>
      prev.map((t) => t.grade === grade ? { ...t, [field]: val ?? 0 } : t)
    );
  };

  const handleSave = () => {
    if (!weightOk) {
      message.error('各维度权重之和必须等于100，请调整后再保存');
      return;
    }
    message.success('评分配置已保存，将在下次重新评分时生效');
  };

  const dimColumns: ColumnsType<Dimension> = [
    { title: '维度', dataIndex: 'name', render: (v) => <Text strong>{v}</Text> },
    { title: '说明', dataIndex: 'description', render: (v) => <Text type="secondary" style={{ fontSize: 12 }}>{v}</Text> },
    {
      title: '评分方式', dataIndex: 'method', width: 110,
      render: (v) => <Tag>{METHOD_LABELS[v]}</Tag>,
    },
    {
      title: (
        <Space>
          权重
          <Tag color={weightOk ? 'green' : 'red'}>合计 {totalWeight}</Tag>
        </Space>
      ),
      dataIndex: 'weight',
      width: 130,
      render: (v, r) => (
        <InputNumber
          value={v}
          min={0}
          max={100}
          suffix="%"
          size="small"
          style={{ width: 100 }}
          onChange={(val) => updateWeight(r.key, val)}
        />
      ),
    },
  ];

  const thresholdColumns: ColumnsType<GradeThreshold> = [
    {
      title: '评级',
      dataIndex: 'grade',
      width: 80,
      render: (v, r) => <Tag color={r.color}>{v}级</Tag>,
    },
    {
      title: '最低分',
      dataIndex: 'min',
      width: 120,
      render: (v, r) => r.grade === 'D' ? (
        <Text type="secondary">0（兜底）</Text>
      ) : (
        <InputNumber
          value={v}
          min={0}
          max={100}
          size="small"
          style={{ width: 90 }}
          onChange={(val) => updateThreshold(r.grade, 'min', val)}
        />
      ),
    },
    {
      title: '最高分',
      dataIndex: 'max',
      width: 120,
      render: (v, r) => r.grade === 'S' ? (
        <Text type="secondary">100（上限）</Text>
      ) : (
        <InputNumber
          value={v}
          min={0}
          max={100}
          size="small"
          style={{ width: 90 }}
          onChange={(val) => updateThreshold(r.grade, 'max', val)}
        />
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Title level={5} style={{ marginBottom: 4 }}>评分配置</Title>
          <Text type="secondary">调整各评分维度权重和评级阈值，以符合您的业务侧重</Text>
        </div>
        <Button type="primary" onClick={handleSave} disabled={!weightOk}>
          保存配置
        </Button>
      </div>

      <Alert
        type="info"
        showIcon
        message="当前评分规则由平台管理员基于您所在行业（PCB）预配置。您可以在此调整权重和阈值，修改将在下次重新评分时应用。"
      />

      <Card title="评分维度与权重" size="small">
        {!weightOk && (
          <Alert
            type="warning"
            showIcon
            message={`当前权重合计为 ${totalWeight}，需调整至 100 才能保存`}
            style={{ marginBottom: 12 }}
          />
        )}
        <Table
          rowKey="key"
          columns={dimColumns}
          dataSource={dimensions}
          size="small"
          pagination={false}
        />
      </Card>

      <Card title="评级阈值" size="small">
        <Table
          rowKey="grade"
          columns={thresholdColumns}
          dataSource={thresholds}
          size="small"
          pagination={false}
        />
        <div style={{ marginTop: 12 }}>
          <Text type="secondary" style={{ fontSize: 12 }}>
            提示：确保各评级分数段连续覆盖 0-100，避免出现空缺区间
          </Text>
        </div>
      </Card>

      <Card title="优选客户准入阈值" size="small">
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 16 }}>
          评分达到所设级别及以上的公司，将自动出现在「优选客户」列表中。
        </Text>
        <Space align="center" wrap>
          <Text>自动收录阈值：</Text>
          <Select
            value={curatedThreshold}
            onChange={setCuratedThreshold}
            style={{ width: 150 }}
          >
            {(['S', 'A', 'B', 'C'] as const).map((g) => (
              <Option key={g} value={g}>
                <Space size={4}>
                  <RatingTag grade={g} />
                  <span style={{ fontSize: 12 }}>及以上</span>
                </Space>
              </Option>
            ))}
          </Select>
          <Text type="secondary" style={{ fontSize: 12 }}>
            即总分 ≥ {thresholds.find((t) => t.grade === curatedThreshold)?.min ?? '—'} 分的公司自动收录
          </Text>
        </Space>
      </Card>

      <Card size="small" style={{ background: '#fafafa' }}>
        <Descriptions column={2} size="small" title={<Text strong style={{ fontSize: 13 }}>评分规则说明</Text>}>
          <Descriptions.Item label="评分来源">平台 PCB 行业通用模板</Descriptions.Item>
          <Descriptions.Item label="最后同步">2026-04-01</Descriptions.Item>
          <Descriptions.Item label="待评分">53 家</Descriptions.Item>
          <Descriptions.Item label="已评分">1,194 家</Descriptions.Item>
        </Descriptions>
      </Card>
    </Space>
  );
}

Component.displayName = 'ScoringSettingsPage';
