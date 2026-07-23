---
name: ship-fix
description: ClientGet 修复/小功能的标准闭环：worktree 隔离 → 门禁验证 → 规范分支 → PR → 合并 → 无残留清场。当用户要求修 bug 并走完流程、提交 PR、走闭环、ship、收尾合并时使用。改动本身完成后才进入本流程。
---

# ClientGet 修复闭环（worktree → PR → 合并 → 清场）

2026-07-23 单日跑通 5 次（PR #86/#88/#89/#90/#92）后固化。目标：每次闭环零残留、验证证据齐全、下一个会话看到的工作区与分支清单严格等于「main + 用户明示保留项」。

## 授权边界

- 用户要求「修复并闭环/直接修」＝ 授权到合并；用户只说「修复」＝ PR 创建后停下等合并指令。
- AGENTS.md 全部红线仍适用：生产库只读、外部副作用显式触发、`.env` 不改。

## 流程

1. **隔离**：`EnterWorktree`（项目纪律：提交作业用 worktree 隔离）。多逻辑改动拆多 commit 预先规划。
2. **门禁**（按改动范围，证据留给 PR）：
   - backend：`uv run --extra dev pytest -q`（worktree 首次运行自动装依赖，dev 依赖在 optional-dependencies，必须带 `--extra dev`）；
   - frontend：`pnpm install --frozen-lockfile` 后 `pnpm type-check` + 相关 app 测试；
   - SQL 语义 / 状态机 / 时区窗口：按 `docs/solutions/conventions/sql-semantics-verification-under-pure-mock-tests.md` 做 Neon 开发库断言（DEV url 在 backend/.env.local）。
3. **分支规范化**：`git branch -m <fix|feat|refactor|docs>/<短描述>`——EnterWorktree 默认的 `worktree-` 前缀不合项目命名约定，必须改名（改名的清理后果见第 6 步）。
4. **提交**：中文提交信息（现象 → 根因 → 方案，含关键数据），结尾 `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`。
5. **PR**：`git push -u origin <分支>` → `gh pr create`，正文含问题背景、修复方式、验证证据（测试计数、真库断言结果），修 issue 带 `Fixes #NN`，尾部 `🤖 Generated with [Claude Code](https://claude.com/claude-code)`。合并用项目惯例 `gh pr merge <N> --merge`（merge commit，非 squash）。
6. **清场序列**（顺序固定，一步不可省）：
   1. `gh pr view <N> --json state` 确认 MERGED；
   2. `ExitWorktree(remove)`——提示 discard 时先核实提交已是 origin/main 祖先再带 `discard_changes`；
   3. `git push origin --delete <分支>`；
   4. `git pull --ff-only`（先 pull 再删本地分支，否则 `-d` 会被未合并保护误拦）；
   5. **`git branch --list` 清点并 `git branch -d` 残留分支**——ExitWorktree 只删它创建时的 `worktree-*` 原名，第 3 步改名后的分支必然残留（2026-07-23 两次踩坑后立此门禁）；只用 `-d` 不用 `-D`，借未合并保护做最后校验。
7. **收尾三件事**（AGENTS.md §4）：验证证据已在 PR；债务销账（`Fixes #NN` 或 `gh issue create` 登记新发现，P0–P3 label）；行为变更同步 README 状态表、新踩坑沉淀 docs/solutions/。
8. **交付提醒**：合并 ≠ 上线——影响生产行为的改动需随下次 `/release` 发布生效，报告里明示。
