import { useEffect, useMemo, useState } from 'react';
import { Alert, Button, Card, Form, Input, InputNumber, Space, Table, Typography, message } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { createAdminApi, createApiClient, type WarmupRuleLevel, type WarmupRules as WarmupRulesType } from '@shared/api';

const { Title, Text } = Typography;
const adminApi = createAdminApi(createApiClient('admin'));

export function Component() {
  const [form] = Form.useForm<WarmupRulesType>();
  const [levels, setLevels] = useState<WarmupRuleLevel[]>([]);
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
          form.setFieldsValue({
            name: rule.name,
            min_observation_emails: rule.min_observation_emails,
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

  const onSave = async () => {
    try {
      const values = await form.validateFields();
      setSaving(true);
      await adminApi.warmupRules.update({
        ...values,
        levels,
      });
      message.success('预热规则已保存');
    } catch {
      message.error('保存失败');
    } finally {
      setSaving(false);
    }
  };

  const columns = useMemo<ColumnsType<WarmupRuleLevel>>(
    () => [
      { title: '档位', dataIndex: 'level', width: 80 },
      {
        title: '每日上限',
        dataIndex: 'daily_limit',
        render: (value, record) => (
          <InputNumber
            min={1}
            value={value}
            onChange={(next) =>
              setLevels((prev) =>
                prev.map((item) => (item.level === record.level ? { ...item, daily_limit: next ?? item.daily_limit } : item)),
              )
            }
          />
        ),
      },
      {
        title: '最少停留天数',
        dataIndex: 'min_stay_days',
        render: (value, record) => (
          <InputNumber
            min={1}
            value={value}
            onChange={(next) =>
              setLevels((prev) =>
                prev.map((item) => (item.level === record.level ? { ...item, min_stay_days: next ?? item.min_stay_days } : item)),
              )
            }
          />
        ),
      },
    ],
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

      <Card loading={loading} title="规则配置" extra={<Button type="primary" loading={saving} onClick={onSave} disabled={Boolean(loadError)}>保存</Button>}>
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="规则名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="min_observation_emails" label="最小观察样本数" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="bounce_alert_rate" label="退信报警阈值" rules={[{ required: true }]}>
            <InputNumber min={0} max={1} step={0.001} style={{ width: '100%' }} />
          </Form.Item>
          <Table rowKey="level" columns={columns} dataSource={levels} pagination={false} />
        </Form>
      </Card>
    </Space>
  );
}

Component.displayName = 'WarmupRulesPage';
