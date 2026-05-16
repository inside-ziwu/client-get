'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import {
  BarChart3,
  Bot,
  Building2,
  Gauge,
  KeyRound,
  Mail,
  Newspaper,
  Send,
  Settings,
  Star,
  Users,
} from 'lucide-react';
import { cn, ScrollArea } from '@shared/ui';

const groups = [
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
      { href: '/email-monitor', label: '邮件监控', icon: BarChart3 },
    ],
  },
  { label: '情报', items: [{ href: '/intelligence', label: '情报中心', icon: Newspaper }] },
  {
    label: '设置',
    items: [
      { href: '/settings/keywords', label: '关键词', icon: KeyRound },
      { href: '/settings/scoring', label: '评分配置', icon: Settings },
      { href: '/settings/ai-provider', label: 'AI 提供商', icon: Bot },
      { href: '/settings/team', label: '团队管理', icon: Users },
    ],
  },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <aside className="hidden h-screen w-64 shrink-0 border-r border-border bg-white lg:block">
      <div className="flex h-14 items-center border-b border-border px-5">
        <Link href="/" className="text-base font-semibold tracking-normal">
          ClientGet
        </Link>
      </div>
      <ScrollArea className="h-[calc(100vh-3.5rem)] px-3 py-4">
        <nav className="space-y-5">
          {groups.map((group) => (
            <section key={group.label} className="space-y-1">
              <div className="px-2 pb-1 text-xs font-medium text-muted-foreground">{group.label}</div>
              {group.items.map((item) => {
                const active = pathname === item.href || (item.href !== '/' && pathname.startsWith(`${item.href}/`));
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onMouseEnter={() => router.prefetch(item.href)}
                    className={cn(
                      'flex h-9 items-center gap-2 rounded-md px-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                      active ? 'bg-primary text-primary-foreground' : 'text-slate-700 hover:bg-muted hover:text-slate-950',
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    <span className="truncate">{item.label}</span>
                  </Link>
                );
              })}
            </section>
          ))}
        </nav>
      </ScrollArea>
    </aside>
  );
}
