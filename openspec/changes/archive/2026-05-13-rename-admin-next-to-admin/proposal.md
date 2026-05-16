## Why

Admin 已经完成 Next.js 重写并作为正式管理端上线，但代码路径、包名、脚本和契约测试仍保留 `admin-next` 过渡命名。这会持续制造认知负担，也让后续清理旧 Vite Admin 时更容易误判项目边界。

本次 change 的目标是把 Next.js Admin 正式命名为 `admin`，同时保持 `frontend/` 作为独立前端仓库，不在根目录新增第三套 Admin 项目。

## What Changes

- 将 `frontend/apps/admin-next` 正式迁移为 `frontend/apps/admin`。
- 将 workspace 包名从 `@apps/admin-next` 改为 `@apps/admin`。
- 更新前端根脚本、Dockerfile、push 脚本、contract tests、文案断言和路径引用中的 `admin-next` 命名。
- 保持正式镜像名 `clientget-admin`、端口 `3000`、API base URL 和 Next.js standalone 部署方式不变。
- 移除或归档旧的过渡命名入口，避免继续出现 `dev:admin-next` / `build:admin-next` 等临时脚本。
- 明确旧 Vite Admin 不再作为正式 Admin 项目入口；如代码仍存在，必须不再被 build / deploy / tests 引用。

## Non-Goals

- 不在根目录新建 `admin/` 独立项目。
- 不拆分新的 git 仓库。
- 不重写页面逻辑、视觉设计或 API 映射。
- 不修改 backend、tenant 或数据库 schema。
- 不改变线上域名、Ingress、镜像仓库名或 Sealos 应用名。

## Capabilities

### New Capabilities

- `admin-project-canonical-layout`: Admin 前端 SHALL 使用正式 `apps/admin` 项目路径和 `@apps/admin` workspace 包名作为唯一管理端代码入口。

### Modified Capabilities

- None.

## Impact

| Area | Impact |
| --- | --- |
| `frontend/apps/admin-next` | Rename to `frontend/apps/admin`; update package metadata and local path references. |
| `frontend/package.json` | Update `dev:admin` / `build:admin` to target `@apps/admin`; remove transitional `admin-next` aliases. |
| `frontend/Dockerfile.admin` | Update COPY paths, build filter, standalone output paths, and server command from `apps/admin-next` to `apps/admin`. |
| `frontend/deploy/push-admin.sh` | Keep image repo `clientget-admin`; ensure it builds the canonical `apps/admin` project. |
| `frontend/apps/admin/test/*` | Move and update contract tests to assert canonical naming and reject old transitional names. |
| `frontend/pnpm-lock.yaml` | Refresh workspace lockfile after package path/name change. |
| backend/database | No change. |
| deployment | Requires local build verification. Production image push is a separate explicit follow-up, not required to complete this rename change. |

## Control References

- Decision: current user decision on 2026-05-13 to keep Admin in the frontend repository but remove `admin-next` transitional naming.
- Capability domain: Admin frontend project layout and deployment packaging.
