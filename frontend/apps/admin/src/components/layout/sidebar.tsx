'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  Bot,
  Building2,
  Database,
  Flame,
  Globe2,
  Mail,
  Network,
  PanelLeftClose,
  PanelLeftOpen,
  Server,
  ShoppingBag,
  Star,
  Tags,
  Users,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { ScrollArea, Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@shared/ui';

const groups = [
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
      { href: '/collection/tendata', label: '腾道数据', icon: Server },
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
      { href: '/ai-config', label: 'AI 配置', icon: Bot },
    ],
  },
];

const STORAGE_KEY = 'sidebar-collapsed';

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [hovered, setHovered] = useState(false);

  useEffect(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === 'true') setCollapsed(true);
  }, []);

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  };

  const showFull = !collapsed || hovered;

  return (
    <TooltipProvider delayDuration={0}>
      <aside
        className={cn(
          'hidden h-screen shrink-0 border-r border-border bg-white transition-all duration-200 lg:block',
          collapsed ? 'w-16' : 'w-64',
        )}
        onMouseEnter={() => collapsed && setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* 悬停浮层 */}
        {collapsed && hovered && (
          <div className="absolute left-16 top-0 z-40 h-screen w-56 border-r border-border bg-white shadow-lg">
            <div className="flex h-14 items-center border-b border-border px-5">
              <Link href="/data-sources" className="text-base font-semibold tracking-normal">
                ClientGet
              </Link>
            </div>
            <ScrollArea className="h-[calc(100vh-3.5rem)] px-3 py-4">
              <nav className="space-y-5">
                {groups.map((group) => (
                  <section key={group.label} className="space-y-1">
                    <div className="px-2 pb-1 text-xs font-medium text-muted-foreground">
                      {group.label}
                    </div>
                    {group.items.map((item) => {
                      const active =
                        pathname === item.href ||
                        (item.href !== '/' && pathname.startsWith(`${item.href}/`));
                      const Icon = item.icon;
                      return (
                        <Link
                          key={item.href}
                          href={item.href}
                          onMouseEnter={() => router.prefetch(item.href)}
                          className={cn(
                            'flex h-9 items-center gap-2 rounded-md px-2 text-sm transition-colors',
                            active
                              ? 'bg-primary text-primary-foreground'
                              : 'text-slate-700 hover:bg-muted hover:text-slate-950',
                          )}
                        >
                          <Icon className="h-4 w-4 shrink-0" />
                          <span className="truncate">{item.label}</span>
                        </Link>
                      );
                    })}
                  </section>
                ))}
              </nav>
            </ScrollArea>
          </div>
        )}

        {/* 主侧边栏内容 */}
        <div className="flex h-14 items-center border-b border-border px-5">
          {showFull && !collapsed ? (
            <Link href="/data-sources" className="text-base font-semibold tracking-normal">
              ClientGet
            </Link>
          ) : (
            <Link href="/data-sources" className="mx-auto text-base font-bold">
              C
            </Link>
          )}
        </div>

        <ScrollArea className="h-[calc(100vh-3.5rem-3rem)] px-2 py-4">
          <nav className="space-y-5">
            {groups.map((group) => (
              <section key={group.label} className="space-y-1">
                {!collapsed && (
                  <div className="px-2 pb-1 text-xs font-medium text-muted-foreground">
                    {group.label}
                  </div>
                )}
                {group.items.map((item) => {
                  const active =
                    pathname === item.href ||
                    (item.href !== '/' && pathname.startsWith(`${item.href}/`));
                  const Icon = item.icon;

                  if (collapsed) {
                    return (
                      <Tooltip key={item.href}>
                        <TooltipTrigger asChild>
                          <Link
                            href={item.href}
                            onMouseEnter={() => router.prefetch(item.href)}
                            className={cn(
                              'flex h-9 w-full items-center justify-center rounded-md transition-colors',
                              active
                                ? 'bg-primary text-primary-foreground'
                                : 'text-slate-700 hover:bg-muted hover:text-slate-950',
                            )}
                          >
                            <Icon className="h-4 w-4" />
                          </Link>
                        </TooltipTrigger>
                        <TooltipContent side="right">{item.label}</TooltipContent>
                      </Tooltip>
                    );
                  }

                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onMouseEnter={() => router.prefetch(item.href)}
                      className={cn(
                        'flex h-9 items-center gap-2 rounded-md px-2 text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                        active
                          ? 'bg-primary text-primary-foreground'
                          : 'text-slate-700 hover:bg-muted hover:text-slate-950',
                      )}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="truncate">{item.label}</span>
                    </Link>
                  );
                })}
              </section>
            ))}
          </nav>
        </ScrollArea>

        {/* 底部切换按钮 */}
        <div className="absolute bottom-0 left-0 right-0 flex h-12 items-center border-t border-border px-2">
          <button
            onClick={toggle}
            className="flex h-9 w-full items-center justify-center gap-2 rounded-md text-sm text-slate-500 transition-colors hover:bg-muted hover:text-slate-700"
          >
            {collapsed ? <PanelLeftOpen className="h-4 w-4" /> : <PanelLeftClose className="h-4 w-4" />}
            {!collapsed && <span>收起侧边栏</span>}
          </button>
        </div>
      </aside>
    </TooltipProvider>
  );
}
