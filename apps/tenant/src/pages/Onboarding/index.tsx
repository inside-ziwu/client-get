import { useState } from 'react';
import {
  Steps,
  Button,
  Form,
  Input,
  Space,
  Typography,
  Tag,
  Card,
  Alert,
  Result,
  message,
} from 'antd';
import {
  LockOutlined,
  TagsOutlined,
  StarOutlined,
  TeamOutlined,
  CheckCircleOutlined,
  ArrowRightOutlined,
  ArrowLeftOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';

const { Text, Paragraph } = Typography;

const STEP_DEFS = [
  { title: '修改密码', icon: <LockOutlined />, required: true },
  { title: '采集关键词', icon: <TagsOutlined />, required: true },
  { title: '评分规则', icon: <StarOutlined />, required: false },
  { title: '联系人规则', icon: <TeamOutlined />, required: false },
  { title: '完成', icon: <CheckCircleOutlined />, required: false },
];

const SUGGESTED_KEYWORDS = ['PCB', 'printed circuit board', 'FPC', 'HDI', 'PCBA', '电路板', '线路板', 'multilayer PCB'];

function StepPassword() {
  return (
    <div style={{ maxWidth: 400 }}>
      <Alert
        type="warning"
        showIcon
        message="首次登录必须修改初始密码"
        style={{ marginBottom: 24 }}
      />
      <Form layout="vertical">
        <Form.Item
          name="current_password"
          label="初始密码"
          rules={[{ required: true, message: '请输入初始密码' }]}
        >
          <Input.Password placeholder="输入管理员提供的初始密码" />
        </Form.Item>
        <Form.Item
          name="new_password"
          label="新密码"
          rules={[
            { required: true, message: '请设置新密码' },
            { min: 8, message: '密码至少8位' },
          ]}
        >
          <Input.Password placeholder="至少8位，包含字母和数字" />
        </Form.Item>
        <Form.Item
          name="confirm_password"
          label="确认新密码"
          rules={[{ required: true, message: '请再次输入新密码' }]}
        >
          <Input.Password placeholder="再次输入新密码" />
        </Form.Item>
      </Form>
    </div>
  );
}

function StepKeywords({ keywords, onChange }: {
  keywords: string[];
  onChange: (kw: string[]) => void;
}) {
  const [inputVal, setInputVal] = useState('');

  const addKeyword = (kw: string) => {
    const trimmed = kw.trim();
    if (!trimmed || keywords.includes(trimmed)) return;
    onChange([...keywords, trimmed]);
    setInputVal('');
  };

  const removeKeyword = (kw: string) => {
    onChange(keywords.filter((k) => k !== kw));
  };

  const toggleSuggested = (kw: string) => {
    if (keywords.includes(kw)) removeKeyword(kw);
    else addKeyword(kw);
  };

  return (
    <div style={{ maxWidth: 560 }}>
      <Paragraph type="secondary">
        关键词用于从海量数据中筛选与您产品相关的目标客户。请填写描述您产品的核心词汇。
      </Paragraph>

      <div style={{ marginBottom: 20 }}>
        <Text strong style={{ display: 'block', marginBottom: 8 }}>推荐关键词（点击添加 / 再次点击移除）</Text>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {SUGGESTED_KEYWORDS.map((kw) => (
            <Tag
              key={kw}
              color={keywords.includes(kw) ? 'blue' : 'default'}
              style={{ cursor: 'pointer', fontSize: 13, userSelect: 'none' }}
              onClick={() => toggleSuggested(kw)}
            >
              {keywords.includes(kw) ? `✓ ${kw}` : `+ ${kw}`}
            </Tag>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 20 }}>
        <Text strong style={{ display: 'block', marginBottom: 8 }}>
          已选关键词
          <Tag style={{ marginLeft: 8 }}>{keywords.length}</Tag>
        </Text>
        {keywords.length === 0 ? (
          <Text type="secondary" style={{ fontSize: 13 }}>尚未选择任何关键词</Text>
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {keywords.map((kw) => (
              <Tag
                key={kw}
                closable
                onClose={() => removeKeyword(kw)}
                color="blue"
                style={{ fontSize: 13 }}
              >
                {kw}
              </Tag>
            ))}
          </div>
        )}
      </div>

      <Space>
        <Input
          value={inputVal}
          onChange={(e) => setInputVal(e.target.value)}
          onPressEnter={() => addKeyword(inputVal)}
          placeholder="自定义关键词，按回车添加"
          style={{ width: 260 }}
        />
        <Button onClick={() => addKeyword(inputVal)}>添加</Button>
      </Space>

      {keywords.length === 0 && (
        <Alert
          type="warning"
          showIcon
          message="至少需要1个关键词才能继续"
          style={{ marginTop: 16 }}
        />
      )}
    </div>
  );
}

function StepScoring() {
  return (
    <div style={{ maxWidth: 560 }}>
      <Paragraph type="secondary">
        平台已根据 PCB 行业特征预置了评分规则，开箱即用，无需立即配置。
      </Paragraph>
      <Card size="small" style={{ background: '#fafafa', marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size={10}>
          {[
            { name: '采购相关性', weight: 30, desc: '职位/描述含PCB采购关键词' },
            { name: '公司规模', weight: 25, desc: '员工数 / 营收规模' },
            { name: '近期活跃度', weight: 20, desc: '近90天采购记录/动态' },
            { name: '决策层联系人', weight: 15, desc: '是否有Purchasing/Sourcing职级联系人' },
            { name: '地区优先级', weight: 10, desc: '目标国家匹配程度' },
          ].map((d) => (
            <div key={d.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8 }}>
              <div>
                <Text style={{ fontSize: 13 }}>{d.name}</Text>
                <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>{d.desc}</Text>
              </div>
              <Tag style={{ flexShrink: 0 }}>{d.weight}%</Tag>
            </div>
          ))}
        </Space>
      </Card>
      <Text type="secondary" style={{ fontSize: 12 }}>
        如需调整权重和评级阈值，入门后前往 <Text strong style={{ fontSize: 12 }}>设置 → 评分配置</Text> 修改。
      </Text>
    </div>
  );
}

function StepContactRules() {
  return (
    <div style={{ maxWidth: 560 }}>
      <Paragraph type="secondary">
        系统根据联系人职位头衔判断其决策层级，每次触达自动选择公司中<Text strong>职级最高的1位联系人</Text>发送邮件，无需手动选择。
      </Paragraph>
      <Card size="small" style={{ background: '#fafafa', marginBottom: 16 }}>
        <Space direction="vertical" size={12} style={{ width: '100%' }}>
          <div>
            <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 6 }}>联系人职级（优先级从高到低）</Text>
            <Space direction="vertical" size={4}>
              {[
                { grade: 'A', label: '核心决策层', example: 'Purchasing Director、CPO、采购总监' },
                { grade: 'B', label: '采购执行层', example: 'Purchasing Manager、采购经理' },
                { grade: 'C', label: '采购专员', example: 'Buyer、Purchasing Engineer' },
                { grade: 'D', label: '其他相关岗', example: 'Supply Chain、Operations' },
              ].map((t) => (
                <div key={t.grade} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <Tag color={t.grade === 'A' ? 'gold' : t.grade === 'B' ? 'green' : t.grade === 'C' ? 'blue' : 'default'} style={{ width: 32, textAlign: 'center' }}>
                    {t.grade}级
                  </Tag>
                  <Text style={{ fontSize: 12, width: 80 }}>{t.label}</Text>
                  <Text type="secondary" style={{ fontSize: 12 }}>{t.example}</Text>
                </div>
              ))}
            </Space>
          </div>
          <div>
            <Text strong style={{ fontSize: 13, display: 'block', marginBottom: 4 }}>优先部门</Text>
            <Space>
              {['Purchasing / Procurement', 'Supply Chain', 'Engineering / R&D'].map((d) => (
                <Tag key={d} color="cyan">{d}</Tag>
              ))}
            </Space>
          </div>
        </Space>
      </Card>
      <Alert
        type="info"
        showIcon
        message="收到回复后自动停止该公司的后续序列邮件。"
        style={{ marginBottom: 12 }}
      />
      <Text type="secondary" style={{ fontSize: 12 }}>
        如需调整职级关键词或优先部门，入门后前往 <Text strong style={{ fontSize: 12 }}>设置 → 触达规则</Text> 修改。
      </Text>
    </div>
  );
}

function StepDone() {
  return (
    <Result
      status="success"
      title="配置完成，开始获客之旅！"
      subTitle="系统正在为您采集和筛选目标客户，通常需要24小时完成首次数据同步。"
      style={{ padding: '24px 0' }}
    />
  );
}

export function Component() {
  const navigate = useNavigate();
  const [current, setCurrent] = useState(0);
  const [keywords, setKeywords] = useState<string[]>(['PCB', 'printed circuit board']);

  const canNext = () => {
    if (current === 1) return keywords.length > 0;
    return true;
  };

  const handleNext = () => {
    if (current === 0) {
      message.success('密码已修改');
    }
    setCurrent((c) => c + 1);
  };

  const handleSkip = () => setCurrent((c) => c + 1);

  const handleFinish = () => navigate('/dashboard');

  const stepItems = STEP_DEFS.map((s, i) => ({
    title: s.title,
    icon: s.icon,
    status: i < current ? 'finish' as const : i === current ? 'process' as const : 'wait' as const,
  }));

  const currentStep = STEP_DEFS[current]!;
  const isLast = current === STEP_DEFS.length - 1;
  const isSkippable = !currentStep.required && current > 1 && !isLast;

  const stepContents = [
    <StepPassword key="password" />,
    <StepKeywords key="keywords" keywords={keywords} onChange={setKeywords} />,
    <StepScoring key="scoring" />,
    <StepContactRules key="contact" />,
    <StepDone key="done" />,
  ];

  return (
    <div style={{
      height: '100vh',
      background: '#f5f7fa',
      display: 'flex',
      flexDirection: 'column',
      padding: '24px',
      boxSizing: 'border-box',
    }}>
      {/* 居中约束容器，flex 列撑满剩余高度 */}
      <div style={{
        width: '100%',
        maxWidth: 720,
        margin: '0 auto',
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0,
      }}>
        {/* 步骤条 */}
        <Steps
          current={current}
          items={stepItems}
          style={{ marginBottom: 20, flexShrink: 0 }}
        />

        {/* 内容卡片：按内容自适应高度，超出时内部滚动，不撑满全屏 */}
        <Card style={{ flexShrink: 0, overflow: 'auto', maxHeight: 'calc(100vh - 180px)', marginBottom: 16 }}>
          {stepContents[current]}
        </Card>

        {/* 弹性垫片：将按钮推到底部 */}
        <div style={{ flex: 1 }} />

        {/* 导航按钮：始终可见 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', flexShrink: 0 }}>
          <Button
            icon={<ArrowLeftOutlined />}
            disabled={current === 0}
            onClick={() => setCurrent((c) => c - 1)}
          >
            上一步
          </Button>
          <Space>
            {isSkippable && (
              <Button onClick={handleSkip}>跳过此步</Button>
            )}
            {isLast ? (
              <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleFinish}>
                进入控制台
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<ArrowRightOutlined />}
                disabled={!canNext()}
                onClick={handleNext}
              >
                {current === 0 ? '确认修改' : '下一步'}
              </Button>
            )}
          </Space>
        </div>
      </div>
    </div>
  );
}

Component.displayName = 'OnboardingPage';
