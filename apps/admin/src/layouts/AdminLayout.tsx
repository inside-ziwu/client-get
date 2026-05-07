import { Outlet, useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  DatabaseOutlined,
  StarOutlined,
  ApartmentOutlined,
  GlobalOutlined,
  MailOutlined,
  FireOutlined,
  RobotOutlined,
  TeamOutlined,
  ThunderboltOutlined,
  UserSwitchOutlined,
  CloudServerOutlined,
  ShopOutlined,
} from '@ant-design/icons';
import { AppLayout, RequireAuth } from '@shared/ui';
import type { SidebarItem } from '@shared/ui';
import { useAuthStore } from '@shared/hooks';
import { adminApi } from '../lib/api';

const sidebarItems: SidebarItem[] = [
  {
    key: 'group-customers',
    label: '客户',
    type: 'group',
    children: [
      { key: 'tenants', path: '/tenants', icon: <TeamOutlined />, label: '客户管理' },
    ],
  },
  {
    key: 'group-collection',
    label: '采集',
    type: 'group',
    children: [
      { key: 'data-sources',          path: '/data-sources',         icon: <DatabaseOutlined />,    label: '数据源' },
      { key: 'collection-tasks',      path: '/collection-tasks',     icon: <ThunderboltOutlined />, label: '关键词' },
      { key: 'collection/peers',        path: '/collection/peers',     icon: <ApartmentOutlined />,   label: '同行公司' },
      { key: 'collection/tendata',    path: '/collection/tendata',   icon: <CloudServerOutlined />, label: '腾道数据' },
      { key: 'collection/customers',  path: '/collection/customers', icon: <ShopOutlined />,        label: '客户数据' },
    ],
  },
  {
    key: 'group-marketing',
    label: '营销',
    type: 'group',
    children: [
      { key: 'intelligence-sources',    path: '/intelligence-sources',   icon: <GlobalOutlined />,     label: '情报源管理' },
      { key: 'email-templates',        path: '/email-templates',        icon: <MailOutlined />,       label: '邮件模板' },
      { key: 'scoring-templates',      path: '/scoring-templates',      icon: <StarOutlined />,       label: '评分模板' },
      { key: 'contact-classification', path: '/contact-classification', icon: <UserSwitchOutlined />, label: '联系人规则' },
      { key: 'warmup-rules',           path: '/warmup-rules',           icon: <FireOutlined />,       label: '预热规则' },
      { key: 'ai-config',              path: '/ai-config',              icon: <RobotOutlined />,      label: 'AI 配置' },
    ],
  },
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
