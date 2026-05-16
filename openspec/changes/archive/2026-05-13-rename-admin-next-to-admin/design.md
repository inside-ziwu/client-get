## Context

当前前端仓库是 `frontend/` 独立 git 仓库，内部用 pnpm workspace 管理 `apps/tenant`、`apps/admin-next` 和 `packages/*` 共享包。Next.js Admin 已经作为正式 Admin 上线，但路径、workspace 包名、Dockerfile、contract tests 中仍保留 `admin-next` 过渡命名。

根目录是 OpenSpec / 控制仓库，不是业务前端应用仓库。直接在根目录新增 `admin/` 会引入第三个项目边界，并需要重新定义 git、pnpm、Docker、共享包依赖和部署脚本关系。

## Goals / Non-Goals

**Goals:**

- 将正式 Admin 项目入口收敛为 `frontend/apps/admin`。
- 将 workspace 包名收敛为 `@apps/admin`。
- 更新构建、部署、测试、契约断言中对 Admin 项目的路径和包名引用。
- 保持现有 `frontend` 仓库、shared packages、Next.js standalone Docker 部署和 `clientget-admin` 镜像名不变。
- 清除用户和开发者可见的 `admin-next` 过渡入口，降低后续维护认知成本。

**Non-Goals:**

- 不创建根目录 `admin/` 应用。
- 不拆分新仓库。
- 不调整页面功能、UI、API contract 或运行时行为。
- 不删除 tenant 应用或 shared packages。
- 不执行生产推送，除非用户后续明确要求。

## Decisions

### D-1: 保留 `frontend/` 仓库边界

Admin SHALL stay under `frontend/` rather than becoming a root-level app.

Rationale: `frontend/` 已经是独立 git 仓库，并承载 pnpm workspace、lockfile、shared API/types/hooks、Dockerfile 和 deploy 脚本。保留这个边界能减少迁移面，也避免根控制仓库承担业务前端源码。

Alternative considered: root-level `admin/` app. Rejected because it creates a new dependency and deployment boundary without solving a runtime problem.

### D-2: 使用 `apps/admin` 作为正式路径

The existing `apps/admin-next` directory SHALL be renamed to `apps/admin`, and package name SHALL become `@apps/admin`.

Rationale: `admin-next` 是迁移期命名；上线后继续保留会让脚本、测试和部署文档都携带过渡状态。

### D-2a: 先清理旧 `apps/admin` 本地残留

Before renaming, implementation SHALL verify that the existing `frontend/apps/admin` directory has no git-tracked source files. If it only contains legacy local artifacts such as `dist/`, `node_modules/`, or `.env.development`, it SHALL be removed as a migration precondition.

Rationale: The canonical target path is currently occupied by old Vite Admin residue. Treating that as an explicit precondition prevents an unsafe overwrite and makes the rename deterministic.

### D-3: 移除过渡脚本别名

Root frontend scripts SHALL expose `dev:admin` and `build:admin` only. Transitional `dev:admin-next` and `build:admin-next` SHALL be removed.

Rationale: 双入口会让后续命令、文档和自动化继续漂移。正式命名后只保留一个入口更符合 KISS。

### D-4: Dockerfile 继续在 frontend 根构建

`Dockerfile.admin` SHALL remain in `frontend/` and continue building `clientget-admin` from the pnpm workspace, but all app paths and filter names SHALL point to `apps/admin` / `@apps/admin`.

Rationale: 当前 Dockerfile 已经适配 Next.js standalone 和 shared packages。只改路径，不重写部署模型，风险最低。

### D-5: Contract tests 作为迁移护栏

Existing Admin contract tests SHALL move with the app and assert the canonical `apps/admin` layout. Tests SHALL reject stale `@apps/admin-next`, `apps/admin-next`, and transitional push/build script names in active build/deploy files.

Rationale: 这类目录迁移最容易留下旧路径。契约测试能防止以后再把过渡命名加回来。

## Risks / Trade-offs

- [Risk] `apps/admin` 旧残留目录阻塞 rename 或被误认为正式源码 → Mitigation: 先运行 `git -C frontend ls-files apps/admin` 确认无 tracked 文件；清理前列出残留内容，避免误删仍需保留的本地环境文件。
- [Risk] `apps/admin-next` ignored build artifacts are moved into the new canonical directory → Mitigation: remove ignored `.next`, `node_modules`, and `*.tsbuildinfo` before or immediately after rename; preserve tracked source changes and `public/.gitkeep`.
- [Risk] pnpm lockfile path/name变化导致安装或 Docker 构建失败 → Mitigation: 运行 `pnpm install --lockfile-only` 或等价命令刷新 lockfile，并运行 Admin type-check/build。
- [Risk] Next standalone 输出路径变化导致容器启动失败 → Mitigation: 更新 Dockerfile 的 `.next/standalone`、static/public copy 路径和 `CMD`，并本地构建镜像验证。
- [Risk] 测试脚本仍从旧目录运行 → Mitigation: 将 `apps/admin-next/test` 移到 `apps/admin/test`，并更新测试中 `appDir` / 错误信息。
- [Risk] 历史文件中仍出现 `admin-next` → Mitigation: 本 change 只要求 active build/deploy/test/source 引用清零；历史 OpenSpec change 或归档记录不强制改写。

## Migration Plan

1. Verify existing `frontend/apps/admin` has no tracked source files.
2. Remove legacy local `frontend/apps/admin` residue.
3. Remove ignored build artifacts from `frontend/apps/admin-next` while preserving tracked source changes.
4. Rename `frontend/apps/admin-next` to `frontend/apps/admin`.
5. Update package name and frontend root scripts.
6. Update `Dockerfile.admin` paths and `pnpm --filter` target.
7. Update contract tests and any active source references.
8. Refresh `pnpm-lock.yaml`.
9. Run `rg` to ensure active frontend build/deploy/source files no longer reference `admin-next`.
10. Run Admin contract tests, type-check, production build, and local Docker build.
11. If the user later requests release, push a new `clientget-admin` image as a separate deployment action.

Rollback: revert the path/package/script changes and restore the previous `apps/admin-next` references. No database or backend rollback is needed.

## Open Questions

- None. User approved keeping Admin in `frontend/` and making `apps/admin` the canonical path.
