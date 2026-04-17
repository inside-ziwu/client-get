import { useState } from 'react';
import {
  Card,
  Input,
  Button,
  Tag,
  Space,
  Typography,
  Alert,
  Tooltip,
  Popconfirm,
  message,
} from 'antd';
import {
  PlusOutlined,
  CloseOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';

const { Text, Title } = Typography;

interface KeywordGroup {
  key: string;
  label: string;
  description: string;
  keywords: string[];
}

const INITIAL_GROUPS: KeywordGroup[] = [
  {
    key: 'product',
    label: '产品关键词',
    description: '描述您生产的产品，用于匹配采购此类产品的目标客户',
    keywords: ['PCB', 'printed circuit board', 'FPC', 'HDI board', 'rigid-flex PCB', 'PCBA', 'multilayer PCB'],
  },
  {
    key: 'industry',
    label: '行业关键词',
    description: '描述目标客户所在行业，用于数据源采集和情报推送',
    keywords: ['电子制造', '消费电子', '汽车电子', '工业自动化', '通信设备', '医疗设备'],
  },
  {
    key: 'exclude',
    label: '排除关键词',
    description: '含有这些词的公司将被过滤，避免触达非目标客户',
    keywords: ['招聘', 'jobs', 'hiring', 'careers', '培训'],
  },
];

function KeywordGroupCard({ group, onChange }: {
  group: KeywordGroup;
  onChange: (keywords: string[]) => void;
}) {
  const [inputVal, setInputVal] = useState('');
  const [inputVisible, setInputVisible] = useState(false);

  const handleAdd = () => {
    const trimmed = inputVal.trim();
    if (!trimmed) return;
    if (group.keywords.includes(trimmed)) {
      message.warning('关键词已存在');
      return;
    }
    onChange([...group.keywords, trimmed]);
    setInputVal('');
    setInputVisible(false);
  };

  const handleRemove = (kw: string) => {
    onChange(group.keywords.filter((k) => k !== kw));
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter') handleAdd();
    if (e.key === 'Escape') { setInputVisible(false); setInputVal(''); }
  };

  return (
    <Card
      size="small"
      title={
        <Space>
          <Text strong>{group.label}</Text>
          <Tooltip title={group.description}>
            <InfoCircleOutlined style={{ color: '#999', fontSize: 13 }} />
          </Tooltip>
          <Tag>{group.keywords.length}</Tag>
        </Space>
      }
      style={{ marginBottom: 16 }}
    >
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {group.keywords.map((kw) => (
          <Tag
            key={kw}
            closable
            onClose={() => handleRemove(kw)}
            closeIcon={<CloseOutlined />}
            style={{ fontSize: 13, padding: '2px 8px' }}
            color={group.key === 'exclude' ? 'default' : 'blue'}
          >
            {kw}
          </Tag>
        ))}
        {inputVisible ? (
          <Input
            autoFocus
            size="small"
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleAdd}
            style={{ width: 140 }}
            placeholder="输入后按回车"
          />
        ) : (
          <Tag
            style={{ cursor: 'pointer', borderStyle: 'dashed' }}
            onClick={() => setInputVisible(true)}
            icon={<PlusOutlined />}
          >
            添加关键词
          </Tag>
        )}
      </div>
    </Card>
  );
}

export function Component() {
  const [groups, setGroups] = useState<KeywordGroup[]>(INITIAL_GROUPS);

  const handleGroupChange = (key: string, keywords: string[]) => {
    setGroups((prev) => prev.map((g) => g.key === key ? { ...g, keywords } : g));
  };

  const handleSave = () => {
    message.success('关键词已保存，将在下次采集周期（约24小时）生效');
    // saved state handled via message feedback
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Title level={5} style={{ marginBottom: 4 }}>关键词管理</Title>
          <Text type="secondary">关键词用于数据源采集和客户匹配，修改后将在下一采集周期生效</Text>
        </div>
        <Popconfirm
          title="保存关键词"
          description="修改将在下次采集周期（约24小时）后生效，确认保存？"
          onConfirm={handleSave}
        >
          <Button type="primary">保存配置</Button>
        </Popconfirm>
      </div>

      <Alert
        type="info"
        showIcon
        message="关键词变更在下次数据采集周期（每天凌晨2点）后生效，不影响当前已采集数据。建议修改后等待1-2天查看效果。"
      />

      {groups.map((group) => (
        <KeywordGroupCard
          key={group.key}
          group={group}
          onChange={(kw) => handleGroupChange(group.key, kw)}
        />
      ))}

      <Card size="small" style={{ background: '#fafafa' }}>
        <Space direction="vertical" size={4}>
          <Text strong style={{ fontSize: 12 }}>填写建议</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>• 产品关键词尽量包含中英文，提升跨语言匹配率</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>• 避免填写过于宽泛的词（如"电子""工厂"），会导致大量不相关客户</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>• 排除关键词可过滤招聘、培训类公司，减少无效数据</Text>
        </Space>
      </Card>
    </Space>
  );
}

Component.displayName = 'KeywordsSettingsPage';
