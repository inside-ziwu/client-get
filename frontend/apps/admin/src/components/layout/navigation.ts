import type { DashboardNavigationGroup } from '@shared/ui';
import {
  Bot,
  Building2,
  Clock,
  Database,
  Flame,
  Globe2,
  Mail,
  Network,
  Server,
  ShoppingBag,
  Star,
  Tags,
  Users,
} from 'lucide-react';

export const adminNavigationGroups = [
  {
    label: '用户',
    items: [{ href: '/tenants', label: '用户管理', icon: Users }],
  },
  {
    label: '采集',
    items: [
      { href: '/data-sources', label: '数据源', icon: Database },
      { href: '/collection-tasks', label: '关键词', icon: Tags },
      { href: '/collection/peers', label: '同行公司', icon: Building2 },
      { href: '/collection/peers-cleaned', label: '同行数据（清洗）', icon: Building2 },
      { href: '/collection/waimaotong', label: '外贸通', icon: Server },
      { href: '/collection/customers', label: '客户数据', icon: ShoppingBag },
    ],
  },
  {
    label: '营销',
    items: [
      { href: '/intelligence-sources', label: '情报源管理', icon: Globe2 },
      { href: '/email-templates', label: '邮件模板', icon: Mail },
      { href: '/scoring-templates', label: '评分模板', icon: Star },
      { href: '/contact-classification', label: '联系人规则', icon: Network },
      { href: '/warmup-rules', label: '预热规则', icon: Flame },
      { href: '/work-schedule', label: '发送时间配置', icon: Clock },
      { href: '/ai-config', label: 'AI 配置', icon: Bot },
    ],
  },
] satisfies DashboardNavigationGroup[];
