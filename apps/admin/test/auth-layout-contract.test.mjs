import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const appDir = resolve(__dirname, '..');

function read(relativePath) {
  return readFileSync(resolve(appDir, relativePath), 'utf8');
}

const rootLayout = read('src/app/layout.tsx');
assert.match(rootLayout, /<html lang=["']zh-CN["']>/, '根布局必须设置中文 lang。');
assert.match(rootLayout, /<Providers>/, '根布局必须包装 Providers。');

const dashboardLayout = read('src/app/(dashboard)/layout.tsx');
assert.match(dashboardLayout, /RequireAuth/, 'Dashboard layout 必须启用认证守卫。');
assert.match(dashboardLayout, /AppShell/, 'Dashboard layout 必须使用 AppShell。');

const requireAuth = read('src/components/auth/require-auth.tsx');
assert.match(requireAuth, /useAuthStore/, '认证守卫必须读取 zustand auth store。');
assert.match(requireAuth, /router\.replace\(['"]\/login['"]\)/, '未登录或过期必须跳转登录页。');
assert.match(requireAuth, /isExpired\(\)/, '认证守卫必须检查 JWT 过期。');
assert.match(requireAuth, /hydrated/, '认证守卫必须等待客户端 hydration，避免重页面刷新时误跳登录。');

const login = read('src/app/login/page.tsx');
assert.match(login, /adminApi\.auth\.login/, '登录页必须调用真实 Admin 登录 API。');
assert.match(login, /setToken/, '登录成功必须写入 sessionStorage auth store。');
assert.match(login, /router\.replace\(['"]\/['"]\)/, '登录成功必须回到后台首页。');
assert.match(login, /type=["']password["']/, '登录页必须包含密码输入。');
assert.match(login, /外贸获客SaaS/, '登录页标题必须使用当前产品定位。');
assert.doesNotMatch(login, /ClientGet Admin/, '登录页不应继续展示旧标题 ClientGet Admin。');
assert.doesNotMatch(login, /使用真实 API 登录后台管理系统/, '登录页不应展示内部实现说明。');

const appShell = read('src/components/layout/app-shell.tsx');
assert.match(appShell, /adminApi\.auth\.me/, '主布局必须加载当前用户信息。');
assert.match(appShell, /logout\(\)/, '主布局必须提供登出。');
assert.match(appShell, /router\.replace\(['"]\/login['"]\)/, '登出必须回登录页。');
assert.match(appShell, /Sidebar/, '主布局必须渲染侧边栏。');

const sidebar = read('src/components/layout/sidebar.tsx');
for (const label of [
  '用户',
  '用户管理',
  '采集',
  '数据源',
  '关键词',
  '同行公司',
  '同行数据（清洗）',
  '腾道数据',
  '客户数据',
  '营销',
  '情报源管理',
  '邮件模板',
  '评分模板',
  '联系人规则',
  '预热规则',
  'AI 配置',
]) {
  assert.match(sidebar, new RegExp(label), `侧边栏缺少导航文案：${label}`);
}

for (const href of [
  '/tenants',
  '/data-sources',
  '/collection-tasks',
  '/collection/peers',
  '/collection/peers-cleaned',
  '/collection/tendata',
  '/collection/customers',
  '/intelligence-sources',
  '/email-templates',
  '/scoring-templates',
  '/contact-classification',
  '/warmup-rules',
  '/ai-config',
]) {
  assert.match(sidebar, new RegExp(`href:\\s*['"]${href.replace(/\//g, '\\/')}['"]`), `侧边栏缺少路由：${href}`);
}

const home = read('src/app/(dashboard)/page.tsx');
assert.match(home, /redirect\(['"]\/data-sources['"]\)/, '首页必须重定向到 /data-sources。');
