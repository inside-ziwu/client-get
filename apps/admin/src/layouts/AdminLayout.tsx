import { Outlet, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  DatabaseOutlined,
  DashboardOutlined,
  StarOutlined,
  GlobalOutlined,
  InboxOutlined,
  MailOutlined,
  FireOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  UserSwitchOutlined,
} from '@ant-design/icons';
import { AppLayout, RequireAuth } from '@shared/ui';
import type { SidebarItem } from '@shared/ui';
import { useAuthStore } from '@shared/hooks';
import { adminApi } from '../lib/api';

const sidebarItems: SidebarItem[] = [
  { key: 'data-sources', path: '/data-sources', icon: <DatabaseOutlined />, label: '数据源管理' },
  { key: 'scoring-templates', path: '/scoring-templates', icon: <StarOutlined />, label: '评分模板' },
  { key: 'intelligence-sources', path: '/intelligence-sources', icon: <GlobalOutlined />, label: '情报源管理' },
  { key: 'email-templates', path: '/email-templates', icon: <MailOutlined />, label: '邮件模板' },
  { key: 'warmup-rules', path: '/warmup-rules', icon: <FireOutlined />, label: '预热规则' },
  { key: 'ai-config', path: '/ai-config', icon: <RobotOutlined />, label: 'AI 配置' },
  { key: 'tenants', path: '/tenants', icon: <TeamOutlined />, label: '租户管理' },
  { key: 'collection-tasks', path: '/collection-tasks', icon: <ThunderboltOutlined />, label: '采集任务' },
  { key: 'collection/dashboard', path: '/collection/dashboard', icon: <DashboardOutlined />, label: '采集看板' },
  { key: 'collection/archive', path: '/collection/archive', icon: <InboxOutlined />, label: '数据归档' },
  { key: 'collection/cleanup-health', path: '/collection/cleanup-health', icon: <SafetyCertificateOutlined />, label: '清洗健康' },
  { key: 'contact-classification', path: '/contact-classification', icon: <UserSwitchOutlined />, label: '职位分类' },
];

function AdminLayout() {
  const navigate = useNavigate();
  const payload = useAuthStore((s) => s.payload);
  const logout = useAuthStore((s) => s.logout);
  const meQuery = useQuery({
    queryKey: ['admin', 'auth', 'me'],
    queryFn: async () => (await adminApi.auth.me()).data.data,
  });

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const currentUser = meQuery.data
    ? { name: meQuery.data.name, email: meQuery.data.email }
    : {
        name: payload?.roles?.includes('platform_admin') ? 'Platform Admin' : 'Admin',
        email: 'platform-admin',
      };

  return (
    <RequireAuth>
      <AppLayout
        sidebarItems={sidebarItems}
        currentUser={currentUser}
        onLogout={handleLogout}
      >
        <Outlet />
      </AppLayout>
    </RequireAuth>
  );
}

export const Component = AdminLayout;
