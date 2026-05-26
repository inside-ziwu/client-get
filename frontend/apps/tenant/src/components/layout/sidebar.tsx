'use client';

import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import {
  Bot,
  Building2,
  Gauge,
  KeyRound,
  Mail,
  Newspaper,
  PanelLeftClose,
  PanelLeftOpen,
  Send,
  Settings,
  Star,
  Users,
} from 'lucide-react';
import { cn, ScrollArea, Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@shared/ui';

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
          'relative hidden h-screen shrink-0 border-r border-border bg-white transition-all duration-200 lg:block',
          collapsed ? 'w-16' : 'w-64',
        )}
        onMouseEnter={() => collapsed && setHovered(true)}
        onMouseLeave={() => setHovered(false)}
      >
        {/* 悬停浮层 */}
        {collapsed && hovered && (
          <div className="absolute left-16 top-0 z-40 h-screen w-56 border-r border-border bg-white shadow-lg">
            <div className="flex h-14 items-center border-b border-border px-5">
              <Link href="/" className="text-base font-semibold tracking-normal">
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
            <Link href="/" className="text-base font-semibold tracking-normal">
              ClientGet
            </Link>
          ) : (
            <Link href="/" className="mx-auto text-base font-bold">
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
