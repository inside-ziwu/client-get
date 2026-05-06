import React from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Alert, Button, Card, Form, Input, Typography, message } from 'antd';
import { createApiClient, createTenantApi } from '@shared/api';
import { useAuthStore } from '@shared/hooks';

const { Title, Text } = Typography;
const tenantApi = createTenantApi(createApiClient('tenant'));

export function Component() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const slug = searchParams.get('slug') ?? '';
  const setToken = useAuthStore((s) => s.setToken);
  const [loading, setLoading] = React.useState(false);

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      const response = await tenantApi.auth.login({ slug, ...values });
      setToken(response.data.data.access_token);
      const me = (await tenantApi.auth.me()).data.data;
      message.success('登录成功');
      navigate(me.must_change_pwd || me.needs_onboarding ? '/onboarding' : '/', { replace: true });
    } catch {
      message.error('账号或密码错误，请重试');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        background: 'linear-gradient(135deg, #f7f9fc 0%, #eef4ff 100%)',
      }}
    >
      <Card style={{ width: '100%', maxWidth: 400 }} styles={{ body: { padding: 32 } }}>
        <Title level={3} style={{ marginTop: 0, marginBottom: 4, textAlign: 'center' }}>
          登录
        </Title>
        {slug && (
          <Text type="secondary" style={{ display: 'block', textAlign: 'center', marginBottom: 24 }}>
            {slug}
          </Text>
        )}
        {!slug && (
          <Alert
            type="error"
            showIcon
            title="无效的登录链接，请联系管理员获取正确的登录地址。"
            style={{ marginBottom: 20 }}
          />
        )}
        <Form layout="vertical" onFinish={onFinish} requiredMark={false} disabled={!slug}>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[{ required: true, message: '请输入邮箱' }]}
          >
            <Input placeholder="user@example.com" autoComplete="email" autoFocus />
          </Form.Item>
          <Form.Item
            name="password"
            label="密码"
            rules={[{ required: true, message: '请输入密码' }]}
          >
            <Input.Password placeholder="请输入密码" autoComplete="current-password" />
          </Form.Item>
          <Form.Item style={{ marginBottom: 0 }}>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}

Component.displayName = 'TenantLoginPage';
