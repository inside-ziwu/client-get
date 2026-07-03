---
title: 多个 AI 会话共用仓库时,一律用 git worktree 隔离作业
date: 2026-07-03
category: conventions
module: development_workflow
problem_type: convention
component: development_workflow
severity: high
applies_when:
  - "同一台机器上有多个 Claude/AI 会话同时在这个仓库工作"
  - "任何会话需要建分支、提交、切换 HEAD"
tags: [git-worktree, multi-session, branch-safety, shared-checkout]
---

# 多个 AI 会话共用仓库时,一律用 git worktree 隔离作业

## Context

两个 Claude 会话并行工作在同一个主检出(`/Users/lay/Documents/Projects/client_get`)时发生过真实事故:会话 A 建了自己的分支,会话 B 在两次命令之间切走了 HEAD,A 的提交落到了 B 的分支上并被误推远端。事后靠"branch -f 搬提交 + reset 还原对方分支 + 删误推远端"外科手术恢复,有数据风险。

## Guidance

**任何会话要做"改文件 → 提交 → PR"的完整作业时,不在主检出上操作,而是创建独立 worktree:**

```bash
git fetch origin main -q
git worktree add .claude/worktrees/<任务名> -b <分支名> origin/main
# ... 在 worktree 目录内编辑、测试、commit、push、PR ...
git worktree remove .claude/worktrees/<任务名>   # 合并后清理
```

配套纪律:

- worktree 统一放 `.claude/worktrees/` 下,和 EnterWorktree 工具的目录一致,便于识别与清理;
- 提交前用 `git branch --show-current` 或提交输出的 `[分支名 hash]` 前缀**确认落点**;
- PR/merge 用 `gh pr create --head <分支>` / `gh pr merge <分支>`,全程不需要 checkout,主检出的 HEAD 留给对方会话;
- 无本地 node_modules 的 worktree 跑不了前端构建——纯字符串级前端改动用 type-check 或在主检出验证,Python 侧全局 site-packages 不受影响。

## Why This Matters

主检出的 HEAD 是所有共用会话的单点共享状态:任何一方 `checkout`/`reset` 都会瞬间改变另一方的世界。worktree 让每个会话拥有独立的 HEAD 和工作区,冲突面直接归零;事故恢复成本(危险的历史手术)远高于每次 30 秒的 worktree 创建。

## When to Apply

- 明确知道或怀疑有另一个会话/终端在同一仓库工作时(如端口被占、出现陌生分支、工作区出现非本会话的改动)——立即切换到 worktree 模式;
- 单会话独占仓库时可以直接在主检出作业,但建分支后要留意用户或工具是否会切换 HEAD。

## Examples

事故特征(据此识别):提交输出显示 `[<别人的分支名> <hash>]`;`git status` 出现非本会话的未跟踪/修改文件;`git checkout -b` 输出里带 `M <文件>` 的携带列表。

恢复手术(万不得已才用):`git branch -f 自己的分支 <提交>` → push 自己的分支 → `git push origin :误推分支` → 在对方分支上 `git reset --hard <提交>^`。
