# Design · git-monorepo-consolidation

## 1. 目标目录结构

```
client-get/                          ← 唯一的 .git/
├── .github/
│   └── workflows/
│       └── build-and-push.yml       ← 统一 workflow（已有，微调即可）
├── .claude/                         ← Agent 配置（从根 repo 带入）
├── .codex/
├── .opencode/
│
├── frontend/                        ← 前端 monorepo（原样迁入）
│   ├── apps/
│   │   ├── admin/
│   │   └── tenant/
│   ├── packages/
│   │   ├── shared-api/
│   │   ├── shared-hooks/
│   │   ├── shared-types/
│   │   └── shared-ui/
│   ├── deploy/
│   │   ├── push-admin.sh
│   │   └── push-tenant.sh
│   ├── .dockerignore
│   ├── Dockerfile.admin
│   ├── Dockerfile.tenant
│   ├── package.json
│   ├── pnpm-lock.yaml
│   └── pnpm-workspace.yaml
│
├── backend/                         ← 后端（原样迁入）
│   ├── app/
│   ├── alembic/
│   ├── scripts/
│   │   └── push-backend.sh
│   ├── Dockerfile
│   └── ...
│
├── openspec/
├── _control/
├── docs/                            ← 只读
├── blueprint/                       ← 只读
├── AGENTS.md
├── CLAUDE.md
├── README.md
└── .gitignore                       ← 合并后的 ignore 规则
```

## 2. `.gitignore` 合并方案

三个 repo 的 `.gitignore` 合并为一个，按模块分区注释：

```gitignore
# ══════════════════════════════════════
# 通用
# ══════════════════════════════════════
.DS_Store
.idea/
.vscode/
*.swp

# ══════════════════════════════════════
# 前端（frontend/）
# ══════════════════════════════════════
node_modules/
dist/
frontend/apps/*/.next/
.turbo/
*.local
*.tsbuildinfo
coverage/
.gstack/

# 部署脚本版本追踪
frontend/deploy/.admin-rev
frontend/deploy/.tenant-rev

# ══════════════════════════════════════
# 后端（backend/）
# ══════════════════════════════════════
.venv/
.pytest_cache/
__pycache__/
*.py[cod]
.coverage
htmlcov/
.ruff_cache/

# 部署脚本版本追踪
backend/scripts/.backend-rev

# ══════════════════════════════════════
# 环境与敏感文件
# ══════════════════════════════════════
.env
.env.*
!.env.example

# ══════════════════════════════════════
# 数据与工具缓存
# ══════════════════════════════════════
*.dump
.playwright-mcp/
.worktrees

# ══════════════════════════════════════
# Agent 本地状态
# ══════════════════════════════════════
.claude/settings.local.json
```

**变更点**：

| 原规则 | 处理 |
|--------|------|
| 根 `.gitignore` 的 `frontend/` 和 `backend/` 排除 | **删除**（核心变更） |
| 前端 `apps/*/.next/` | 改为 `frontend/apps/*/.next/`（路径前缀） |
| 前端 `deploy/.admin-rev` | 改为 `frontend/deploy/.admin-rev` |
| 后端 `scripts/.backend-rev` | 改为 `backend/scripts/.backend-rev` |
| 三者共有的 `.DS_Store`、`.env`、`node_modules/` 等 | 去重合并 |

## 3. CI/CD Workflow 方案

### 现状

根 repo 已经有一个统一的 `build-and-push.yml`，支持 `workflow_dispatch` 手动选择 admin / tenant / backend，**且 context 路径已经正确**：

```yaml
# 已有的正确配置
context: ${{ inputs.service == 'backend' && 'backend' || 'frontend' }}
file: ${{ inputs.service == 'backend' && 'backend/Dockerfile' || format('frontend/Dockerfile.{0}', inputs.service) }}
```

### 方案：直接复用根 repo 的 workflow

根 repo 的 workflow 已经是 monorepo 视角设计的，只需微调：

1. **保留** `.github/workflows/build-and-push.yml`（根 repo 版本）
2. **删除** frontend 和 backend 各自的 `.github/workflows/`（不再需要）
3. **修正** tenant 的 `build-args`：

```yaml
# 修正前（根 repo 现有）
${{ inputs.service == 'tenant' && format('VITE_API_BASE_URL={0}', env.API_URL) || '' }}

# 修正后（tenant 已迁移到 Next.js）
${{ inputs.service == 'tenant' && format('NEXT_PUBLIC_API_BASE_URL={0}', env.API_URL) || '' }}
```

> 注：tenant 已完成 Next.js 迁移（`tenant-nextjs-rewrite` 已归档），不再使用 Vite。已确认 `Dockerfile.tenant` 使用 `ARG NEXT_PUBLIC_API_BASE_URL`，此为环境变量名的唯一真源。同步更新 `frontend/.env.example`。

### 不做 path-filter 自动触发

现有 workflow 是 `workflow_dispatch`（手动触发），不是 push 自动触发。保持这个模式——项目规模小，手动触发更可控。如果后续需要自动化，再加 `on.push.paths` 触发条件。

## 4. Dockerfile 影响分析

### frontend/Dockerfile.admin 和 Dockerfile.tenant

**无需修改**。Dockerfile 中的 `COPY` 路径都是相对于 build context 的，而 workflow 的 `context: 'frontend'` 已确保 build context 是 `frontend/` 目录。

```
workflow context: frontend/     ← Docker build 的根
├── COPY package.json ...       ← 相对于 frontend/
├── COPY apps/admin/...         ← 相对于 frontend/
└── COPY packages/...           ← 相对于 frontend/
```

### backend/Dockerfile

**无需修改**。同理，`context: 'backend'` 确保 build context 是 `backend/` 目录。

### frontend/.dockerignore

**无需修改**。`.dockerignore` 已排除 `.git`、`node_modules` 等，在 monorepo 下行为不变。

## 5. 部署脚本影响分析

### `frontend/deploy/push-admin.sh` / `push-tenant.sh`

脚本使用 `$(dirname "$0")` 来定位 rev 文件，使用 `docker build` 时传入的 context 和 Dockerfile 路径。需检查是否有硬编码的绝对路径或依赖 `git rev-parse --show-toplevel`。

```bash
# push-admin.sh 中的关键路径（需确认）
DOCKERFILE="Dockerfile.admin"       # 相对路径 → 需从 frontend/ 目录运行
REV_FILE="$(dirname "$0")/.admin-rev"  # 相对于脚本位置 → 不受影响
```

**结论**：只要运行脚本时 `cd frontend` 再执行，或脚本内部用 `cd "$(dirname "$0")/.."` 定位根，就不受影响。需逐行确认。

### `backend/scripts/push-backend.sh`

同理检查。

## 6. Agent 配置更新

### AGENTS.md 变更

**§1 工作区结构**需要重写：

```markdown
## 1. 工作区结构

这是一个 **monorepo 单仓库**：

| 路径 | 角色 | 是否可改 |
| --- | --- | --- |
| `frontend/` | 前端代码（pnpm monorepo：tenant + admin） | 可改 |
| `backend/` | 后端代码 | 可改 |
| `blueprint/` | 历史后端蓝图与设计依据 | **只读** |
| `docs/` | 历史文档（`docs/solutions/` 除外） | **只读** |
| `docs/solutions/` | 已沉淀的解决方案 | 可改 |
| `_control/` | 输入 / 证据 / 历史归档区 | 可改 |
| `openspec/` | 规范驱动开发 | 可改 |
```

删除原文中关于"根目录是 OpenSpec / 工作区控制仓库；`frontend/` 与 `backend/` 各自是独立 git 仓库"的描述，以及"涉及业务代码改动时，必须分别在对应子仓库查看分支与工作区状态"的警告。

**§8.2 本地构建验证** — 同步修复环境变量名（tenant-nextjs-rewrite 遗留债务）：

```bash
# 修正前
docker build -f Dockerfile.admin --build-arg VITE_API_BASE_URL=https://api.xinanpcb.com ...
docker build -f Dockerfile.tenant --build-arg VITE_API_BASE_URL=https://api.xinanpcb.com ...

# 修正后
docker build -f Dockerfile.admin --build-arg NEXT_PUBLIC_ADMIN_API_BASE_URL=https://api.xinanpcb.com ...
docker build -f Dockerfile.tenant --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.xinanpcb.com ...
```

### CLAUDE.md 变更

**§5 模块说明**开头更新：

```markdown
## 5. 模块说明

单一 monorepo，所有代码和 PM 资产在同一个 git 历史中。
```

### openspec/config.yaml 变更

`context.工作区结构` 更新为：

```yaml
context: |
  # 工作区结构
  - 单一 monorepo（根目录一个 .git）
  - frontend/：pnpm monorepo（tenant 租户端 + admin 管理端 + packages/ 共享包）
  - backend/：Python（FastAPI + SQLAlchemy + Alembic）
  - openspec/、_control/、docs/、blueprint/：PM 资产和历史文档
```

## 7. 迁移操作细节

### Step 1: 准备临时目录

```bash
mkdir ~/tmp-monorepo && cd ~/tmp-monorepo
git init
```

### Step 2: 复制文件（保持目录结构）

```bash
# 前端（从 frontend repo 的 main 分支）
cd /Users/lay/Documents/Github/client_get/frontend
git checkout main
cd ~/tmp-monorepo
rsync -av --exclude='.git' --exclude='.github' \
  --exclude='node_modules' --exclude='.next' --exclude='dist' \
  --exclude='.turbo' --exclude='.tsbuildinfo' \
  /Users/lay/Documents/Github/client_get/frontend/ frontend/

# 后端（从 backend repo 的 main 分支）
cd /Users/lay/Documents/Github/client_get/backend
git checkout main
cd ~/tmp-monorepo
rsync -av --exclude='.git' --exclude='.github' \
  --exclude='.venv' --exclude='__pycache__' --exclude='.pytest_cache' \
  --exclude='.ruff_cache' \
  /Users/lay/Documents/Github/client_get/backend/ backend/

# PM 资产和 Agent 配置（从根 repo）
rsync -av --exclude='.git' --exclude='frontend' --exclude='backend' \
  --exclude='.worktrees' --exclude='.gstack' \
  /Users/lay/Documents/Github/client_get/ .
```

### Step 3: 写入新 `.gitignore`（见上方 §2）

### Step 4: 更新配置文件（见上方 §6）

### Step 5: 首次提交与推送

```bash
git add -A
git commit -m "chore: 三仓库合并为 monorepo

将根 repo（PM 资产）、frontend repo（前端代码）、backend repo（后端代码）
合并为单一 monorepo。全新 commit 历史，旧 repo 归档。

动机：
- 解决 Agent 工具（Claude Code / Codex）worktree 无法覆盖全部代码的问题
- 统一 CI/CD workflow
- 消除两个 repo 共用一个 GitHub remote 的混乱状态"

git remote add origin https://github.com/inside-ziwu/client-get.git
git push --force origin main
```

### Step 6: 归档 backend 旧 repo

```bash
gh repo archive inside-ziwu/clientget-api --yes
```

### Step 7: 替换本地工作目录

```bash
# 备份旧目录
mv /Users/lay/Documents/Github/client_get /Users/lay/Documents/Github/client_get.bak

# 克隆新 monorepo
git clone https://github.com/inside-ziwu/client-get.git \
  /Users/lay/Documents/Github/client_get
```

## 8. 回滚方案

如果迁移后发现问题：

1. 旧的 `.git/` 目录已备份（tasks 1.4）
2. `clientget-api.git` 归档前可随时 unarchive
3. GitHub 的 force push 可通过 reflog 恢复（72 小时内）

最坏情况：从备份的 `.git.bak` 目录恢复三个独立 repo。
