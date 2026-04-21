import { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Descriptions,
  Form,
  Input,
  Result,
  Space,
  Steps,
  Tag,
  Typography,
  message,
} from 'antd';
import {
  ArrowLeftOutlined,
  ArrowRightOutlined,
  CheckCircleOutlined,
  LockOutlined,
  StarOutlined,
  TagsOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createApiClient,
  createTenantApi,
  queryKeys,
  type ContactRules,
  type ContactRuleSet,
  type Keyword,
  type TenantScoringTemplate,
} from '@shared/api';

const { Text, Paragraph } = Typography;

const api = createTenantApi(createApiClient('tenant'));

function pickActiveTemplate(items: TenantScoringTemplate[]): TenantScoringTemplate | null {
  return items.find((item) => item.is_active) ?? items[0] ?? null;
}

function pickActiveRule(items: ContactRules[]): ContactRules | null {
  return items.find((item) => item.is_active) ?? items[0] ?? null;
}

const STEP_DEFS = [
  { title: '修改密码', icon: <LockOutlined />, required: true },
  { title: '采集关键词', icon: <TagsOutlined />, required: true },
  { title: '评分规则', icon: <StarOutlined />, required: false },
  { title: '联系人规则', icon: <TeamOutlined />, required: false },
  { title: '完成', icon: <CheckCircleOutlined />, required: false },
];

function StepPassword({
  onSuccess,
  onSubmitReady,
}: {
  onSuccess: () => void;
  onSubmitReady: (submit: () => void) => void;
}) {
  const [form] = Form.useForm();
  const changePasswordMutation = useMutation({
    mutationFn: (values: { old_password: string; new_password: string }) => api.auth.changePassword(values),
    onSuccess: () => {
      message.success('密码已修改');
      form.resetFields();
      onSuccess();
    },
    onError: () => message.error('密码修改失败，请检查输入后重试'),
  });

  useEffect(() => {
    onSubmitReady(() => form.submit());
  }, [form, onSubmitReady]);

  return (
    <div style={{ maxWidth: 440 }}>
      <Alert
        type="warning"
        showIcon
        message="首次登录必须修改初始密码"
        style={{ marginBottom: 24 }}
      />
      <Form
        layout="vertical"
        form={form}
        onFinish={(values) => changePasswordMutation.mutate(values)}
      >
        <Form.Item
          name="old_password"
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
            { min: 8, message: '密码至少 8 位' },
          ]}
        >
          <Input.Password placeholder="至少 8 位，包含字母和数字" />
        </Form.Item>
        <Form.Item
          name="confirm_password"
          label="确认新密码"
          dependencies={['new_password']}
          rules={[
            { required: true, message: '请再次输入新密码' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('new_password') === value) return Promise.resolve();
                return Promise.reject(new Error('两次输入的密码不一致'));
              },
            }),
          ]}
        >
          <Input.Password placeholder="再次输入新密码" />
        </Form.Item>
        <Button
          type="primary"
          htmlType="submit"
          loading={changePasswordMutation.isPending}
        >
          确认修改
        </Button>
      </Form>
    </div>
  );
}

function StepKeywords({
  keywords,
  onAdd,
  onRemove,
}: {
  keywords: Keyword[];
  onAdd: (keyword: string) => void;
  onRemove: (id: string) => void;
}) {
  const [inputVal, setInputVal] = useState('');

  return (
    <div style={{ maxWidth: 640 }}>
      <Paragraph type="secondary">
        关键词用于筛选与你产品相关的目标客户。这里直接读取和写入真实关键词接口。
      </Paragraph>

      <Card size="small" style={{ marginBottom: 16 }}>
        <Space.Compact style={{ width: '100%' }}>
          <Input
            value={inputVal}
            onChange={(e) => setInputVal(e.target.value)}
            placeholder="输入关键词后添加"
            onPressEnter={() => {
              const value = inputVal.trim();
              if (!value) return;
              onAdd(value);
              setInputVal('');
            }}
          />
          <Button
            type="primary"
            onClick={() => {
              const value = inputVal.trim();
              if (!value) return;
              onAdd(value);
              setInputVal('');
            }}
          >
            添加
          </Button>
        </Space.Compact>
      </Card>

      <div style={{ marginBottom: 20 }}>
        <Text strong style={{ display: 'block', marginBottom: 8 }}>
          当前关键词
          <Tag style={{ marginLeft: 8 }}>{keywords.length}</Tag>
        </Text>
        {keywords.length === 0 ? (
          <Alert type="warning" showIcon message="至少添加 1 个关键词后才能继续" />
        ) : (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {keywords.map((item) => (
              <Tag
                key={item.id}
                closable
                onClose={() => onRemove(item.id)}
                color="blue"
                style={{ fontSize: 13 }}
              >
                {item.keyword}
              </Tag>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StepScoring({ template }: { template?: TenantScoringTemplate | null }) {
  return (
    <div style={{ maxWidth: 680 }}>
      <Paragraph type="secondary">
        评分模板已从后端加载。当前页面只做预览，设置页可以进一步调整。
      </Paragraph>
      <Card size="small" style={{ marginBottom: 16 }}>
        <Space direction="vertical" style={{ width: '100%' }} size={10}>
          {(template?.dimensions ?? []).map((dim) => (
            <div key={dim.name} style={{ display: 'flex', justifyContent: 'space-between', gap: 12 }}>
              <div>
                <Text style={{ fontSize: 13 }}>{dim.name}</Text>
                <Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>{dim.criteria ?? '—'}</Text>
              </div>
              <Tag>{dim.weight}%</Tag>
            </div>
          ))}
          {(template?.dimensions?.length ?? 0) === 0 && (
            <Text type="secondary">暂无评分维度</Text>
          )}
        </Space>
      </Card>
      <Text type="secondary" style={{ fontSize: 12 }}>
        最后同步：{template?.updated_at ? new Date(template.updated_at).toLocaleString('zh-CN') : '—'}
      </Text>
    </div>
  );
}

function StepContactRules({ rules }: { rules?: ContactRules | null }) {
  const config: ContactRuleSet | undefined = rules?.rules;
  return (
    <div style={{ maxWidth: 680 }}>
      <Paragraph type="secondary">
        联系人触达规则已从后端加载。系统会据此控制发送频次和退订处理。
      </Paragraph>
      <Card size="small">
        <Descriptions column={2} size="small">
          <Descriptions.Item label="每日最大发送数">{config?.max_emails_per_prospect_per_day ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="每周最大发送数">{config?.max_emails_per_prospect_per_week ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="最小间隔（小时）">{config?.min_interval_hours ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="退信阈值">{config?.bounce_threshold ?? '—'}</Descriptions.Item>
          <Descriptions.Item label="遵守退订">{config?.respect_unsubscribe ? '是' : '否'}</Descriptions.Item>
          <Descriptions.Item label="最后同步">{rules ? new Date(rules.updated_at).toLocaleString('zh-CN') : '—'}</Descriptions.Item>
        </Descriptions>
      </Card>
      <Alert
        type="info"
        showIcon
        message="这些规则会直接影响后续发送行为。"
        style={{ marginTop: 16 }}
      />
    </div>
  );
}

function StepDone() {
  return (
    <Result
      status="success"
      title="配置完成，开始使用系统"
      subTitle="你的租户已完成基础设置，系统会在后续同步真实数据。"
      style={{ padding: '24px 0' }}
    />
  );
}

export function Component() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [current, setCurrent] = useState(0);
  const [passwordSubmit, setPasswordSubmit] = useState<(() => void) | null>(null);

  const keywordsQuery = useQuery<Keyword[]>({
    queryKey: queryKeys.keywords.list(),
    queryFn: async () => (await api.keywords.list()).data.data,
  });
  const scoringQuery = useQuery<TenantScoringTemplate | null>({
    queryKey: queryKeys.scoring.all(),
    queryFn: async () => pickActiveTemplate((await api.scoring.get()).data.data),
  });
  const rulesQuery = useQuery<ContactRules | null>({
    queryKey: queryKeys.contactRules.all(),
    queryFn: async () => pickActiveRule((await api.contactRules.get()).data.data),
  });

  const addKeywordMutation = useMutation({
    mutationFn: (keyword: string) => api.keywords.create({ keyword }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.keywords.list() });
      message.success('关键词已添加');
    },
    onError: () => message.error('添加关键词失败'),
  });

  const removeKeywordMutation = useMutation({
    mutationFn: (id: string) => api.keywords.delete(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.keywords.list() });
      message.success('关键词已删除');
    },
    onError: () => message.error('删除关键词失败'),
  });

  const completeMutation = useMutation({
    mutationFn: () => api.onboarding.complete(),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['tenant', 'auth', 'me'] });
      navigate('/dashboard', { replace: true });
    },
    onError: () => message.error('完成引导失败，请确认关键词已配置'),
  });

  const keywords = keywordsQuery.data ?? [];

  const canNext = () => {
    if (current === 1) return keywords.length > 0;
    return true;
  };

  const handleNext = () => {
    setCurrent((value) => Math.min(value + 1, STEP_DEFS.length - 1));
  };

  const handleStepOneSuccess = () => {
    handleNext();
  };

  const handleSkip = () => handleNext();

  const handleFinish = () => completeMutation.mutate();

  const stepItems = STEP_DEFS.map((step, index) => ({
    title: step.title,
    icon: step.icon,
    status: index < current ? 'finish' as const : index === current ? 'process' as const : 'wait' as const,
  }));

  const currentStep = STEP_DEFS[current]!;
  const isLast = current === STEP_DEFS.length - 1;
  const isSkippable = !currentStep.required && current > 1 && !isLast;

  const stepContents = [
    <StepPassword
      key="password"
      onSuccess={handleStepOneSuccess}
      onSubmitReady={setPasswordSubmit}
    />,
    <StepKeywords
      key="keywords"
      keywords={keywords}
      onAdd={(keyword) => addKeywordMutation.mutate(keyword)}
      onRemove={(id) => removeKeywordMutation.mutate(id)}
    />,
    <StepScoring key="scoring" template={scoringQuery.data} />,
    <StepContactRules key="contact" rules={rulesQuery.data} />,
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
      <div style={{
        width: '100%',
        maxWidth: 760,
        margin: '0 auto',
        display: 'flex',
        flexDirection: 'column',
        flex: 1,
        minHeight: 0,
      }}>
        <Steps current={current} items={stepItems} style={{ marginBottom: 20, flexShrink: 0 }} />

        <Card style={{ flexShrink: 0, overflow: 'auto', maxHeight: 'calc(100vh - 180px)', marginBottom: 16 }}>
          {stepContents[current]}
        </Card>

        <div style={{ flex: 1 }} />

        <div style={{ display: 'flex', justifyContent: 'space-between', flexShrink: 0 }}>
          <Button
            icon={<ArrowLeftOutlined />}
            disabled={current === 0}
            onClick={() => setCurrent((value) => Math.max(value - 1, 0))}
          >
            上一步
          </Button>
          <Space>
            {isSkippable && <Button onClick={handleSkip}>跳过此步</Button>}
            {isLast ? (
              <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleFinish} loading={completeMutation.isPending}>
                进入控制台
              </Button>
            ) : (
              <Button
                type="primary"
                icon={<ArrowRightOutlined />}
                disabled={!canNext()}
                onClick={current === 0 ? passwordSubmit ?? undefined : handleNext}
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
