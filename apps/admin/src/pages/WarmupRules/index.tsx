import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Collapse,
  Form,
  Input,
  InputNumber,
  Popconfirm,
  Space,
  Table,
  Typography,
  message,
} from 'antd';
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { createAdminApi, createApiClient, type WarmupRuleLevel, type WarmupRules as WarmupRulesType } from '@shared/api';

const { Title, Text } = Typography;
const adminApi = createAdminApi(createApiClient('admin'));

export function Component() {
  const [form] = Form.useForm<WarmupRulesType>();
  const [levels, setLevels] = useState<WarmupRuleLevel[]>([]);
  const [ruleId, setRuleId] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    const load = async () => {
      setLoading(true);
      try {
        const response = await adminApi.warmupRules.get();
        const rule = response.data.data[0];
        if (active) {
          if (!rule) {
            setLoadError('后台暂无预热规则，请先初始化后端配置');
            form.resetFields();
            setLevels([]);
            return;
          }
          setLoadError(null);
          setRuleId(rule.id);
          form.setFieldsValue({
            name: rule.name,
            min_observation_emails: rule.min_observation_emails ?? 20,
            bounce_alert_rate: rule.bounce_alert_rate,
          });
          setLevels(rule.levels ?? []);
        }
      } catch {
        if (active) {
          setLoadError('预热规则加载失败，请检查接口与配置初始化状态');
          form.resetFields();
          setLevels([]);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    void load();

    return () => {
      active = false;
    };
  }, [form]);

  const updateLevel = (level: number, field: keyof WarmupRuleLevel, value: number) => {
    setLevels((prev) =>
      prev.map((item) => (item.level === level ? { ...item, [field]: value } : item)),
    );
  };

  const addLevel = () => {
    const maxLevel = levels.length > 0 ? Math.max(...levels.map((l) => l.level)) : 0;
    const newLevel: WarmupRuleLevel = {
      level: maxLevel + 1,
      daily_limit: 50,
      min_stay_days: 7,
      min_delivery_rate: 0.95,
      max_bounce_rate: 0.02,
      max_complaint_rate: 0.001,
    };
    setLevels((prev) => [...prev, newLevel]);
  };

  const removeLevel = (level: number) => {
    setLevels((prev) => prev.filter((item) => item.level !== level));
  };

  const onSave = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      // form validation failed — ant design already highlights the fields
      return;
    }
    if (!ruleId) {
      message.error('规则 ID 丢失，请刷新页面后重试');
      return;
    }
    setSaving(true);
    try {
      await adminApi.warmupRules.update({
        ...values,
        id: ruleId,
        levels,
      });
      message.success('预热规则已保存');
    } catch (err: unknown) {
      const resp = (err as { response?: { data?: { message?: string } } })?.response?.data;
      message.error(resp?.message ?? '保存失败，请检查控制台');
      console.error('[WarmupRules] save error', err);
    } finally {
      setSaving(false);
    }
  };

  const columns = useMemo<ColumnsType<WarmupRuleLevel>>(
    () => [
      { title: '档位', dataIndex: 'level', width: 64, align: 'center' },
      {
        title: '每日上限',
        dataIndex: 'daily_limit',
        width: 110,
        render: (value, record) => (
          <InputNumber
            min={1}
            value={value}
            style={{ width: '100%' }}
            onChange={(next) => updateLevel(record.level, 'daily_limit', next ?? value)}
          />
        ),
      },
      {
        title: '最少停留天数',
        dataIndex: 'min_stay_days',
        width: 120,
        render: (value, record) => (
          <InputNumber
            min={1}
            value={value}
            style={{ width: '100%' }}
            onChange={(next) => updateLevel(record.level, 'min_stay_days', next ?? value)}
          />
        ),
      },
      {
        title: '最低送达率',
        dataIndex: 'min_delivery_rate',
        width: 120,
        render: (value, record) => (
          <InputNumber
            min={0}
            max={1}
            step={0.01}
            value={value}
            style={{ width: '100%' }}
            onChange={(next) => updateLevel(record.level, 'min_delivery_rate', next ?? value)}
          />
        ),
      },
      {
        title: '最高退信率',
        dataIndex: 'max_bounce_rate',
        width: 120,
        render: (value, record) => (
          <InputNumber
            min={0}
            max={1}
            step={0.001}
            value={value}
            style={{ width: '100%' }}
            onChange={(next) => updateLevel(record.level, 'max_bounce_rate', next ?? value)}
          />
        ),
      },
      {
        title: '最高投诉率',
        dataIndex: 'max_complaint_rate',
        width: 120,
        render: (value, record) => (
          <InputNumber
            min={0}
            max={1}
            step={0.0001}
            value={value}
            style={{ width: '100%' }}
            onChange={(next) => updateLevel(record.level, 'max_complaint_rate', next ?? value)}
          />
        ),
      },
      {
        title: '',
        width: 56,
        render: (_, record) => (
          <Popconfirm title="确认删除此档位？" onConfirm={() => removeLevel(record.level)}>
            <Button type="text" danger icon={<DeleteOutlined />} size="small" />
          </Popconfirm>
        ),
      },
    ],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [],
  );

  return (
    <Space direction="vertical" size="large" style={{ width: '100%' }}>
      <div>
        <Title level={4} style={{ marginBottom: 4 }}>
          预热规则
        </Title>
        <Text type="secondary">直接编辑并保存到后端。</Text>
      </div>

      <Alert
        type="warning"
        showIcon
        message="这里是全局配置，保存后会影响所有租户域名的预热策略。"
      />
      {loadError && <Alert type="error" showIcon message={loadError} />}

      <Card
        loading={loading}
        title="规则配置"
        extra={<Button type="primary" loading={saving} onClick={onSave} disabled={Boolean(loadError)}>保存</Button>}
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="规则名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="bounce_alert_rate" label="退信报警阈值" rules={[{ required: true }]}>
            <InputNumber min={0} max={1} step={0.001} style={{ width: 200 }} />
          </Form.Item>

          <Collapse
            ghost
            size="small"
            style={{ marginBottom: 16 }}
            items={[{
              key: 'advanced',
              label: <Text type="secondary" style={{ fontSize: 13 }}>高级参数（通常无需修改）</Text>,
              children: (
                <Form.Item
                  name="min_observation_emails"
                  label="最小观察样本数"
                  tooltip="档位评估所需的最低邮件发送量，用于保证统计置信度，默认 20 封"
                >
                  <InputNumber min={1} defaultValue={20} style={{ width: 200 }} />
                </Form.Item>
              ),
            }]}
          />

          <div style={{ marginBottom: 8, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Text strong>预热档位</Text>
            <Button size="small" icon={<PlusOutlined />} onClick={addLevel}>
              新增档位
            </Button>
          </div>
          <Table
            rowKey="level"
            columns={columns}
            dataSource={levels}
            pagination={false}
            size="small"
            scroll={{ x: true }}
            locale={{ emptyText: '暂无档位，点击"新增档位"创建' }}
          />
          <Text type="secondary" style={{ fontSize: 12, marginTop: 8, display: 'block' }}>
            档位升级需同时满足：停留天数 ≥ 最少停留天数 AND 送达率 ≥ 最低送达率 AND 退信率 ≤ 最高退信率 AND 投诉率 ≤ 最高投诉率
          </Text>
        </Form>
      </Card>
    </Space>
  );
}

Component.displayName = 'WarmupRulesPage';
