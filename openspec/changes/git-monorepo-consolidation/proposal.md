# Proposal · git-monorepo-consolidation

> 基础设施变更：将 3 个独立 git 仓库整合为 1 个 monorepo

## Why

当前工作区 `client_get/` 下存在 3 个互相独立的 git 仓库：

| 目录 | GitHub remote | 追踪内容 | 文件数 |
|------|---------------|----------|--------|
| `/`（根） | `client-get.git` | PM 资产（openspec, _control, docs, AGENTS.md） | 468 |
| `frontend/` | `client-get.git` | 前端代码（apps/admin + apps/tenant + packages/*） | 195 |
| `backend/` | `clientget-api.git` | 后端代码（FastAPI + Alembic） | 201 |

这个结构引发三类问题：

1. **Agent 工具混乱** — Claude Code / Codex 的 worktree 基于根 repo 创建，但根 `.gitignore` 排除了 `frontend/` 和 `backend/`，导致 worktree 中无法看到实际代码。跨模块改动需要切换 repo 上下文，极易搞混。
2. **CI/CD 碎片化** — 三个 repo 各自维护一份 `.github/workflows/build-and-push.yml`，部署逻辑分散在不同 git 历史中，无法通过单一 PR 完成跨模块变更。
3. **远端冲突** — 根 repo 和 frontend repo 指向同一个 GitHub remote（`client-get.git`），但拥有完全独立的 commit 历史（互不可达）。根 repo 的 PM 资产分支（`claude/*`）仅存在于本地，没有远端备份。

## What Changes

### 引入

#### 统一的 monorepo 目录结构

在 `client-get.git` 上全新初始化，将三个 repo 的代码合入同一个 git 历史：

```
client-get/
├── frontend/              ← 原 frontend repo 全量文件
│   ├── apps/admin/
│   ├── apps/tenant/
│   ├── packages/shared-*/
│   ├── deploy/
│   ├── pnpm-workspace.yaml
│   └── package.json
├── backend/               ← 原 backend repo 全量文件
│   ├── app/
│   ├── alembic/
│   ├── scripts/
│   └── Dockerfile
├── openspec/              ← 原根 repo PM 资产
├── _control/
├── docs/
├── blueprint/
├── .github/workflows/     ← 统一 CI workflow（workflow_dispatch）
├── .claude/               ← Agent 配置统一
├── .codex/
├── AGENTS.md
├── CLAUDE.md
└── .gitignore             ← 不再 ignore frontend/ 和 backend/
```

#### 复用现有 workflow_dispatch

根 repo 已有的 `build-and-push.yml` 支持 `workflow_dispatch` 手动选择 admin / tenant / backend，context 路径已正确指向 monorepo 目录。只需修复 tenant 的 build-arg（`VITE_API_BASE_URL` → `NEXT_PUBLIC_API_BASE_URL`），删除 frontend 和 backend 各自的独立 workflow。

### 修改

- **`.gitignore`** — 移除 `frontend/` 和 `backend/` 的排除规则
- **`CLAUDE.md`** — 更新模块路径说明（不再提"独立 git 仓库"）
- **`AGENTS.md`** — 更新工作区结构描述
- **`openspec/config.yaml`** — 更新 context 中的仓库结构描述

### 移除

- 根目录、frontend/、backend/ 各自的独立 `.git/` 目录（合并后只保留根 `.git/`）
- frontend 和 backend 各自的 `.github/workflows/`（已合入根目录的统一 workflow）
- GitHub 远端 `clientget-api.git` — 归档后标记为 archived

## Non-Goals

- ❌ 不改动任何业务代码（前端页面、后端 API、数据库 schema）
- ❌ 不改动 pnpm workspace 结构（`packages/*` 和 `apps/*` 的引用关系不变）
- ❌ 不改动 Dockerfile 内容和部署脚本逻辑（仅路径引用可能微调）
- ❌ 不改动 Sealos 集群配置或阿里云 ACR 仓库名
- ❌ 不保留旧 git 历史（全新初始化，三个 repo 都较新且 commit 数少，历史价值有限）
- ❌ 不拆分 admin/tenant 为独立 repo（它们通过 `workspace:*` 共享 4 个包，拆分代价过高）

## Impact

| 模块 | 影响 |
|------|------|
| Git 仓库 | 3 个 repo → 1 个 monorepo；全新 commit 历史 |
| GitHub remote | `client-get.git` 重置为 monorepo；`clientget-api.git` 归档 |
| CI/CD | 3 份独立 workflow → 复用根 repo 现有 workflow_dispatch（修复 tenant build-arg） |
| Agent 工具 | worktree 可覆盖全部代码和 PM 资产，不再需要切换 repo 上下文 |
| 前端代码 | 无变动（原样迁入） |
| 后端代码 | 无变动（原样迁入） |
| PM 资产 | 无变动（已在根目录） |
| 部署脚本 | 路径不变（`frontend/deploy/push-*.sh`、`backend/scripts/push-backend.sh`） |
| 数据库 | 无影响 |

## Risks

| 风险 | 缓解措施 |
|------|----------|
| GitHub force push 丢失远端分支 | 操作前确认所有有价值的分支已合入 main 或本地备份 |
| CI secrets/环境变量失效 | 合并 workflow 前逐一确认 GitHub Actions secrets 配置 |
| Agent 配置文件路径硬编码 | 全局搜索 `.claude/`、`.codex/` 中的路径引用并更新 |
| 旧 repo 被其他工具引用 | 检查 Sealos 部署配置、本地 IDE 配置是否引用旧 remote |

## Relationship to Other Changes

- `tenant-nextjs-rewrite`（已归档）— Tenant 已完成 Next.js 迁移，本 change 可直接执行
- 后续所有 change 将在统一的 monorepo 中进行，不再需要跨 repo 协调
