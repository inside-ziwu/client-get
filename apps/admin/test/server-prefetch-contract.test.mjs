import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const appDir = resolve(__dirname, '..');
const rootDir = resolve(appDir, '../..');

function read(relativePath) {
  return readFileSync(resolve(appDir, relativePath), 'utf8');
}

function readRoot(relativePath) {
  return readFileSync(resolve(rootDir, relativePath), 'utf8');
}

for (const relativePath of [
  'src/lib/server-api.ts',
  'src/lib/server-query-client.ts',
  'src/lib/get-server-token.ts',
  'src/lib/create-prefetch-page.tsx',
  'src/app/api/auth/set-token/route.ts',
  'src/app/api/auth/clear-token/route.ts',
]) {
  assert.ok(existsSync(resolve(appDir, relativePath)), `缺少服务端预取基础设施：${relativePath}`);
}

const serverApi = read('src/lib/server-api.ts');
assert.match(serverApi, /server-only/, '服务端 API 客户端必须标记 server-only。');
assert.match(serverApi, /BACKEND_INTERNAL_URL/, '服务端 API 客户端必须读取 BACKEND_INTERNAL_URL。');
assert.doesNotMatch(read('next.config.ts'), /BACKEND_INTERNAL_URL/, 'BACKEND_INTERNAL_URL 不能放进 next.config.ts env。');
assert.match(serverApi, /http:\/\/localhost:8000/, '开发环境必须默认回退本地后端。');
assert.match(serverApi, /Authorization/, '服务端 API 客户端必须透传 Authorization header。');
assert.match(serverApi, /AbortController/, '服务端 API 客户端必须用 AbortController 控制超时。');
assert.match(serverApi, /setTimeout\([\s\S]*3_000/, '服务端 API 客户端预取超时必须为 3 秒。');

const queryClient = read('src/lib/server-query-client.ts');
assert.match(queryClient, /new QueryClient/, '每次请求必须创建新的 QueryClient。');
assert.match(queryClient, /staleTime:\s*30_000/, '服务端 staleTime 必须与客户端 30s 一致。');
assert.match(queryClient, /retry:\s*0/, '服务端预取必须禁止 retry。');

const getToken = read('src/lib/get-server-token.ts');
assert.match(getToken, /cookies\(\)/, '必须通过 Next cookies() 读取 token。');
assert.match(getToken, /await\s+cookies\(\)/, 'Next 15 cookies() 必须 await。');

const setToken = read('src/app/api/auth/set-token/route.ts');
assert.match(setToken, /httpOnly:\s*true/, 'set-token 必须写 httpOnly cookie。');
assert.match(setToken, /sameSite:\s*['"]lax['"]/, 'set-token cookie sameSite 必须为 lax。');
assert.match(setToken, /secure:\s*process\.env\.NODE_ENV\s*===\s*['"]production['"]/, 'secure 必须按环境动态设置。');
assert.doesNotMatch(setToken, /maxAge/, '认证 cookie 应为 session cookie，不设置 maxAge。');

const clearToken = read('src/app/api/auth/clear-token/route.ts');
assert.match(clearToken, /delete\(/, 'clear-token 必须删除认证 cookie。');

const login = read('src/app/login/page.tsx');
assert.match(login, /await\s+fetch\(['"]\/api\/auth\/set-token['"]/, '登录成功后必须 await set-token。');
assert.match(login, /setToken\(token\)/, '登录成功仍必须写入 sessionStorage auth store。');
assert.match(login, /router\.replace\(['"]\/['"]\)/, 'set-token 完成后再跳转后台首页。');

const shell = read('src/components/layout/app-shell.tsx');
assert.match(shell, /await\s+fetch\(['"]\/api\/auth\/clear-token['"]/, '登出时必须调用 clear-token。');
assert.match(shell, /logout\(\)/, '登出仍必须清理客户端 auth store。');

const prefetchPage = read('src/lib/create-prefetch-page.tsx');
assert.match(prefetchPage, /HydrationBoundary/, '页面必须通过 HydrationBoundary 注入 dehydrated state。');
assert.match(prefetchPage, /dehydrate\(queryClient\)/, '页面必须 dehydrate 服务端 QueryClient。');
assert.match(prefetchPage, /getServerToken/, '无 token 时必须跳过预取。');
assert.match(prefetchPage, /prefetchQuery/, '必须使用 TanStack prefetchQuery。');

const dockerfile = readRoot('Dockerfile.admin');
assert.match(dockerfile, /ENV BACKEND_INTERNAL_URL=/, 'Admin Dockerfile 必须声明 BACKEND_INTERNAL_URL。');

const warmupPage = read('src/app/(dashboard)/warmup-rules/page.tsx');
assert.doesNotMatch(warmupPage, /['"]use client['"]/, 'warmup-rules page.tsx 必须是 Server Component。');
assert.match(warmupPage, /createPrefetchPage/, 'warmup-rules 必须使用 createPrefetchPage。');
assert.match(warmupPage, /\['admin',\s*'warmup-rules'\]/, 'warmup-rules 服务端 queryKey 必须与客户端一致。');
assert.match(warmupPage, /serverApi\.get/, 'warmup-rules 必须通过服务端 API 预取。');
assert.ok(existsSync(resolve(appDir, 'src/app/(dashboard)/warmup-rules/client-page.tsx')), 'warmup-rules 客户端组件必须拆到 client-page.tsx。');
assert.match(read('src/app/(dashboard)/warmup-rules/client-page.tsx'), /useQuery/, 'warmup-rules 客户端主数据必须改用 useQuery 才能命中 hydrate 缓存。');
