import { useState } from 'react';
import {
  Card,
  Table,
  Input,
  Button,
  Space,
  Typography,
  Tag,
  Alert,
  message,
} from 'antd';
import {
  PlusOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';

const { Text, Title } = Typography;

interface SeniorityTier {
  id: string;
  grade: 'A' | 'B' | 'C' | 'D';
  label: string;
  keywords: string[];
}

interface PriorityDept {
  id: string;
  name: string;
}

const INITIAL_TIERS: SeniorityTier[] = [
  { id: 't1', grade: 'A', label: '核心决策层', keywords: ['Purchasing Director', 'CPO', 'Head of Procurement', '采购总监', '供应链总监'] },
  { id: 't2', grade: 'B', label: '采购执行层', keywords: ['Purchasing Manager', 'Procurement Manager', '采购经理', 'Sourcing Manager'] },
  { id: 't3', grade: 'C', label: '采购专员', keywords: ['Purchasing Engineer', 'Buyer', '采购专员', '采购工程师'] },
  { id: 't4', grade: 'D', label: '其他相关岗', keywords: ['Supply Chain', 'Operations', '供应链', '运营'] },
];

const GRADE_COLOR: Record<string, string> = { A: 'gold', B: 'green', C: 'blue', D: 'default' };

const INITIAL_DEPTS: PriorityDept[] = [
  { id: 'd1', name: 'Purchasing / Procurement' },
  { id: 'd2', name: 'Supply Chain' },
  { id: 'd3', name: 'Engineering / R&D' },
];

function TierKeywordEditor({ keywords, onChange }: {
  keywords: string[];
  onChange: (kw: string[]) => void;
}) {
  const [inputVal, setInputVal] = useState('');

  const add = () => {
    const trimmed = inputVal.trim();
    if (!trimmed || keywords.includes(trimmed)) return;
    onChange([...keywords, trimmed]);
    setInputVal('');
  };

  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
      {keywords.map((kw) => (
        <Tag
          key={kw}
          closable
          onClose={() => onChange(keywords.filter((k) => k !== kw))}
          style={{ fontSize: 12 }}
        >
          {kw}
        </Tag>
      ))}
      <Input
        size="small"
        value={inputVal}
        onChange={(e) => setInputVal(e.target.value)}
        onPressEnter={add}
        onBlur={add}
        placeholder="+ 添加"
        style={{ width: 80 }}
      />
    </div>
  );
}

export function Component() {
  const [tiers, setTiers] = useState<SeniorityTier[]>(INITIAL_TIERS);
  const [depts, setDepts] = useState<PriorityDept[]>(INITIAL_DEPTS);
  const [newDept, setNewDept] = useState('');

  const updateTierKeywords = (id: string, keywords: string[]) => {
    setTiers((prev) => prev.map((t) => t.id === id ? { ...t, keywords } : t));
  };

  const addDept = () => {
    const trimmed = newDept.trim();
    if (!trimmed) return;
    setDepts((prev) => [...prev, { id: `d${Date.now()}`, name: trimmed }]);
    setNewDept('');
  };

  const removeDept = (id: string) => {
    setDepts((prev) => prev.filter((d) => d.id !== id));
  };

  const handleSave = () => message.success('触达规则已保存');

  const tierCols: ColumnsType<SeniorityTier> = [
    {
      title: '职级',
      dataIndex: 'grade',
      width: 60,
      render: (v: string) => <Tag color={GRADE_COLOR[v]}>{v}级</Tag>,
    },
    {
      title: '层级描述',
      dataIndex: 'label',
      width: 120,
      render: (v) => <Text strong style={{ fontSize: 13 }}>{v}</Text>,
    },
    {
      title: '职位关键词（含此关键词的联系人归为此层级）',
      dataIndex: 'keywords',
      render: (kw, r) => (
        <TierKeywordEditor
          keywords={kw}
          onChange={(updated) => updateTierKeywords(r.id, updated)}
        />
      ),
    },
  ];

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Title level={5} style={{ marginBottom: 4 }}>触达规则</Title>
          <Text type="secondary">配置联系人职级判定和优先触达部门</Text>
        </div>
        <Button type="primary" onClick={handleSave}>保存配置</Button>
      </div>

      <Alert
        type="info"
        showIcon
        message="每家公司仅向职级最高的 1 位联系人发送邮件。收到回复后自动停止该公司的后续序列。规则变更不影响已加入发送计划的联系人。"
      />

      {/* 职级层级 */}
      <Card title="联系人职级层级" size="small">
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
          系统根据联系人职位头衔匹配关键词，判定其所属层级。同一公司中自动优先选择层级最高的联系人。
        </Text>
        <Table
          rowKey="id"
          columns={tierCols}
          dataSource={tiers}
          size="small"
          pagination={false}
        />
      </Card>

      {/* 优先部门 */}
      <Card title="优先触达部门" size="small">
        <Text type="secondary" style={{ fontSize: 12, display: 'block', marginBottom: 12 }}>
          只有属于以下部门的联系人才会被纳入触达范围（留空则不限制部门）
        </Text>
        <Space wrap style={{ marginBottom: 12 }}>
          {depts.map((d) => (
            <Tag
              key={d.id}
              closable
              onClose={() => removeDept(d.id)}
              style={{ fontSize: 13, padding: '2px 8px' }}
              color="cyan"
            >
              {d.name}
            </Tag>
          ))}
        </Space>
        <Space>
          <Input
            value={newDept}
            onChange={(e) => setNewDept(e.target.value)}
            onPressEnter={addDept}
            placeholder="输入部门名称"
            style={{ width: 220 }}
            size="small"
          />
          <Button size="small" icon={<PlusOutlined />} onClick={addDept}>添加</Button>
        </Space>
      </Card>
    </Space>
  );
}

Component.displayName = 'ContactRulesSettingsPage';
