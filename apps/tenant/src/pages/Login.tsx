import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Button, Card, Form, Input, Typography, message } from 'antd';
import { createApiClient, createTenantApi } from '@shared/api';
import { useAuthStore } from '@shared/hooks';

const { Title } = Typography;
const tenantApi = createTenantApi(createApiClient('tenant'));

export function Component() {
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);
  const [loading, setLoading] = React.useState(false);

  const onFinish = async (values: { slug: string; email: string; password: string }) => {
    setLoading(true);
    try {
      const response = await tenantApi.auth.login(values);
      setToken(response.data.data.access_token);
      const me = (await tenantApi.auth.me()).data.data;
      message.success('登录成功');
      navigate(me.must_change_pwd || me.needs_onboarding ? '/onboarding' : '/', { replace: true });
    } catch {
      message.error('登录失败，请检查 slug、账号密码或接口状态');
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
      <Card style={{ width: '100%', maxWidth: 440 }} styles={{ body: { padding: 28 } }}>
        <Title level={3} style={{ marginTop: 0, marginBottom: 8, textAlign: 'center' }}>
          ClientGet Tenant
        </Title>
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 20 }}
          message="请输入租户 slug 后再登录，系统会直接调用真实 tenant 登录接口。"
        />
        <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item
            name="slug"
            label="租户 Slug"
            rules={[{ required: true, message: '请输入租户 slug' }]}
          >
            <Input placeholder="tenant-slug" autoComplete="off" />
          </Form.Item>
          <Form.Item
            name="email"
            label="邮箱"
            rules={[{ required: true, message: '请输入邮箱' }]}
          >
            <Input placeholder="user@example.com" autoComplete="email" />
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
