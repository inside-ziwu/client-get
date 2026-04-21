import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Alert, Button, Card, Form, Input, Typography, message } from 'antd';
import { createAdminApi, createApiClient } from '@shared/api';
import { useAuthStore } from '@shared/hooks';

const { Title, Text } = Typography;
const adminApi = createAdminApi(createApiClient('admin'));

export function Component() {
  const navigate = useNavigate();
  const setToken = useAuthStore((state) => state.setToken);
  const [loading, setLoading] = React.useState(false);

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      const response = await adminApi.auth.login(values);
      setToken(response.data.data.access_token);
      message.success('登录成功');
      navigate('/', { replace: true });
    } catch (error) {
      message.error('登录失败，请检查账号密码或接口状态');
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
        background: 'linear-gradient(135deg, #f5f7fb 0%, #eef2ff 100%)',
      }}
    >
      <Card style={{ width: '100%', maxWidth: 420 }} styles={{ body: { padding: 28 } }}>
        <Title level={3} style={{ marginTop: 0, marginBottom: 8 }}>
          ClientGet Admin
        </Title>
        <Text type="secondary">使用真实 API 登录后台管理系统</Text>

        <Alert
          type="info"
          showIcon
          style={{ marginTop: 20, marginBottom: 20 }}
          message="登录后会把后端返回的 access_token 写入会话存储。"
        />

        <Form layout="vertical" onFinish={onFinish} requiredMark={false}>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, message: '请输入邮箱' }]}>
            <Input placeholder="admin@example.com" autoComplete="email" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
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

Component.displayName = 'AdminLoginPage';
