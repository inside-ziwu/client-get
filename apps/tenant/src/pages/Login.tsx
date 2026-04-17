import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, Typography, Flex } from 'antd';
import { useAuthStore } from '@shared/hooks';

const { Title } = Typography;

export function Component() {
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);
  const [loading, setLoading] = React.useState(false);

  const onFinish = async (values: { slug: string; email: string; password: string }) => {
    setLoading(true);
    // TODO: replace with real API call when backend is ready
    await new Promise((r) => setTimeout(r, 600));
    const b64 = (obj: object) =>
      btoa(JSON.stringify(obj)).replace(/=/g, '').replace(/\+/g, '-').replace(/\//g, '_');
    const mockToken = [
      b64({ alg: 'HS256', typ: 'JWT' }),
      b64({
        sub: 'user-001',
        tid: 'tenant-001',
        slug: values.slug,
        roles: ['member'],
        exp: Math.floor(Date.now() / 1000) + 86400 * 7,
        iat: Math.floor(Date.now() / 1000),
      }),
      'mock-sig',
    ].join('.');
    setToken(mockToken);
    setLoading(false);
    navigate('/', { replace: true });
  };

  return (
    <Flex justify="center" align="center" style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ textAlign: 'center' }}>ClientGet 客户管理</Title>
        <Form layout="vertical" onFinish={onFinish}>
          <Form.Item name="slug" label="企业标识" rules={[{ required: true, message: '请输入企业标识' }]}>
            <Input placeholder="your-company" />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, message: '请输入邮箱' }]}>
            <Input placeholder="user@example.com" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, message: '请输入密码' }]}>
            <Input.Password placeholder="请输入密码" />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={loading} block>
              登录
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </Flex>
  );
}

Component.displayName = 'TenantLoginPage';
