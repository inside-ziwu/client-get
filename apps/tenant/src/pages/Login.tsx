import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, Form, Input, Button, Typography, Flex } from 'antd';
import { useAuthStore } from '@shared/hooks';

const { Title } = Typography;

export function Component() {
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);
  const [loading, setLoading] = React.useState(false);

  const onFinish = async (_values: { email: string; password: string }) => {
    setLoading(true);
    await new Promise((r) => setTimeout(r, 600));
    // 固定 mock token，header.payload.sig 均为合法 base64url，exp 设为超远未来
    setToken('eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTAwMSIsInRpZCI6InRlbmFudC0wMDEiLCJyb2xlcyI6WyJtZW1iZXIiXSwiZXhwIjo5OTk5OTk5OTk5fQ.mock-sig');
    setLoading(false);
    navigate('/', { replace: true });
  };

  return (
    <Flex justify="center" align="center" style={{ minHeight: '100vh', background: '#f5f5f5' }}>
      <Card style={{ width: 400 }}>
        <Title level={3} style={{ textAlign: 'center' }}>ClientGet 客户管理</Title>
        <Form layout="vertical" onFinish={onFinish}>
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
