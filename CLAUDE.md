# CLAUDE.md

> Claude Code 专用补充约束。**先读 [AGENTS.md](AGENTS.md)（最高约束）与 [HANDBOOK.md](HANDBOOK.md)（唯一事实源）**；本文件只补充 Claude 特有项。

## 1. 行为要求

- 输出语言：中文（Implementation Plan, Task List and Thought in Chinese）。注释、提交信息、文档全部中文。
- 实施前如有歧义、冲突、缺口或验收标准不清，先用 AskUserQuestion 工具澄清，再动手。
- 收尾时输出「原始需求 → 已实现 / 未实现」对照，并附验证证据（测试输出、type-check、手工验收记录）。
- 不凭记忆引用文件路径或系统行为——先 grep / read；行为口径以 [HANDBOOK.md](HANDBOOK.md) §5 与代码为准。
- 收尾三件事（销账 TODO、同步 HANDBOOK、沉淀 solutions）见 [AGENTS.md](AGENTS.md) §2，不得跳过。

## Skill routing

When the user's request matches an available skill, invoke it via the Skill tool. When in doubt, invoke the skill.

Key routing rules:
- Product ideas/brainstorming → invoke /office-hours
- Strategy/scope → invoke /plan-ceo-review
- Architecture → invoke /plan-eng-review
- Design system/plan review → invoke /design-consultation or /plan-design-review
- Full review pipeline → invoke /autoplan
- Bugs/errors → invoke /investigate
- QA/testing site behavior → invoke /qa or /qa-only
- Code review/diff check → invoke /review
- Visual polish → invoke /design-review
- Ship/deploy/PR → invoke /ship or /land-and-deploy
- Save progress → invoke /context-save
- Resume context → invoke /context-restore
