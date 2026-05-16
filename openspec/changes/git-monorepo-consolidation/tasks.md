# Tasks · git-monorepo-consolidation

## Phase 1: 准备与备份

- [ ] **1.1** 确认 frontend repo 所有有价值分支已合入 main 或本地可达
  - 检查 `codex/tenant-nextjs-rewrite` 等活跃分支状态
  - 如有未合入的 feature 分支，先完成合并或记录
- [ ] **1.2** 确认 backend repo 所有有价值分支已合入 main 或本地可达
- [ ] **1.3** 确认根 repo 的 `claude/*` 本地分支中是否有未提交的 PM 资产变更
- [ ] **1.4** 备份三个 repo 的 `.git/` 目录到临时位置（以防回滚）

## Phase 2: 组装 Monorepo

- [ ] **2.1** 在临时目录创建新的 git repo（`git init`）
- [ ] **2.2** 从 frontend repo（main 分支）复制全量文件到 `frontend/`
  - 包含 `apps/`、`packages/`、`deploy/`、`pnpm-workspace.yaml`、`package.json` 等
  - 不复制 `.git/`、`.github/`（CI 后面单独处理）
- [ ] **2.3** 从 backend repo（main 分支）复制全量文件到 `backend/`
  - 包含 `app/`、`alembic/`、`scripts/`、`Dockerfile` 等
  - 不复制 `.git/`、`.github/`
- [ ] **2.4** 从根 repo 复制 PM 资产和 Agent 配置到根目录
  - `openspec/`、`_control/`、`docs/`、`blueprint/`
  - `AGENTS.md`、`CLAUDE.md`、`README.md`
  - `.claude/`、`.codex/`、`.opencode/`
- [ ] **2.5** 编写新的根 `.gitignore`
  - 移除 `frontend/` 和 `backend/` 排除规则
  - 合并三个 repo 的 ignore 规则（node_modules、.next、__pycache__、.venv 等）

## Phase 3: CI/CD 整合

- [ ] **3.1** 复用根 repo 现有 `build-and-push.yml`（workflow_dispatch）
  - context 路径已正确（`frontend` / `backend`）
  - 修复 tenant build-arg：`VITE_API_BASE_URL` → `NEXT_PUBLIC_API_BASE_URL`
  - 同步更新 `frontend/.env.example`：`VITE_API_BASE_URL` → `NEXT_PUBLIC_API_BASE_URL`
- [ ] **3.2** 删除 frontend 和 backend 各自的 `.github/workflows/`
- [ ] **3.3** 确认 GitHub Actions secrets（ACR 凭据等）在 `client-get` repo 中已配置

## Phase 4: 配置文件更新

- [ ] **4.1** 更新 `CLAUDE.md` — 移除"独立 git 仓库"描述，更新模块说明
- [ ] **4.2** 更新 `AGENTS.md` — 更新工作区结构描述 + §8.2 本地构建命令环境变量修复
  - §1：移除"独立 git 仓库"描述
  - §8.2：admin 改用 `NEXT_PUBLIC_ADMIN_API_BASE_URL`，tenant 改用 `NEXT_PUBLIC_API_BASE_URL`
- [ ] **4.3** 更新 `openspec/config.yaml` — 更新 context 中的仓库结构
- [ ] **4.4** 全局搜索路径硬编码 — grep `.claude/`、`.codex/` 配置中是否有旧路径引用
- [ ] **4.5** 检查部署脚本路径 — `push-admin.sh`、`push-tenant.sh`、`push-backend.sh` 中的相对路径是否仍然正确

## Phase 5: 推送与远端清理

- [ ] **5.1** 首次 commit 并推送到 `client-get.git`
  - 需要 force push（远端历史将被替换）
  - 操作前最终确认远端分支已无保留价值
- [ ] **5.2** 归档 `clientget-api.git`
  - 先提交 README 重定向说明（指向 monorepo）
  - 再在 GitHub 上标记为 archived（archive 后 repo 变为只读）
- [ ] **5.3** 清理本地 `client_get/` 目录
  - 删除 `frontend/.git/` 和 `backend/.git/`
  - 或直接用新 monorepo 替换整个目录

## Phase 6: 验证

- [ ] **6.1** `git clone` 新 repo 到干净目录，确认文件完整
- [ ] **6.2** `cd frontend && pnpm install && pnpm build:admin && pnpm build:tenant` — 前端构建正常
- [ ] **6.3** Claude Code worktree 创建测试 — 确认 worktree 包含 frontend/ 和 backend/ 代码
- [ ] **6.4** 手动触发 workflow_dispatch 构建 admin，确认构建成功
- [ ] **6.5** 手动触发 workflow_dispatch 构建 tenant，确认 `NEXT_PUBLIC_API_BASE_URL` 正确注入
- [ ] **6.6** `docker build -f backend/Dockerfile backend/` — 后端 Docker 构建正常
- [ ] **6.7** 确认部署脚本 `push-admin.sh --load`、`push-tenant.sh --load`、`push-backend.sh --load` 本地构建正常
