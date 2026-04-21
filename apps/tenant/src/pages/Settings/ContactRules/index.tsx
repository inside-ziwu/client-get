import { useEffect } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Form,
  InputNumber,
  Space,
  Switch,
  Typography,
  message,
} from 'antd';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createApiClient, createTenantApi, queryKeys, type ContactRules, type ContactRuleSet } from '@shared/api';

const { Text, Title } = Typography;

const api = createTenantApi(createApiClient('tenant'));

function pickActiveRule(items: ContactRules[]): ContactRules | null {
  return items.find((item) => item.is_active) ?? items[0] ?? null;
}

export function Component() {
  const [form] = Form.useForm<ContactRuleSet>();
  const queryClient = useQueryClient();

  const rulesQuery = useQuery<ContactRules | null>({
    queryKey: queryKeys.contactRules.all(),
    queryFn: async () => pickActiveRule((await api.contactRules.get()).data.data),
  });

  useEffect(() => {
    if (rulesQuery.data) {
      form.setFieldsValue(rulesQuery.data.rules);
    } else {
      form.resetFields();
    }
  }, [rulesQuery.data, form]);

  const updateMutation = useMutation({
    mutationFn: (values: ContactRuleSet) => {
      if (!rulesQuery.data) {
        throw new Error('missing_contact_rule');
      }
      return api.contactRules.update(rulesQuery.data.id, {
        name: rulesQuery.data.name,
        rules: values,
      });
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.contactRules.all() });
      message.success('触达规则已保存');
    },
    onError: () => message.error('保存失败，请稍后重试'),
  });

  const handleSave = async () => {
    const values = await form.validateFields();
    updateMutation.mutate(values);
  };

  return (
    <Space direction="vertical" style={{ width: '100%' }} size="large">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 16, alignItems: 'flex-start' }}>
        <div>
          <Title level={5} style={{ marginBottom: 4 }}>触达规则</Title>
          <Text type="secondary">规则数据来自真实 API，读取的是当前启用规则集。</Text>
        </div>
        <Button type="primary" onClick={() => void handleSave()} loading={updateMutation.isPending} disabled={!rulesQuery.data}>
          保存配置
        </Button>
      </div>

      <Alert
        type="info"
        showIcon
        message="这些规则控制单个联系人发送频次、退订处理和退信阈值。修改会立即生效。"
      />

      <Card size="small">
        {!rulesQuery.isLoading && !rulesQuery.data ? (
          <Empty description="后台暂无联系人规则" />
        ) : (
          <Form<ContactRuleSet> layout="vertical" form={form}>
            <Space direction="vertical" size="middle" style={{ width: '100%' }}>
              <Form.Item
                name="max_emails_per_prospect_per_day"
                label="单联系人每日最大发送数"
                rules={[{ required: true, message: '请输入每日最大发送数' }]}
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="max_emails_per_prospect_per_week"
                label="单联系人每周最大发送数"
                rules={[{ required: true, message: '请输入每周最大发送数' }]}
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="min_interval_hours"
                label="同一联系人最小间隔（小时）"
                rules={[{ required: true, message: '请输入最小间隔小时数' }]}
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="bounce_threshold"
                label="退信阈值（次）"
                rules={[{ required: true, message: '请输入退信阈值' }]}
              >
                <InputNumber min={1} style={{ width: '100%' }} />
              </Form.Item>

              <Form.Item
                name="respect_unsubscribe"
                label="遵守退订"
                valuePropName="checked"
              >
                <Switch />
              </Form.Item>
            </Space>
          </Form>
        )}
      </Card>

      <Card size="small">
        <Space direction="vertical" size={4}>
          <Text strong>同步信息</Text>
          <Text type="secondary">最后同步：{rulesQuery.data ? new Date(rulesQuery.data.updated_at).toLocaleString('zh-CN') : '—'}</Text>
          <Text type="secondary">页面直接读写 `/api/v1/contact-rules` 的启用规则集，不再假设单对象接口。</Text>
        </Space>
      </Card>
    </Space>
  );
}

Component.displayName = 'ContactRulesSettingsPage';
