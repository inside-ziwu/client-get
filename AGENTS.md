# AGENTS.md

> 给 **Codex / Claude Code / 其他 AI 编码代理** 的工作区约束。动手前先读完本文，并通读 [HANDBOOK.md](HANDBOOK.md)。

## 1. 事实源与文档体系

| 文件 | 地位 |
| --- | --- |
| [HANDBOOK.md](HANDBOOK.md) | **唯一事实源入口**：产品、业务流程、功能现状矩阵、行为口径、架构、部署、本地开发、运维脚本 |
| [TODO.md](TODO.md) | **唯一债务与需求台账**（技术债 + 未实现需求，编号 `T-NN` 稳定不复用） |
| [DESIGN.md](DESIGN.md) | **前端视觉与交互规范**：改 Admin/Tenant UI 前必读；`proposed`/`adopting` 均不代表全量落地，不得据此零散替换全局主题 |
| `docs/solutions/` | 踩坑知识库（带 YAML frontmatter，按类目组织）。实施或调试涉及相关领域前先检索 |
| `docs/handovers/2026-07-06-b-instance-operations-manual.md` | B 实例运营操作手册（面向运营的活文档） |

- **优先级：代码 + 测试 > HANDBOOK > 其他。** 发现文档与代码不符时，修文档，不要迁就文档。
- 历史文档（旧工作流产物、specs、会议资料、原型等约 370 份）已于 2026-07 整体清理，考古方式：`git show archive/2026-07-pre-handbook:<路径>`。**不要引用、恢复或参考这些历史文档做实施依据。**

## 2. 工作流

- **只读任务**（分析、review、咨询、运维查询）：直接读取必要上下文完成，无需额外流程。
- **轻量改动**（文档、注释、配置、样式微调）：直接实施。
- **功能开发 / 行为变更 / 重构 / 数据库迁移**：先给出简短方案（改什么、影响面、验证方式），经用户确认后再动手；过程中遇到歧义、冲突、验收标准不清，用 AskUserQuestion 澄清，不允许自行选边或平均。
- **收尾三件事（硬性）**：
  1. 运行与改动匹配的验证（测试 / type-check / 构建 / 手工验收），汇报时附证据；涉及真实业务链路的改动不能只靠单元测试。
  2. 检查 [TODO.md](TODO.md)：完成的条目销账（移入「已销账」并注明证据）；新发现值得单独修的问题即登记（来源 / 缺口 / 验收三要素）。
  3. 行为变更同步 [HANDBOOK.md](HANDBOOK.md) 功能矩阵（§3）与行为口径（§5）；新踩坑沉淀到 `docs/solutions/`。

## 3. 硬性纪律

- **中文**：沟通、注释、提交信息、文档一律中文。
- **不凭记忆写代码或引用路径**——先 grep / read 确认。
- **`.env` 由用户手动维护，禁止自动修改。**
- **生产数据库默认只读**；任何直接或间接写入，必须先展示具体 SQL 与影响范围，取得用户针对该操作的明确确认（操作模式见 `docs/solutions/conventions/production-data-operation-safety.md`）。
- **正式推送镜像、同步线上快照、上线操作都是外部副作用**，必须由用户显式触发，不得因普通实施任务自动执行。
- **多会话并行是常态**：提交作业用 git worktree 隔离（见 `docs/solutions/conventions/multi-session-git-worktree-isolation.md`）；提交时明确列出文件白名单，避免卷入其他会话的 WIP。

## 4. Git 分支与推送

**所有功能开发走分支，其余直接推 main。**

| 方式 | 适用场景 |
| --- | --- |
| 直接推 main | 文档、注释、配置、样式微调等非功能改动 |
| 分支 → PR → 合并 | 新功能、bug 修复、重构、数据库迁移、API 变更 |

分支命名：`feat/<简短描述>`、`fix/<简短描述>`、`refactor/<简短描述>`、`docs/<简短描述>`。合并时机：功能完整可用、本地验证通过即可，不等完美，但不能破坏现有功能。

## 5. 编码规范速览

- 后端分层：api（路由 + 参数 + 权限）→ services（业务逻辑 + 手写 SQL via AsyncConnection，无 ORM 实体层）→ db/pools（连接池 + RLS）。route 层不写业务逻辑。
- 新增入参优先 Pydantic schema，避免 `payload: dict`；新增静态路由必须放在动态 `/{id}` 路由之前。
- Alembic：每次变更一个 revision；涉及前端 API 调用时同步更新 `frontend/packages/shared-api`。
- 前端：服务端状态用 React Query、认证状态用 Zustand；改 UI 前先读 [DESIGN.md](DESIGN.md)；UI 组件一律来自 `@shared/ui`，不在 app 内重复造原语或 Pattern。
- 命名：Python snake_case；TypeScript camelCase 变量 / PascalCase 组件。
- 简洁优先（KISS），不做过度防御性设计、不做无需求的重构。

## 6. 部署与生产操作

完整部署链路、环境变量、多实例说明见 [HANDBOOK.md](HANDBOOK.md) §6–§8。此处只留快捷命令与线上操作经验。

### 6.1 镜像构建（GitHub Actions，正式发布唯一通道）

```bash
gh workflow run build-and-push.yml -f service=backend   # 后端（API + worker 共用镜像）
gh workflow run build-and-push.yml -f service=admin     # Admin 前端
gh workflow run build-and-push.yml -f service=tenant    # Tenant 前端
gh workflow run build-and-push.yml -f service=backend -f tag=hotfix-1   # 自定义 tag
gh run list --workflow=build-and-push.yml --limit 3     # 查看构建状态
```

推送后在 Sealos 控制台更新镜像 tag：`clientget-backend` 与各 worker 应用（如 sending worker）共用同一 backend tag；`clientget-admin` / `clientget-tenant` 各用自己的 tag。本地 `push-*.sh` 与 `docker build` 仅用于调试验证，不作正式发布。

### 6.2 线上 PostgreSQL / Alembic 经验

- Sealos 外部连接串必须显式补业务库名 `/clientget`，否则连到默认 `postgres` 库（没有 `alembic_version`）。
- 连接串不要带 `?directConnection=true`（Mongo 风格参数，psycopg 会报错）。
- backend 镜像 `/start.sh` 启动时自动执行 `alembic upgrade head`；手动迁移只在需要确认或补跑时执行，且执行前先只读确认：

  ```sql
  select current_database(), current_user;
  select version_num from alembic_version;
  ```
