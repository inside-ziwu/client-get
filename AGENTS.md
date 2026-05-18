# AGENTS.md

> 本文件是给 **Codex / Claude Code / 其他 AI 编码代理** 看的工作区约束。所有代理在动手前必须先读完本文。

## 1. 工作区结构

这是一个 **monorepo 单仓库**：

| 路径 | 角色 | 是否可改 |
| --- | --- | --- |
| `frontend/` | 前端代码（pnpm monorepo：tenant + admin + packages/ 共享包） | 可改 |
| `backend/` | 后端代码 | 可改 |
| `docs/` | 历史文档：会议、原始资料、归档、计划（`docs/solutions/` 除外，见下行） | **只读，禁止修改/删除/移动** |
| `docs/solutions/` | 已沉淀的解决方案（bug 修复 / 最佳实践 / 工作流方法论），按 category 组织 + YAML frontmatter（`module` / `tags` / `problem_type`）；由 `/ce:compound` skill 创建。**实施或调试涉及已有解决方案的领域时可参考。** | 可改（仅限 `ce:compound` / `ce:compound-refresh` 添加） |
| `openspec/` | 规范驱动开发（OpenSpec skill 识别） | 可改 |

## 2. 任务前置判断

开始前先判断任务是否会修改代码/文档/配置：
- **不修改**（只读分析、review、咨询）：直接读取必要上下文即可，无需绑定 OpenSpec change
- **修改代码/文档/配置**：必须进入下方行动顺序，绑定 OpenSpec change 后再实施
- **上线 / 生产副作用**：必须由用户显式触发（见 §7 镜像推送）

## 3. 行动顺序（硬性）

任何实施类任务开始前，按以下顺序确认上下文：

1. 先确认当前任务对应的 OpenSpec change：
   - 若用户已指定 change，读取该 change 的 `proposal.md` / `design.md`（如有）/ `tasks.md` / `specs/*`（如有）
   - 若用户未指定 change，先用 `openspec list` 查看当前 active changes
   - 若 active changes 中无法唯一匹配当前任务，必须暂停并询问用户指定 change；不得自行选择相近 change
   - 若没有合适 change，不得实施；必须先创建或补齐 change

2. 最后读取相关代码、测试、配置与当前 change 指向的材料。

禁止在未确认当前 OpenSpec change 的情况下直接改代码。

## 4. 硬性禁止

- **禁止移动或剪切** `docs/` 与 `blueprint/` 下的任何文件
- **禁止在未确认当前 OpenSpec change 的情况下** 直接改代码或写新文档
- **禁止跳过必要上下文读取**——OpenSpec change 必读，`_control/` 仅按当前 change 引用或任务需要读取
- **禁止凭印象写代码**——当前实施事实以 active OpenSpec change 为准；`_control/` 仅提供输入、证据和历史归档
- **禁止跳过 OpenSpec 流程**——bugfix、需求、行为调整、重构、部署变更都必须走 `openspec/changes/`

## 5. 提交与改动准则

- 简洁优先（KISS），不做过度防御性设计
- 改动前发现疑点时，必须先用 AskUserQuestion 澄清；用户确认后写入当前 OpenSpec change
- 中文沟通，注释与提交信息同样使用中文

## 6. OpenSpec 变更驱动原则（最高优先级）

> 用户决策（2026-05-10）：本工作区不再维护单一静态真源。
> 不管是 bug、需求、行为调整、重构、部署变更，都必须先走 OpenSpec，生成 `openspec/changes/<change-id>/` 后再实施。

### 6.1 执行权威

当前实施任务的最高执行权威是对应的 OpenSpec change：

- `openspec/changes/<change-id>/proposal.md`
- `openspec/changes/<change-id>/design.md`（如存在）
- `openspec/changes/<change-id>/tasks.md`
- `openspec/changes/<change-id>/specs/*`（如存在）

没有 OpenSpec change，不得直接改代码实施。

### 6.2 冲突与缺口处理

- change 内已明确裁决的，以当前 change 为准
- change 没有明确裁决的，不允许 AI 自行补完、选边或平均
- 遇到冲突、缺口、范围不清、验收标准不清时，必须暂停实施，并使用 AskUserQuestion 工具向用户提问
- 提问方式应采用苏格拉底式澄清：一次聚焦一个关键不确定点，给出事实背景、影响范围和可选判断，帮助用户把需求补完整
- 用户确认后，必须先把结论更新进当前 OpenSpec change 的 proposal / design / tasks / specs，再继续实施

### 6.3 AI 行为约束

- 实施前必须确认当前工作对应哪个 `openspec/changes/<change-id>/`
- bugfix、需求、行为调整、重构、部署变更都必须有 change；不能因为“只是修 bug”跳过 OpenSpec
- 不得把任何历史文档、现状代码、口头推测直接当作实施命令；必须先沉淀到当前 change
- 如果发现当前 change 与新决策不一致，必须暂停、提问、更新 change，再继续

## 7. OpenSpec 实施门禁

> 本节约束 OpenSpec change 从实施到收尾的最低门槛。

### 7.1 实施前

- 必须存在当前任务对应的 `openspec/changes/<change-id>/`
- change 必须至少包含 `proposal.md` 与 `tasks.md`
- 涉及架构、数据模型、跨模块流程、外部服务、部署的 change，必须补 `design.md`
- `tasks.md` 必须能拆到可执行步骤，不能只有一句泛泛目标
- change 中存在冲突、缺口或验收标准不清时，必须先 AskUserQuestion 澄清并更新 change

### 7.2 实施中

- 代码改动必须严格落在当前 change 范围内
- 新发现的需求变化、技术约束、范围变化，必须先更新 change，再继续实施
- 涉及数据库、worker、邮件、tenant 权限、部署、生产数据的改动，必须做额外 review

### 7.3 收尾前

- 必须完成当前 change 的 `tasks.md` 勾选或明确标注未完成项
- 必须运行与改动匹配的验证：测试、构建、lint、E2E、或手工验收记录
- 涉及真实业务链路的 change，不能只靠单元测试，必须有端到端验证或明确记录未验证原因
- 涉及上线的 change，必须有 release / rollback / secrets 检查
- 汇报完成前必须调用 `verification-before-completion` skill，并输出「原始需求 → 已实现/未实现」对照

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

## 9. 本地数据库与线上快照同步

- 正式推送镜像、同步线上快照、上线操作都属于外部副作用，必须由用户明确触发，不得因普通实施任务自动执行。
- 本地开发库：`clientget`
- 每次需要用线上同数据测试前，在后端目录运行：

  ```bash
  cd backend
  ./scripts/sync_prod_db_to_local.sh
  ```

## 10. 线上 PostgreSQL / Alembic 操作经验

- Sealos 外部 PostgreSQL 连接串若只给到主机和端口，必须显式补业务库名 `/clientget`；不补库名会连到默认 `postgres` 库，那里通常没有 `alembic_version`。
- PostgreSQL 的 `psycopg` / SQLAlchemy 连接串不要带 `?directConnection=true`；这是 Mongo 风格参数，`psycopg` 会报 `invalid connection option "directConnection"`。
- 线上手动 Alembic 迁移使用同步驱动连接串：

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

## 11. 开发工作流（按任务规模分档）

按任务规模选择对应流程。每步只用一个技能/工具。

### S 级：小任务（< 2h，低风险）

适用：文案、小 bug、局部样式、单文件小改、低风险脚本调整。

```
ce:plan → ce:work → verification-before-completion → gstack ship
```

S 级不强制 OpenSpec，不强制 QA，不强制经验沉淀。

### M 级：常规功能（半天~2天）

适用：常规功能、常规重构、影响用户路径但范围清楚。

```
ce:brainstorm → ce:plan → gstack plan-eng-review → ce:work → verification-before-completion → gstack qa → gstack ship
```

### L 级：大功能/高风险（多天，跨模块）

适用：多天任务、跨模块改动、产品方向不确定、多人协作、需要长期维护。

```
ce:brainstorm → opsx:propose → opsx:verify → ce:plan → gstack plan-eng-review → ce:work → verification-before-completion → gstack qa → ce:review → gstack ship → gstack land-and-deploy → opsx:archive → ce:compound
```

### 补充说明

- `using-superpowers` 是隐含会话纪律，不列为执行步骤
- `gstack autoplan` 不是默认步骤，仅在需要全视角自动总审时使用（"帮我完整审一遍"）
- `ce:compound` 只在踩坑、形成可复用模式、或有长期价值时使用
- 纯修 bug 时，M 级第 1 步可替换为 `systematic-debugging`
- 非 Web 项目，`gstack qa` 替换为 `gstack health`
