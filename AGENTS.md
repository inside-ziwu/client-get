# AGENTS.md

> 本文件是给 **Codex / Claude Code / 其他 AI 编码代理** 看的工作区约束。所有代理在动手前必须先读完本文。

## 1. 工作区结构

这是一个 **monorepo 单仓库**：

| 路径 | 角色 | 是否可改 |
| --- | --- | --- |
| `frontend/` | 前端代码（pnpm monorepo：tenant + admin + packages/ 共享包） | 可改 |
| `backend/` | 后端代码 | 可改 |
| `docs/brainstorms/`、`docs/plans/`、`docs/superpowers/`、`docs/handovers/` | 当前工作流产物（需求 / 设计 / 执行脚本 / 交接记录） | 可改（由工作流 skill 按流程写入） |
| `docs/specs/` | 系统行为规格（能力域 Given/When/Then，系统行为真相；原 `openspec/specs/`，2026-07-05 迁入） | 只读参考：不再经流程自动更新，行为变更后由实施者手工同步对应 spec |
| `docs/solutions/` | 已沉淀的解决方案（bug 修复 / 最佳实践 / 工作流方法论），按 category 组织 + YAML frontmatter（`module` / `tags` / `problem_type`）；由 `/ce:compound` skill 创建。**实施或调试涉及已有解决方案的领域时可参考。** | 可改（仅限 `ce:compound` / `ce:compound-refresh` 添加） |
| `docs/` 其余（会议、原始资料、research、session-records、mock 等） | 历史文档 | **只读，禁止修改/删除/移动** |
| `openspec/` | **已退役**（2026-07-05）：仅保留归档 changes 与 config.yaml 作历史参考，不再新建 change | 只读参考 |

## 2. 任务前置判断

开始前先判断任务会不会修改代码/文档/配置：
- **不修改**（只读分析、review、咨询、运维查询）：直接读取必要上下文即可，无需走工作流
- **修改代码/文档/配置**：进入 §3 行动顺序，按当前工作流推进
- **上线 / 生产副作用**：必须由用户显式触发（见 §8 镜像推送）

## 3. 行动顺序（硬性）

bugfix、需求、行为调整、重构、部署变更都必须走当前工作流（主链权威定义见 `~/Projects/CLAUDE.md`「AI 编程工作流」），不得跳过：

- **路径 A（常规）**：`ce-brainstorm`（产 `docs/brainstorms/…` 需求）→ `writing-plans`（产 `docs/superpowers/plans/…` 的 checkbox-TDD 执行脚本）→ `subagent-driven-development` 或 `executing-plans` 执行
- **路径 B（复杂 / 跨模块 / 仓库耦合深）**：在 A 中间插 `ce-plan` 做架构设计（产 `docs/plans/…-plan.md`）；`writing-plans` 以该 implementation-ready plan 为输入，只降海拔、不重做架构
- **校验 gate**：需求 / spec 定型后跑 `ce-doc-review`；设计定型后（仅路径 B）跑 `gstack-plan-eng-review`
- **坑**：`ce-plan` 收尾会提议 handoff 到 `ce-work`——必须拒绝，手动起 `writing-plans`，否则丢 checkbox-TDD 红绿纪律

实施前先读相关代码、测试、配置与当前 plan 指向的材料；不得把历史文档、现状代码、口头推测直接当实施命令。
文档、注释、配置、样式微调等非功能开发改动，按 §5.1 直接实施即可，不强制全链路。

## 4. 硬性禁止

- **禁止移动 / 剪切 / 删除** `docs/` 下的历史文档与 `docs/specs/`（工作流产物目录 `docs/plans`、`docs/brainstorms`、`docs/superpowers`、`docs/handovers` 由对应 skill 正常写入，不在此列）
- **禁止跳过当前工作流** 直接改代码或写新文档（触发范围见 §3；非功能开发的轻量改动除外）
- **禁止凭印象 / 凭记忆写代码或引用路径**——先 grep / read 确认；系统行为以 `docs/specs/` 现状与代码为准
- **禁止把历史文档、现状代码、口头推测直接当实施命令**——必须先沉淀进当前 plan 产物

## 5. 提交与改动准则

- 简洁优先（KISS），不做过度防御性设计
- 改动前发现疑点时，必须先用 AskUserQuestion 澄清；用户确认后写入当前 plan 产物（`docs/plans/` 或 `docs/superpowers/plans/`）
- 中文沟通，注释与提交信息同样使用中文

### 5.1 Git 分支与推送策略

**所有功能开发走分支，其余直接推 main。**

| 方式 | 适用场景 | 示例 |
| --- | --- | --- |
| **直接推 main** | 非功能开发的改动 | 文档、注释、配置、样式微调、工作流 plan 文档 |
| **分支 → PR → 合并** | 所有功能开发 | 新功能、bug 修复、重构、数据库迁移、API 变更 |

**分支命名**：`feat/<简短描述>`、`fix/<简短描述>`、`refactor/<简短描述>`。

### 5.2 Git 工作流

#### 直接推 main（非功能开发）

```
git add <文件>  →  git commit  →  git push
```

#### 分支开发（功能开发）

```
1. git checkout -b feat/xxx        # 从 main 创建分支
2. 开发过程中随时 commit           # 本地保存进度
3. git push -u origin feat/xxx     # 推送分支到远程
4. 在 GitHub 创建 PR               # 请求合并到 main
5. 验证通过后合并 PR               # 合并到 main
6. git checkout main && git pull   # 本地切回 main 并同步
```

**合并时机**：分支上的功能完整可用、本地验证通过即可合并。不需要等到完美，但不能破坏现有功能。

## 6. 工作流驱动原则（最高优先级）

> 用户决策（2026-07-05）：OpenSpec 退役，改用 compound-engineering（定需求 / 设计）+ superpowers（管执行 / 纪律）主链。主链权威定义见 `~/Projects/CLAUDE.md`「AI 编程工作流」。
> 不管是 bug、需求、行为调整、重构、部署变更，都必须先走该工作流，产出对应 plan 产物后再实施。

### 6.1 执行权威

当前实施任务的最高执行权威是对应的 plan 产物：

- `docs/brainstorms/…`（需求，ce-brainstorm 产出）
- `docs/plans/…-plan.md`（架构设计源，路径 B，ce-plan 产出）
- `docs/superpowers/plans/…`（checkbox-TDD 执行脚本，writing-plans 产出）
- `docs/specs/<capability>/spec.md`（系统行为规格 / 行为真相；只读参考，非本次改动产物）

功能类改动没有对应 plan 产物，不得直接改代码实施。

### 6.2 冲突与缺口处理

- plan 内已明确裁决的，以当前 plan 为准
- plan 没有明确裁决的，不允许 AI 自行补完、选边或平均
- 遇到冲突、缺口、范围不清、验收标准不清时，必须暂停实施，并使用 AskUserQuestion 工具向用户提问
- 提问方式应采用苏格拉底式澄清：一次聚焦一个关键不确定点，给出事实背景、影响范围和可选判断，帮助用户把需求补完整
- 用户确认后，需求变更改 `docs/plans/…-plan.md` 再重跑 `writing-plans` 翻译；不要绕过设计源直接改执行脚本

### 6.3 AI 行为约束

- 实施前必须确认当前工作对应哪份 plan 产物
- bugfix、需求、行为调整、重构、部署变更都必须有 plan 产物；不能因为“只是修 bug”跳过工作流
- 不得把任何历史文档、现状代码、口头推测直接当作实施命令；必须先沉淀到当前 plan
- 如果发现当前 plan 与新决策不一致，必须暂停、提问、更新 plan，再继续

## 7. 实施门禁与迁移过渡

> 本节约束从实施到收尾的最低门槛，并登记 OpenSpec 退役期的过渡例外。

### 7.1 实施中

- 代码改动必须严格落在当前 plan 范围内
- 新发现的需求变化、技术约束、范围变化，必须先更新 plan，再继续实施
- 涉及数据库、worker、邮件、tenant 权限、部署、生产数据的改动，必须做额外 review

### 7.2 收尾前

- 必须完成当前执行脚本的 checkbox 勾选或明确标注未完成项（TDD 红绿纪律由 `writing-plans` 的 checkbox 承载，`executing-plans` 只机械执行）
- 必须运行与改动匹配的验证：测试、构建、lint、E2E、或手工验收记录
- 涉及真实业务链路的改动，不能只靠单元测试，必须有端到端验证或明确记录未验证原因
- 涉及上线的改动，必须有 release / rollback / secrets 检查
- 汇报完成前必须调用 `verification-before-completion` skill，并输出「原始需求 → 已实现/未实现」对照

### 7.3 OpenSpec 退役过渡例外（2026-07-05）

以下 2 个 in-flight change 按老流程做完：完成各自 `tasks.md` 的代码任务 + 验证即可，**无需 `opsx:archive`**；完成后把其最终 spec 手工放进 `docs/specs/`：

- `openspec/changes/fix-engagelab-provider-event-id-length`（11/14）→ 新 spec 落 `docs/specs/engagelab-email-event-ingestion/`
- `openspec/changes/update-email-send-interval-1s`（9/11）→ 新 spec 落 `docs/specs/email-send-interval/`

`openspec/changes/company-list-index-optimization`（3/7，改 `tenant-companies-list`）暂停，待用 docs/plans 重评估是否重启。其余 active changes（`2026-05-16-local-verify-setup` 等）与 3 个 ✓Complete 未归档 change 就地封存，不再推进。

## 8. 镜像构建与推送快捷命令

> 用于下次快速发布镜像。默认按实际改动选择更新 backend / admin / tenant
> 正式推送镜像、同步线上快照、上线操作都属于外部副作用，必须由用户明确触发，不得因普通实施任务自动执行。

### 8.1 正式推送到阿里云 ACR（GitHub Actions，推荐）

通过 GitHub Actions `workflow_dispatch` 手动触发构建，镜像 tag 默认 `YYYY.MM.DD-r1`。
工作流文件：`.github/workflows/build-and-push.yml`

```bash
# 后端（API + 所有 worker 共用镜像）
gh workflow run build-and-push.yml -f service=backend

# Admin 前端
gh workflow run build-and-push.yml -f service=admin

# Tenant 前端
gh workflow run build-and-push.yml -f service=tenant

# 自定义 tag
gh workflow run build-and-push.yml -f service=backend -f tag=hotfix-1

# 查看构建状态
gh run list --workflow=build-and-push.yml --limit 3
```

### 8.2 推送后 Sealos 更新

- `clientget-backend` 使用构建输出的 backend tag
- collection / scheduler / scoring / sending 等 worker 应用也使用同一个 backend tag
- `clientget-admin` 使用构建输出的 admin tag
- `clientget-tenant` 只有执行 tenant 构建时才更新为 tenant tag

### 8.3 仅本地构建验证

```bash
cd /Users/lay/Documents/Github/client_get/backend
docker build -t clientget-backend:local .

cd /Users/lay/Documents/Github/client_get/frontend
docker build -f Dockerfile.admin --build-arg NEXT_PUBLIC_ADMIN_API_BASE_URL=https://api.xinanpcb.com -t clientget-admin:local .

cd /Users/lay/Documents/Github/client_get/frontend
docker build -f Dockerfile.tenant --build-arg NEXT_PUBLIC_API_BASE_URL=https://api.xinanpcb.com -t clientget-tenant:local .
```

## 9. 环境与部署

### 环境变量

- 各端在自己根目录维护 `.env`，互不干扰：
  - `backend/.env` — `CLIENTGET_DEV_DATABASE_URL`（Neon）+ `CLIENTGET_PROD_DATABASE_URL`（Sealos）
  - `frontend/apps/tenant/.env` — `NEXT_PUBLIC_API_BASE_URL`
  - `frontend/apps/admin/.env` — `NEXT_PUBLIC_ADMIN_API_BASE_URL`
- `.env` 值由用户手动维护，不得自动修改。
- 开发环境和生产环境完全隔离，没有"切换"动作。

### 开发环境

- 数据库：Neon 云数据库（`CLIENTGET_DEV_DATABASE_URL`）
- 后端：本地 `uvicorn`
- 前端：本地 `next dev`

### 生产环境

- 数据库：Sealos PostgreSQL（环境变量由 Sealos 控制台注入容器）
- 后端 + 前端：均为 Sealos 容器，镜像托管在阿里云 ACR

### 部署流程（开发验证通过后）

1. 代码推送到 GitHub
2. 在 GitHub Actions 手动触发 `workflow_dispatch`（选择 service：admin / tenant / backend）
3. GitHub Actions 在 amd64 runner 上构建 Docker 镜像并推送到阿里云 ACR
4. 在 Sealos 控制台更新对应服务的镜像 tag

- 本地 `push-*.sh` 脚本仅用于本地调试验证，不用于正式发布（本机 ARM 交叉编译 amd64 很慢）。
- 前端 API 地址在构建时通过 `--build-arg` 注入（`https://api.xinanpcb.com`），不走 `.env`。
- 后端镜像启动时 `/start.sh` 自动执行 `alembic upgrade head`。
- 正式推送镜像、同步线上快照、上线操作都属于外部副作用，必须由用户明确触发，不得因普通实施任务自动执行。

## 10. 线上 PostgreSQL / Alembic 操作经验

- Sealos 外部 PostgreSQL 连接串若只给到主机和端口，必须显式补业务库名 `/clientget`；不补库名会连到默认 `postgres` 库，那里通常没有 `alembic_version`。
- PostgreSQL 的 `psycopg` / SQLAlchemy 连接串不要带 `?directConnection=true`；这是 Mongo 风格参数，`psycopg` 会报 `invalid connection option "directConnection"`。
- 线上手动 Alembic 迁移使用生产连接串（需补 `+psycopg` 驱动前缀）：

  ```bash
  cd backend
  SYNC_DATABASE_URL='postgresql+psycopg://postgres:<password>@dbconn.sealosbja.site:45010/clientget' \
    .venv/bin/python -m alembic upgrade head
  ```

- 执行生产迁移前先只读确认：

  ```sql
  select current_database(), current_user;
  select version_num from alembic_version;
  ```

- 当前 backend 镜像的 `/start.sh` 会先执行 `alembic upgrade head` 再启动服务；若已更新并重启 `clientget-backend`，通常迁移会自动跑完。手动迁移只在需要确认或补跑时执行。

## 11. 项目架构与代码规范速览

> 原 `openspec/config.yaml` 的项目背景随 OpenSpec 退役上移至此，作为实施参考。

- **产品**：ClientGet — B2B 外贸客户智能平台（采集 → 清洗 → 评分 → 邮件触达 全链路）
- **技术栈**：前端 pnpm monorepo（apps/tenant + apps/admin + packages/ 共享包，shadcn/ui + Tailwind，GrapeJS 邮件编辑器）；后端 Python / FastAPI / SQLAlchemy(async)；PostgreSQL + Alembic；Worker `backend/app/workers/`（collection / scheduler / scoring / sending）；部署 Sealos + 阿里云 ACR
- **外部服务**：EngageLab（邮件通道）、Tendata（数据采集）
- **后端路由前缀**：`/admin/api/v1`（管理端）、`/t/{slug}/api/v1`（租户端）、`/internal/api/v1`（内部 worker）、`/webhooks`
- **认证与隔离**：JWT + RLS（`set_current_tenant` 实现租户隔离）
- **前端状态**：React Query（服务端状态）+ Zustand（认证状态）
- **后端分层**：api（路由 + 参数 + 权限）→ services（业务逻辑 + 手写 SQL via AsyncConnection，无 ORM 实体层）→ db/pools（连接池 + RLS）；route 层不写业务逻辑；新增入参优先 Pydantic schema，避免 `payload: dict`；新增静态路由必须放在动态 `/{id}` 路由之前
- **命名**：Python snake_case，TypeScript camelCase 变量 / PascalCase 组件
- **迁移**：Alembic auto-generate，每次变更一个 revision；涉及前端 API 调用时同步更新 `packages/shared-api`
- **准则**：简洁优先（KISS），避免过度防御性设计；中文沟通 / 注释 / 提交信息
