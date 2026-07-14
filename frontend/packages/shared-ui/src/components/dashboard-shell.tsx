'use client';

import { Menu, PanelLeftClose, PanelLeftOpen } from 'lucide-react';
import { type ComponentType, type ReactNode, useEffect, useState } from 'react';
import { Button } from './button';
import { Sheet, SheetContent, SheetDescription, SheetTitle, SheetTrigger } from './sheet';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from './tooltip';
import { cn } from '../lib/utils';

export interface DashboardNavigationItem {
  href: string;
  label: string;
  icon: ComponentType<{ className?: string }>;
}

export interface DashboardNavigationGroup {
  label: string;
  items: DashboardNavigationItem[];
}

export interface DashboardShellLinkProps {
  href: string;
  className?: string;
  children: ReactNode;
  onClick?: () => void;
  onMouseEnter?: () => void;
  'aria-current'?: 'page';
  'aria-label'?: string;
}

export interface DashboardShellProps {
  brand: string;
  children: ReactNode;
  currentPath: string;
  groups: DashboardNavigationGroup[];
  headerActions: ReactNode;
  homeHref: string;
  onPrefetch?: (href: string) => void;
  renderLink: (props: DashboardShellLinkProps) => ReactNode;
  title: string;
}

const STORAGE_KEY = 'sidebar-collapsed';

function isActivePath(pathname: string, href: string) {
  return pathname === href || (href !== '/' && pathname.startsWith(`${href}/`));
}

export function DashboardShell({
  brand,
  children,
  currentPath,
  groups,
  headerActions,
  homeHref,
  onPrefetch,
  renderLink,
  title,
}: DashboardShellProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [hovered, setHovered] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    setCollapsed(localStorage.getItem(STORAGE_KEY) === 'true');
  }, []);

  const toggleCollapsed = () => {
    const next = !collapsed;
    setCollapsed(next);
    localStorage.setItem(STORAGE_KEY, String(next));
  };

  const renderNavigation = (mobile: boolean) => (
    <nav aria-label={mobile ? '移动端主导航' : '桌面主导航'} className="space-y-5">
      {groups.map((group) => (
        <section key={group.label} className="space-y-1">
          {(mobile || !collapsed) && (
            <div className="px-2 pb-1 text-xs font-medium text-muted-foreground">
              {group.label}
            </div>
          )}
          {group.items.map((item) => {
            const active = isActivePath(currentPath, item.href);
            const Icon = item.icon;
            const link = renderLink({
              href: item.href,
              onClick: mobile ? () => setMobileOpen(false) : undefined,
              onMouseEnter: () => onPrefetch?.(item.href),
              'aria-current': active ? 'page' : undefined,
              'aria-label': !mobile && collapsed ? item.label : undefined,
              className: cn(
                'flex h-9 items-center rounded-md text-sm transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring',
                !mobile && collapsed ? 'w-full justify-center' : 'gap-2 px-2',
                active
                  ? 'bg-primary text-primary-foreground'
                  : 'text-slate-700 hover:bg-muted hover:text-slate-950',
              ),
              children: (
                <>
                  <Icon className="h-4 w-4 shrink-0" />
                  {(mobile || !collapsed) && <span className="truncate">{item.label}</span>}
                </>
              ),
            });

            if (!mobile && collapsed) {
              return (
                <Tooltip key={item.href}>
                  <TooltipTrigger asChild>{link}</TooltipTrigger>
                  <TooltipContent side="right">{item.label}</TooltipContent>
                </Tooltip>
              );
            }

            return <div key={item.href}>{link}</div>;
          })}
        </section>
      ))}
    </nav>
  );

  const expandedOverlay = collapsed && hovered;

  return (
    <TooltipProvider delayDuration={0}>
      <div className="min-h-screen bg-background">
        <div className="flex">
          <aside
            className={cn(
              'sticky top-0 hidden h-screen shrink-0 self-start border-r border-border bg-white transition-all duration-200 lg:block',
              collapsed ? 'w-16' : 'w-64',
            )}
            onMouseEnter={() => collapsed && setHovered(true)}
            onMouseLeave={() => setHovered(false)}
          >
            {expandedOverlay && (
              <div className="absolute left-16 top-0 z-40 h-screen w-56 border-r border-border bg-white shadow-lg">
                <div className="flex h-14 items-center border-b border-border px-5">
                  {renderLink({
                    href: homeHref,
                    className: 'text-base font-semibold tracking-normal',
                    children: brand,
                  })}
                </div>
                <div className="h-[calc(100vh-3.5rem)] overflow-y-auto px-3 py-4">
                  <nav aria-label="展开的桌面主导航" className="space-y-5">
                    {groups.map((group) => (
                      <section key={group.label} className="space-y-1">
                        <div className="px-2 pb-1 text-xs font-medium text-muted-foreground">
                          {group.label}
                        </div>
                        {group.items.map((item) => {
                          const active = isActivePath(currentPath, item.href);
                          const Icon = item.icon;
                          return (
                            <div key={item.href}>
                              {renderLink({
                                href: item.href,
                                onMouseEnter: () => onPrefetch?.(item.href),
                                'aria-current': active ? 'page' : undefined,
                                className: cn(
                                  'flex h-9 items-center gap-2 rounded-md px-2 text-sm transition-colors',
                                  active
                                    ? 'bg-primary text-primary-foreground'
                                    : 'text-slate-700 hover:bg-muted hover:text-slate-950',
                                ),
                                children: (
                                  <>
                                    <Icon className="h-4 w-4 shrink-0" />
                                    <span className="truncate">{item.label}</span>
                                  </>
                                ),
                              })}
                            </div>
                          );
                        })}
                      </section>
                    ))}
                  </nav>
                </div>
              </div>
            )}

            <div className="flex h-14 items-center border-b border-border px-5">
              {renderLink({
                href: homeHref,
                'aria-label': collapsed ? brand : undefined,
                className: collapsed
                  ? 'mx-auto text-base font-bold'
                  : 'text-base font-semibold tracking-normal',
                children: collapsed ? brand.slice(0, 1) : brand,
              })}
            </div>

            <div className="h-[calc(100vh-3.5rem-3rem)] overflow-y-auto px-2 py-4">
              {renderNavigation(false)}
            </div>

            <div className="absolute bottom-0 left-0 right-0 flex h-12 items-center border-t border-border px-2">
              <button
                aria-label={collapsed ? '展开侧边栏' : '收起侧边栏'}
                className="flex h-9 w-full items-center justify-center gap-2 rounded-md text-sm text-slate-500 transition-colors hover:bg-muted hover:text-slate-700"
                onClick={toggleCollapsed}
                type="button"
              >
                {collapsed ? (
                  <PanelLeftOpen className="h-4 w-4" />
                ) : (
                  <PanelLeftClose className="h-4 w-4" />
                )}
                {!collapsed && <span>收起侧边栏</span>}
              </button>
            </div>
          </aside>

          <div className="flex min-h-screen min-w-0 flex-1 flex-col">
            <header className="sticky top-0 z-50 flex h-14 items-center justify-between border-b border-border bg-white/95 px-4 backdrop-blur lg:px-6">
              <div className="flex items-center gap-3">
                <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
                  <SheetTrigger asChild>
                    <Button
                      aria-label="打开导航"
                      className="lg:hidden"
                      size="icon"
                      variant="ghost"
                    >
                      <Menu className="h-4 w-4" />
                    </Button>
                  </SheetTrigger>
                  <SheetContent className="w-72 max-w-[85vw] p-0" side="left">
                    <SheetTitle className="sr-only">主导航</SheetTitle>
                    <SheetDescription className="sr-only">选择要前往的功能页面</SheetDescription>
                    <div className="flex h-14 items-center border-b border-border px-5">
                      {renderLink({
                        href: homeHref,
                        onClick: () => setMobileOpen(false),
                        className: 'text-base font-semibold tracking-normal',
                        children: brand,
                      })}
                    </div>
                    <div className="flex-1 overflow-y-auto px-3 py-4">{renderNavigation(true)}</div>
                  </SheetContent>
                </Sheet>
                <div className="text-sm font-medium text-slate-700">{title}</div>
              </div>
              <div className="flex items-center gap-3">{headerActions}</div>
            </header>
            <main className="min-w-0 flex-1 p-4 lg:p-6">{children}</main>
          </div>
        </div>
      </div>
    </TooltipProvider>
  );
}
