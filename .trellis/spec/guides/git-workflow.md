# Git 工作流

## 分支与 PR

- 新功能、bug 修复、重构、数据库迁移、API 变更：分支 → PR → 合并。分支名 `feat/` `fix/` `refactor/` `docs/` + 简短描述。
- 文档、注释、配置等非功能改动可直推 main。
- 合并时机：功能完整、本地验证通过即可，不等完美，但不得破坏现有功能。
- 提交信息与 PR 描述一律中文；修复类 PR 描述带 `Fixes #NN`（见 delivery-checklist.md）。

## 多会话并行：worktree 隔离

同一台机器常有多个 AI 会话同时工作。任何"改文件 → 提交 → PR"的完整作业不在主检出上做：

```bash
git fetch origin main -q
git worktree add .claude/worktrees/<任务名> -b <分支名> origin/main
# 在 worktree 内编辑、测试、commit、push、gh pr create --head <分支>
git worktree remove .claude/worktrees/<任务名>   # 合并后清理
```

- worktree 统一放 `.claude/worktrees/`（本地 `.git/info/exclude` 已忽略）。
- 提交前用 `git branch --show-current` 确认落点；PR / merge 用 `gh pr create --head` / `gh pr merge`，不 checkout 主检出，HEAD 留给其他会话。
- 无 node_modules 的 worktree 跑不了前端构建：纯字符串级前端改动用 type-check，或回主检出验证；Python 侧不受影响。
- 事故特征：提交输出显示别人的分支名；`git status` 出现非本会话的改动。发现即切到 worktree 模式。

## 提交白名单

提交时显式列出文件（`git add <路径...>`），不用 `git add -A`，避免卷入其他会话的 WIP；提交前 `git status --short` 复核暂存区不含 `.env*`、凭证、客户数据与无关文件。
