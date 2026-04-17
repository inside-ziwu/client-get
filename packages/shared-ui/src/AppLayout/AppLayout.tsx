import React, { useState } from 'react';
import { Layout, Menu, Avatar, Dropdown, Badge, Button } from 'antd';
import {
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  UserOutlined,
  LogoutOutlined,
  BellOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation } from 'react-router-dom';

const { Header, Sider, Content } = Layout;

export interface SidebarItem {
  key: string;
  icon: React.ReactNode;
  label: string;
  path: string;
  children?: SidebarItem[];
}

export interface AppLayoutProps {
  sidebarItems: SidebarItem[];
  children: React.ReactNode;
  currentUser?: { name: string; email: string };
  onLogout?: () => void;
  notificationCount?: number;
  onNotificationClick?: () => void;
  logo?: React.ReactNode;
}

export function AppLayout({
  sidebarItems,
  children,
  currentUser,
  onLogout,
  notificationCount = 0,
  onNotificationClick,
  logo,
}: AppLayoutProps) {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey =
    sidebarItems.find((item) => location.pathname.startsWith(item.path))?.key ??
    sidebarItems[0]?.key;

  const menuItems = sidebarItems.map((item) => ({
    key: item.key,
    icon: item.icon,
    label: item.label,
    children: item.children?.map((child) => ({
      key: child.key,
      icon: child.icon,
      label: child.label,
    })),
  }));

  const userMenuItems = [
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: '退出登录',
      onClick: onLogout,
    },
  ];

  const handleMenuClick = ({ key }: { key: string }) => {
    const findItem = (items: SidebarItem[]): SidebarItem | undefined => {
      for (const item of items) {
        if (item.key === key) return item;
        if (item.children) {
          const found = findItem(item.children);
          if (found) return found;
        }
      }
      return undefined;
    };
    const item = findItem(sidebarItems);
    if (item?.path) {
      navigate(item.path);
    }
  };

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={setCollapsed}
        trigger={null}
        width={240}
        collapsedWidth={64}
      >
        <div
          style={{
            height: 64,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: collapsed ? 16 : 20,
            fontWeight: 600,
            borderBottom: '1px solid rgba(255,255,255,0.1)',
          }}
        >
          {logo ?? (collapsed ? 'CG' : 'ClientGet')}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey ?? '']}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: '1px solid #f0f0f0',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            <Button
              type="text"
              icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
              onClick={() => setCollapsed(!collapsed)}
            />
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
            {onNotificationClick && (
              <Badge count={notificationCount} size="small">
                <Button
                  type="text"
                  icon={<BellOutlined />}
                  onClick={onNotificationClick}
                />
              </Badge>
            )}
            {currentUser && (
              <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
                <div
                  style={{
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                  }}
                >
                  <Avatar size="small" icon={<UserOutlined />} />
                  <span>{currentUser.name}</span>
                </div>
              </Dropdown>
            )}
          </div>
        </Header>
        <Content style={{ margin: 24, minHeight: 'calc(100vh - 112px)' }}>
          {children}
        </Content>
      </Layout>
    </Layout>
  );
}
