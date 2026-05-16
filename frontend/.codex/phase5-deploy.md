# Phase 5: 部署与收尾

> 前置：Phase 1-4 全部完成（12 个页面已实现）
> 完整规划见 `../../openspec/changes/tenant-nextjs-rewrite/design.md`

## 目标

创建部署配置、contract tests、完成回归验证，最终用 tenant-next 替换旧 tenant。

## 执行步骤

### 1. Dockerfile

创建 `Dockerfile.tenant-next`（放在 `frontend/` 根目录），参照 `Dockerfile.admin`：

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
RUN npm install -g pnpm@9.15.0

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml tsconfig.base.json .npmrc ./
COPY apps/tenant-next/package.json apps/tenant-next/package.json
COPY apps/tenant/package.json apps/tenant/package.json
COPY apps/admin/package.json apps/admin/package.json
COPY packages/shared-api/package.json packages/shared-api/package.json
COPY packages/shared-hooks/package.json packages/shared-hooks/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
COPY packages/shared-ui/package.json packages/shared-ui/package.json

RUN pnpm install --frozen-lockfile

COPY apps/tenant-next apps/tenant-next
COPY packages packages

ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

RUN pnpm --filter @apps/tenant-next build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs \
  && adduser --system --uid 1001 nextjs

COPY --from=build --chown=nextjs:nodejs /app/apps/tenant-next/.next/standalone ./
COPY --from=build --chown=nextjs:nodejs /app/apps/tenant-next/.next/static ./apps/tenant-next/.next/static
COPY --from=build --chown=nextjs:nodejs /app/apps/tenant-next/public ./apps/tenant-next/public

USER nextjs
EXPOSE 3000
CMD ["node", "apps/tenant-next/server.js"]
```

### 2. push-tenant.sh

重写 `deploy/push-tenant.sh`，参照 `deploy/push-admin.sh`，适配 Next.js standalone 镜像。

### 3. Health Check Route

创建 `apps/tenant-next/src/app/api/healthz/route.ts`：
```ts
export function GET() {
  return Response.json({ status: 'ok' });
}
```

### 4. Contract Tests

创建 `apps/tenant-next/test/foundation-contract.test.mjs`，参照 `apps/admin/test/foundation-contract.test.mjs`。

覆盖断言：
1. 文件存在性：package.json, next.config.ts, Dockerfile, push script, 所有 page.tsx
2. package.json 依赖
3. next.config 设置（standalone, transpilePackages, rewrites）
4. Dockerfile 规范
5. push-tenant.sh 规范
6. tsconfig aliases
7. tailwind.config（sharedPreset, content 路径）
8. providers 配置（staleTime, gcTime, retry）

### 5. 回归测试

12 个页面逐一手动验证，确认功能与现有 Vite 版本一致。

### 6. 清理与替换

确认全部通过后：
1. 删除 `apps/tenant/`（旧 Vite 版本）
2. 将 `apps/tenant-next/` 重命名为 `apps/tenant/`
3. 更新 Dockerfile 和 push 脚本中的路径
4. 清理 @shared/ui 中残留的 antd 相关代码（如有）
5. 更新 monorepo 根 package.json 的 dev:tenant / build:tenant 脚本
6. 更新 pnpm-workspace.yaml（tenant-next → tenant）

## 约束

- 清理替换前必须确认所有 12 个页面回归通过
- 旧 tenant 的 `pnpm dev` 和 `pnpm build` 在替换前不受影响
