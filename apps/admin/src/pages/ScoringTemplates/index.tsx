import React, { useState } from 'react';
import {
  Table,
  Button,
  Tag,
  Space,
  Drawer,
  Input,
  InputNumber,
  Select,
  Typography,
  Popconfirm,
  message,
  Alert,
  Switch,
} from 'antd';
import { PlusOutlined, EditOutlined, CopyOutlined, RobotOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text, Title } = Typography;
const { Option } = Select;

interface Dimension {
  id: string;
  name: string;
  description: string;
  max_score: number;
  type: 'rule' | 'llm';
}

interface ScoringTemplate {
  id: string;
  industry: string;
  dimension_count: number;
  is_active: boolean;
  created_at: string;
  dimensions: Dimension[];
}

const MOCK_TEMPLATES: ScoringTemplate[] = [
  {
    id: 't1', industry: 'PCB', dimension_count: 5, is_active: true, created_at: '2026-01-10',
    dimensions: [
      { id: 'd1', name: '国家匹配度', description: '目标采购国匹配程度', max_score: 20, type: 'rule' },
      { id: 'd2', name: '产品匹配度', description: '关键词语义相似度', max_score: 30, type: 'llm' },
      { id: 'd3', name: '公司规模', description: '员工数量区间判断', max_score: 15, type: 'rule' },
      { id: 'd4', name: '进出口记录', description: '近1年进出口频次', max_score: 15, type: 'rule' },
      { id: 'd5', name: '联系人丰富度', description: '有效邮箱联系人数量', max_score: 20, type: 'rule' },
    ],
  },
  {
    id: 't2', industry: '电子元器件', dimension_count: 4, is_active: true, created_at: '2026-02-05',
    dimensions: [
      { id: 'd6', name: '国家匹配度', description: '目标采购国匹配程度', max_score: 25, type: 'rule' },
      { id: 'd7', name: '产品匹配度', description: '关键词语义相似度', max_score: 35, type: 'llm' },
      { id: 'd8', name: '公司规模', description: '员工数量区间判断', max_score: 20, type: 'rule' },
      { id: 'd9', name: '联系人丰富度', description: '有效邮箱联系人数量', max_score: 20, type: 'rule' },
    ],
  },
];

interface GradeThreshold {
  grade: 'S' | 'A' | 'B' | 'C' | 'D';
  is_special: boolean;   // S 级用精准来源判断，不用分值
  min_score: number;
  max_score: number;
  desc: string;
}

const DEFAULT_THRESHOLDS: GradeThreshold[] = [
  { grade: 'S', is_special: false, min_score: 90,  max_score: 100, desc: '精准客户' },
  { grade: 'A', is_special: false, min_score: 80,  max_score: 89,  desc: '优质' },
  { grade: 'B', is_special: false, min_score: 60,  max_score: 79,  desc: '良好' },
  { grade: 'C', is_special: false, min_score: 40,  max_score: 59,  desc: '一般' },
  { grade: 'D', is_special: false, min_score: 0,   max_score: 39,  desc: '低优先' },
];

const GRADE_COLORS: Record<string, string> = {
  S: 'gold', A: 'green', B: 'blue', C: 'orange', D: 'default',
};

function TemplateEditor({ template, onClose }: { template: ScoringTemplate; onClose: () => void }) {
  const [dimensions, setDimensions] = useState<Dimension[]>(template.dimensions);
  const [thresholds, setThresholds] = useState<GradeThreshold[]>(DEFAULT_THRESHOLDS);

  const updateThreshold = (grade: string, field: 'min_score' | 'max_score', val: number | null) => {
    setThresholds(prev => prev.map(t => t.grade === grade ? { ...t, [field]: val ?? 0 } : t));
  };

  const addDimension = () => {
    setDimensions(prev => [...prev, {
      id: `new_${Date.now()}`,
      name: '',
      description: '',
      max_score: 10,
      type: 'rule',
    }]);
  };

  const removeDimension = (id: string) => {
    setDimensions(prev => prev.filter(d => d.id !== id));
  };

  const totalScore = dimensions.reduce((sum, d) => sum + d.max_score, 0);

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div>
        <Title level={5}>维度配置</Title>
        <Table
          rowKey="id"
          dataSource={dimensions}
          size="small"
          pagination={false}
          columns={[
            {
              title: '维度名称', dataIndex: 'name', width: 140,
              render: (v: string, r) => (
                <Input
                  value={v}
                  size="small"
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDimensions(prev => prev.map(d => d.id === r.id ? { ...d, name: e.target.value } : d))}
                />
              ),
            },
            {
              title: '规则描述', dataIndex: 'description',
              render: (v: string, r) => (
                <Input
                  value={v}
                  size="small"
                  onChange={(e: React.ChangeEvent<HTMLInputElement>) => setDimensions(prev => prev.map(d => d.id === r.id ? { ...d, description: e.target.value } : d))}
                />
              ),
            },
            {
              title: '满分', dataIndex: 'max_score', width: 80,
              render: (v, r) => (
                <InputNumber
                  value={v}
                  min={1}
                  max={100}
                  size="small"
                  style={{ width: 70 }}
                  onChange={(val) => setDimensions(prev => prev.map(d => d.id === r.id ? { ...d, max_score: val ?? 10 } : d))}
                />
              ),
            },
            {
              title: '评分方式', dataIndex: 'type', width: 120,
              render: (v, r) => (
                <Select
                  value={v}
                  size="small"
                  style={{ width: 110 }}
                  onChange={(val) => setDimensions(prev => prev.map(d => d.id === r.id ? { ...d, type: val } : d))}
                >
                  <Option value="rule">纯规则</Option>
                  <Option value="llm"><RobotOutlined /> LLM辅助</Option>
                </Select>
              ),
            },
            {
              title: '', width: 60,
              render: (_, r) => (
                <Popconfirm title="确认删除此维度？" onConfirm={() => removeDimension(r.id)}>
                  <Button type="link" size="small" danger>删除</Button>
                </Popconfirm>
              ),
            },
          ]}
          footer={() => (
            <Space style={{ justifyContent: 'space-between', width: '100%' }}>
              <Button size="small" icon={<PlusOutlined />} onClick={addDimension}>添加维度</Button>
              <Text type="secondary">总分上限: {totalScore}</Text>
            </Space>
          )}
        />
      </div>

      <div>
        <Title level={5}>评级区间配置</Title>
        <Table
          rowKey="grade"
          dataSource={thresholds}
          size="small"
          pagination={false}
          columns={[
            {
              title: '评级', dataIndex: 'grade', width: 70,
              render: (g) => <Tag color={GRADE_COLORS[g]}>{g}</Tag>,
            },
            {
              title: '最低分', dataIndex: 'min_score', width: 110,
              render: (v, r) => (
                <InputNumber
                  value={v}
                  min={0}
                  max={100}
                  size="small"
                  style={{ width: 80 }}
                  onChange={(val) => updateThreshold(r.grade, 'min_score', val)}
                />
              ),
            },
            {
              title: '最高分', dataIndex: 'max_score', width: 110,
              render: (v, r) => r.grade === 'S'
                ? <Text type="secondary">100（上限）</Text>
                : (
                  <InputNumber
                    value={v}
                    min={0}
                    max={100}
                    size="small"
                    style={{ width: 80 }}
                    onChange={(val) => updateThreshold(r.grade, 'max_score', val)}
                  />
                ),
            },
            {
              title: '说明',
              render: (_, r) => (
                <Space size={4}>
                  <Text type="secondary" style={{ fontSize: 12 }}>{r.desc}</Text>
                  {r.grade === 'S' && (
                    <Tag color="gold" style={{ fontSize: 11 }}>励销云来源自动打标</Tag>
                  )}
                </Space>
              ),
            },
          ]}
        />
        <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
          确保各级分值段连续覆盖 0–100，D 级最低分固定为 0。
        </Text>
      </div>

      <Alert
        type="warning"
        showIcon
        message="修改仅影响新创建的租户，已有租户保持快照版本"
      />

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8 }}>
        <Button onClick={onClose}>取消</Button>
        <Button type="primary" onClick={() => { message.success('模板已保存'); onClose(); }}>保存</Button>
      </div>
    </Space>
  );
}

export function Component() {
  const [editingTemplate, setEditingTemplate] = useState<ScoringTemplate | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [industryFilter, setIndustryFilter] = useState<string | undefined>(undefined);

  const filtered = industryFilter
    ? MOCK_TEMPLATES.filter((t) => t.industry === industryFilter)
    : MOCK_TEMPLATES;

  const columns: ColumnsType<ScoringTemplate> = [
    { title: '行业', dataIndex: 'industry', render: (v) => <Tag color="blue">{v}</Tag> },
    { title: '维度数量', dataIndex: 'dimension_count', render: (n) => `${n} 个维度` },
    { title: '状态', dataIndex: 'is_active', render: (v) => <Switch checked={v} size="small" onChange={() => message.info('状态已更新')} /> },
    { title: '创建时间', dataIndex: 'created_at' },
    {
      title: '操作', width: 130,
      render: (_, record) => (
        <Space>
          <Button type="link" size="small" icon={<EditOutlined />} onClick={() => { setEditingTemplate(record); setDrawerOpen(true); }}>
            编辑
          </Button>
          <Button type="link" size="small" icon={<CopyOutlined />} onClick={() => message.success('模板已复制')}>
            复制
          </Button>
        </Space>
      ),
    },
  ];

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
        <Text>行业筛选：</Text>
        <Select
          placeholder="全部行业"
          style={{ width: 160 }}
          allowClear
          value={industryFilter}
          onChange={setIndustryFilter}
        >
          <Option value="PCB">PCB</Option>
          <Option value="电子元器件">电子元器件</Option>
        </Select>
        <Button type="primary" icon={<PlusOutlined />} style={{ marginLeft: 'auto' }}>
          新建模板
        </Button>
      </div>

      <Table rowKey="id" columns={columns} dataSource={filtered} size="middle" pagination={false} />

      <Drawer
        title={`编辑评分模板 — ${editingTemplate?.industry}`}
        width={720}
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        footer={null}
      >
        {editingTemplate && (
          <TemplateEditor template={editingTemplate} onClose={() => setDrawerOpen(false)} />
        )}
      </Drawer>
    </>
  );
}

Component.displayName = 'ScoringTemplatesPage';
