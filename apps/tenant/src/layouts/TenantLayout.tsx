import { useEffect } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  DashboardOutlined,
  BankOutlined,
  UsergroupAddOutlined,
  FileTextOutlined,
  SendOutlined,
  BarChartOutlined,
  ReadOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { AppLayout, RequireAuth } from '@shared/ui';
import type { SidebarItem } from '@shared/ui';
import { useAuthStore } from '@shared/hooks';
import { tenantApi } from '../lib/api';

const sidebarItems: SidebarItem[] = [
  { key: 'dashboard', icon: <DashboardOutlined />, label: '工作台', path: '/dashboard' },
  { key: 'companies', icon: <BankOutlined />, label: '公司列表', path: '/companies' },
  { key: 'curated-customers', icon: <UsergroupAddOutlined />, label: '优选客户', path: '/curated-customers' },
  { key: 'templates', icon: <FileTextOutlined />, label: '邮件模板', path: '/templates' },
  { key: 'send-plans', icon: <SendOutlined />, label: '发送计划', path: '/send-plans' },
  { key: 'email-monitor', icon: <BarChartOutlined />, label: '邮件监控', path: '/email-monitor' },
  { key: 'intelligence', icon: <ReadOutlined />, label: '情报中心', path: '/intelligence' },
  {
    key: 'settings',
    icon: <SettingOutlined />,
    label: '设置',
    path: '/settings',
    children: [
      { key: 'settings-keywords', icon: <SettingOutlined />, label: '关键词管理', path: '/settings/keywords' },
      { key: 'settings-scoring', icon: <SettingOutlined />, label: '评分配置', path: '/settings/scoring' },
      { key: 'settings-contact-rules', icon: <SettingOutlined />, label: '触达规则', path: '/settings/contact-rules' },
      { key: 'settings-ai-provider', icon: <SettingOutlined />, label: 'OpenRouter', path: '/settings/ai-provider' },
      { key: 'settings-team', icon: <SettingOutlined />, label: '团队管理', path: '/settings/team' },
    ],
  },
];

function TenantLayout() {
  const navigate = useNavigate();
  const location = useLocation();
  const logout = useAuthStore((s) => s.logout);
  const meQuery = useQuery({
    queryKey: ['tenant', 'auth', 'me'],
    queryFn: async () => (await tenantApi.auth.me()).data.data,
  });
  const notificationsQuery = useQuery({
    queryKey: ['tenant', 'notifications', 'layout'],
    queryFn: async () => (await tenantApi.notifications.list()).data.data,
  });

  useEffect(() => {
    if (meQuery.data?.needs_onboarding && location.pathname !== '/onboarding') {
      navigate('/onboarding', { replace: true });
    }
  }, [location.pathname, meQuery.data?.needs_onboarding, navigate]);

  return (
    <RequireAuth>
      <AppLayout
        sidebarItems={sidebarItems}
        currentUser={meQuery.data ? { name: meQuery.data.name, email: meQuery.data.email } : undefined}
        notificationCount={(notificationsQuery.data ?? []).filter((item) => !item.is_read).length}
        onNotificationClick={() => navigate('/dashboard')}
        onLogout={() => {
          logout();
          navigate('/login', { replace: true });
        }}
      >
        <Outlet />
      </AppLayout>
    </RequireAuth>
  );
}

export const Component = TenantLayout;
