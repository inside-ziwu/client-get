import { Outlet, useNavigate } from 'react-router-dom';
import {
  DatabaseOutlined,
  StarOutlined,
  GlobalOutlined,
  MailOutlined,
  FireOutlined,
  RobotOutlined,
  TeamOutlined,
} from '@ant-design/icons';
import { AppLayout, RequireAuth } from '@shared/ui';
import type { SidebarItem } from '@shared/ui';
import { useAuthStore } from '@shared/hooks';

const sidebarItems: SidebarItem[] = [
  { key: 'data-sources', path: '/data-sources', icon: <DatabaseOutlined />, label: '数据源管理' },
  { key: 'scoring-templates', path: '/scoring-templates', icon: <StarOutlined />, label: '评分模板' },
  { key: 'intelligence-sources', path: '/intelligence-sources', icon: <GlobalOutlined />, label: '情报源管理' },
  { key: 'email-templates', path: '/email-templates', icon: <MailOutlined />, label: '邮件模板' },
  { key: 'warmup-rules', path: '/warmup-rules', icon: <FireOutlined />, label: '预热规则' },
  { key: 'ai-config', path: '/ai-config', icon: <RobotOutlined />, label: 'AI 配置' },
  { key: 'tenants', path: '/tenants', icon: <TeamOutlined />, label: '租户管理' },
];

function AdminLayout() {
  const navigate = useNavigate();
  const logout = useAuthStore((s) => s.logout);

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  return (
    <RequireAuth>
      <AppLayout
        sidebarItems={sidebarItems}
        currentUser={{ name: 'Admin', email: 'admin@clientget.com' }}
        onLogout={handleLogout}
      >
        <Outlet />
      </AppLayout>
    </RequireAuth>
  );
}

export const Component = AdminLayout;
