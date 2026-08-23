# 通用指南（跨层）

> 这些指南不属于某一层，但每次编码前都要过一遍；`trellis-before-dev` 默认读取本文件。安全红线见 [AGENTS.md](../../../AGENTS.md) §1。

| 指南 | 用途 | 何时用 |
|---|---|---|
| [cross-layer-thinking-guide.md](./cross-layer-thinking-guide.md) | 一次改动在 DB → service → API → 类型 → 页面之间要同步的事，以及边界问题清单 | 功能横跨多层时 |
| [code-reuse-thinking-guide.md](./code-reuse-thinking-guide.md) | 本仓库已有的可复用件与抽取时机 | 发现自己在重复写东西时 |
| [git-workflow.md](./git-workflow.md) | 分支 / PR 规则、多会话 worktree 隔离、提交白名单 | 任何提交前 |
| [delivery-checklist.md](./delivery-checklist.md) | 收尾三件事：验证证据、Issues 销账、文档与 spec 同步 | 任务结束 |
| [production-operations.md](./production-operations.md) | 生产库只读默认、写操作三段式、备份恢复、发布、日志取证 | 运维 / 数据操作 |

## 思考触发器

- 改了一张表的列 → cross-layer：迁移、结构快照、service SQL、序列化、shared-types、页面、测试。
- 改了"发出去"的内容（邮件、webhook、导出）→ 写入点 / 存量面 / 出口三张清单。
- 多个写入方推进同一状态列 → 幂等闸门放单写入方的表。
- 涉及日期 / 时区 → Python 端算好传参，带时区 datetime。
- 涉及两实例 → `instance_id` 过滤 + 实例级锁 + 按实例的开关。
- 想写一个新表格 / 分页 / 筛选 → 先看 `@shared/ui` 五件套。
- 要动生产库 → production-operations.md 三段式，先取得用户确认。
