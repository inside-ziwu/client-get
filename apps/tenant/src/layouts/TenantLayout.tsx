import { Outlet } from 'react-router-dom';
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
import { AppLayout, RequireAuth } from '@shared/ui';
import type { SidebarItem } from '@shared/ui';

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
      { key: 'settings-ai-balance', icon: <SettingOutlined />, label: 'AI 额度', path: '/settings/ai-balance' },
      { key: 'settings-team', icon: <SettingOutlined />, label: '团队管理', path: '/settings/team' },
    ],
  },
];

function TenantLayout() {
  return (
    <RequireAuth>
      <AppLayout sidebarItems={sidebarItems}>
        <Outlet />
      </AppLayout>
    </RequireAuth>
  );
}

export const Component = TenantLayout;
