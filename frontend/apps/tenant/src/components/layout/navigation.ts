import type { DashboardNavigationGroup } from '@shared/ui';
import {
  Bot,
  Building2,
  Gauge,
  Mail,
  Newspaper,
  Send,
  Settings,
  Star,
  Users,
} from 'lucide-react';

export const tenantNavigationGroups = [
  { label: '工作台', items: [{ href: '/', label: '仪表盘', icon: Gauge }] },
  {
    label: '客户',
    items: [
      { href: '/companies', label: '公司列表', icon: Building2 },
      { href: '/curated-customers', label: '优选客户', icon: Star },
    ],
  },
  {
    label: '营销',
    items: [
      { href: '/templates', label: '邮件模板', icon: Mail },
      { href: '/send-plans', label: '发送计划', icon: Send },
    ],
  },
  { label: '情报', items: [{ href: '/intelligence', label: '情报中心', icon: Newspaper }] },
  {
    label: '设置',
    items: [
      { href: '/settings/scoring', label: '评分配置', icon: Settings },
      { href: '/settings/ai-provider', label: 'AI 提供商', icon: Bot },
      { href: '/settings/team', label: '团队管理', icon: Users },
    ],
  },
] satisfies DashboardNavigationGroup[];
