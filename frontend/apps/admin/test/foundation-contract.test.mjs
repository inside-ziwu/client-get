import assert from 'node:assert/strict';
import { existsSync, readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const appDir = resolve(__dirname, '..');
const rootDir = resolve(appDir, '../..');
const transitionalName = ['admin', 'next'].join('-');

function read(relativePath) {
  return readFileSync(resolve(appDir, relativePath), 'utf8');
}

function readRoot(relativePath) {
  return readFileSync(resolve(rootDir, relativePath), 'utf8');
}

for (const relativePath of [
  'package.json',
  'next.config.ts',
  'components.json',
  '../../Dockerfile.admin',
  '../../deploy/push-admin.sh',
  'src/app/layout.tsx',
  'src/app/api/healthz/route.ts',
  'src/app/login/page.tsx',
  'src/app/(dashboard)/layout.tsx',
  'src/app/(dashboard)/page.tsx',
  'src/components/layout/sidebar.tsx',
  'src/components/layout/app-shell.tsx',
  'src/components/auth/require-auth.tsx',
  'src/providers.tsx',
  'src/lib/api.ts',
  'src/lib/format.ts',
  'src/lib/utils.ts',
]) {
  assert.ok(existsSync(resolve(appDir, relativePath)), `缺少 admin 文件：${relativePath}`);
}

assert.ok(!existsSync(resolve(rootDir, `apps/${transitionalName}`)), '过渡 Admin Next 目录必须已删除。');
assert.ok(!existsSync(resolve(rootDir, `Dockerfile.${transitionalName}`)), '过渡 Admin Next Dockerfile 必须已删除。');
assert.ok(!existsSync(resolve(rootDir, `deploy/push-${transitionalName}.sh`)), '过渡 Admin Next 推送脚本必须已删除。');

const packageJson = JSON.parse(read('package.json'));
assert.equal(packageJson.name, '@apps/admin');
assert.equal(packageJson.scripts.dev, 'next dev');
assert.equal(packageJson.scripts.build, 'next build');
assert.ok(packageJson.dependencies.next, 'admin 必须依赖 Next.js。');
assert.ok(packageJson.dependencies['@tanstack/react-query'], 'admin 必须复用 TanStack Query。');
assert.ok(packageJson.dependencies.zustand, 'admin 必须保留 zustand auth store。');
assert.ok(packageJson.dependencies.axios, 'admin 必须继续复用 axios shared api。');
assert.ok(packageJson.dependencies.dayjs, 'admin 必须提供日期格式化依赖。');
assert.ok(packageJson.dependencies['lucide-react'], 'shadcn 图标按钮使用 lucide-react。');

const nextConfig = read('next.config.ts');
assert.match(nextConfig, /output:\s*['"]standalone['"]/, 'Next 必须启用 standalone 输出。');
assert.match(nextConfig, /@shared\/api/, 'Next 必须 transpile @shared/api。');
assert.match(nextConfig, /@shared\/types/, 'Next 必须 transpile @shared/types。');
assert.match(nextConfig, /@shared\/hooks/, 'Next 必须 transpile @shared/hooks。');
assert.match(nextConfig, /PHASE_DEVELOPMENT_SERVER/, 'Next 配置必须只在 dev server 启用本地后端 rewrite。');
assert.match(nextConfig, /phase\s*!==\s*PHASE_DEVELOPMENT_SERVER/, '生产 standalone 构建不能带本地后端 rewrite。');
assert.match(nextConfig, /return\s+\[\];/, '生产 standalone 构建不能把 /admin/api/* rewrite 到容器内本地后端。');
assert.match(nextConfig, /source:\s*['"]\/admin\/api\/:path\*['"]/, 'Next dev 必须代理 /admin/api/*。');
assert.match(
  nextConfig,
  /destination:\s*['"]http:\/\/localhost:8000\/admin\/api\/:path\*['"]/,
  'Next dev 代理必须指向本地后端 admin API。',
);

const dockerfile = readRoot('Dockerfile.admin');
assert.match(dockerfile, /FROM node:20-alpine AS build/, 'admin Dockerfile 必须使用 node:20-alpine build 阶段。');
assert.match(dockerfile, /ARG NEXT_PUBLIC_ADMIN_API_BASE_URL/, 'admin Dockerfile 必须声明生产 API base URL 构建参数。');
assert.match(dockerfile, /ENV NEXT_PUBLIC_ADMIN_API_BASE_URL=\$\{NEXT_PUBLIC_ADMIN_API_BASE_URL\}/, 'admin Dockerfile 必须在 next build 前暴露生产 API base URL。');
assert.match(dockerfile, /pnpm --filter @apps\/admin build/, 'admin Dockerfile 必须构建 admin。');
assert.match(dockerfile, /\.next\/standalone/, 'admin Dockerfile 必须复制 Next standalone 输出。');
assert.match(dockerfile, /EXPOSE 3000/, 'admin standalone 容器必须暴露 3000 端口。');
assert.match(dockerfile, /CMD \["node", "apps\/admin\/server\.js"\]/, 'admin 容器必须启动 standalone server。');
assert.doesNotMatch(dockerfile, /COPY apps\/admin apps\/admin/, 'admin Dockerfile 不能覆盖安装后生成的 workspace node_modules。');
assert.doesNotMatch(dockerfile, /apps\/admin\/dist/, '正式 admin Dockerfile 不能再引用旧 Vite admin dist。');

const pushAdmin = readRoot('deploy/push-admin.sh');
assert.match(pushAdmin, /clientget-admin/, '正式 Admin 推送脚本必须使用 clientget-admin 镜像名。');
assert.doesNotMatch(pushAdmin, new RegExp(`clientget-${transitionalName}`), '正式 Admin 推送脚本不能再使用过渡镜像名。');
assert.match(pushAdmin, /crpi-q6fqloatvalw3jr2\.cn-beijing\.personal\.cr\.aliyuncs\.com/, 'Admin 推送脚本必须指向阿里云 ACR。');
assert.match(pushAdmin, /PLATFORM=["']linux\/amd64["']/, 'Admin 推送脚本必须固定 linux/amd64。');
assert.match(pushAdmin, /MODE="\$\{1:---load\}"/, 'Admin 推送脚本默认必须只本地 load，不推送。');
assert.match(pushAdmin, /TAG:-/, 'Admin 推送脚本必须允许显式 TAG 覆盖。');
assert.match(pushAdmin, /REV:-/, 'Admin 推送脚本必须允许显式 REV 覆盖。');
assert.match(pushAdmin, /--push/, 'Admin 推送脚本必须保留显式推送模式。');
assert.match(pushAdmin, /API_URL=["']https:\/\/api\.xinanpcb\.com["']/, 'Admin 推送脚本必须固定生产后端 API 域名。');
assert.match(pushAdmin, /--build-arg\s+NEXT_PUBLIC_ADMIN_API_BASE_URL="\$\{API_URL\}"/, 'Admin 推送脚本必须把生产 API base URL 写入构建。');

const healthz = read('src/app/api/healthz/route.ts');
assert.match(healthz, /NextResponse\.json\(\{\s*ok:\s*true\s*\}\)/, 'admin 必须提供 /api/healthz 健康检查。');

const tsconfig = read('tsconfig.json');
assert.match(tsconfig, /"@shared\/api"/, 'tsconfig 必须配置 @shared/api alias。');
assert.match(tsconfig, /"@shared\/types"/, 'tsconfig 必须配置 @shared/types alias。');
assert.match(tsconfig, /"@shared\/hooks"/, 'tsconfig 必须配置 @shared/hooks alias。');

const tailwindConfig = read('tailwind.config.ts');
assert.doesNotMatch(tailwindConfig, /require\(/, 'tailwind.config.ts 必须兼容 ESM next dev，不能使用 require()。');
assert.match(tailwindConfig, /tailwindcss-animate/, 'Tailwind 必须保留 tailwindcss-animate 插件。');

const providers = read('src/providers.tsx');
assert.match(providers, /QueryClientProvider/, 'providers 必须包装 QueryClientProvider。');
assert.match(providers, /staleTime:\s*30_000/, 'Query staleTime 必须沿用 30s。');
assert.match(providers, /gcTime:\s*5\s*\*\s*60_000/, 'Query gcTime 必须沿用 5m。');
assert.match(providers, /retry:\s*1/, 'Query retry 必须沿用 1。');

const sharedClient = readRoot('packages/shared-api/src/client.ts');
assert.match(sharedClient, /baseURL\?:\s*string/, 'createApiClient 必须接受可选 baseURL。');
assert.match(sharedClient, /import\.meta\.env\.VITE_API_BASE_URL/, '默认 baseURL 必须保持 Vite 环境变量。');

const adminApi = read('src/lib/api.ts');
assert.match(adminApi, /NEXT_PUBLIC_ADMIN_API_BASE_URL/, 'admin 生产构建必须读取 NEXT_PUBLIC_ADMIN_API_BASE_URL。');
assert.match(adminApi, /createApiClient\(['"]admin['"],\s*\{\s*baseURL:\s*adminBaseURL\s*\}\)/, 'admin 必须把生产 API base URL 传给 shared api。');
assert.match(adminApi, /createAdminApi\(client\)/, 'admin 必须复用 createAdminApi。');

const format = read('src/lib/format.ts');
assert.match(format, /formatDateTime/, '必须提供 formatDateTime 工具。');
assert.match(format, /YYYY-MM-DD HH:mm/, '默认时间格式应为 YYYY-MM-DD HH:mm。');
assert.match(format, /return\s+['"]-['"]/, '空时间值应展示为 -。');
assert.match(format, /dayjs/, 'formatDateTime 应使用 dayjs。');
