# ClientGet Frontend

pnpm monorepo（Next.js 15 + React 19）：`apps/tenant`（租户端，端口 3001）+ `apps/admin`（管理端，端口 3000）+ `packages/*` 共享包（shared-ui / shared-api / shared-hooks / shared-types）。**完整文档见根目录 [HANDBOOK.md](../HANDBOOK.md)**（架构 §4、本地开发 §8）。

## 快速开始

```bash
pnpm install
pnpm dev:admin     # http://localhost:3000
pnpm dev:tenant    # http://localhost:3001
pnpm type-check    # 全 workspace tsc
```

## 环境变量

- `apps/tenant/.env` → `NEXT_PUBLIC_API_BASE_URL`
- `apps/admin/.env` → `NEXT_PUBLIC_ADMIN_API_BASE_URL`

本地开发均指向 `http://localhost:8000`；生产地址在镜像构建时经 `--build-arg` 注入，不走 .env。

## 要点

- API 前缀由 `@shared/api` 统一拼接：admin 走 `/admin/api/v1`，tenant 走 `/t/{slug}/api/v1`；**tenant 前端路由本身不带 slug，slug 只来自登录输入与 JWT payload**。
- 联调账号：先跑 `backend/scripts/seed_demo_data.py`（见 backend/README）。
- `pnpm lint` 当前不可用（eslint 从未安装，已登记 [issue #50](https://github.com/inside-ziwu/client-get/issues/50)）。
