# 收尾清单

任务结束前三件事，一件不能省。Trellis 的 `/trellis:finish-work` 负责 spec 更新与任务归档，本清单补本项目特有动作。

## ① 验证证据

- 跑与改动匹配的验证并把输出附在收尾说明里：`uv run pytest -q`、`pnpm type-check`、tenant Vitest、Neon 真库断言记录、手工验收记录。
- 如实报告失败与未验证项；"未验证"要写明原因。
- 涉及行为口径、SQL 语义、时区、状态机的改动，没有真库断言不算完成。

## ② Issues 销账

- GitHub Issues 是唯一债务台账（`gh issue list`，P0–P3 label）。
- 修复 PR 描述带 `Fixes #NN`，合并自动关闭；无 PR 的用 `gh issue close` 并附证据。
- 新发现值得单独修的问题：`gh issue create`，写明来源 / 缺口 / 验收，打优先级 label；不在代码里留 TODO 代替。

## ③ 文档与 spec 同步

- 行为变更：更新 [../backend/domain-rules.md](../backend/domain-rules.md)（口径表）与 README §3 功能现状矩阵对应行。
- schema 变更：重跑 `scripts/schema_snapshot.py` 提交快照；`docs/database-schema.md` 在发布后按生产快照再生。
- 新教训 / 新约定：写进对应 spec 的「常见错误」或规则节（`trellis-update-spec`）；**不再新增 `docs/solutions/` 文件**（该目录已冻结为历史档案）。
- 发现 spec / README 与代码不符：以代码 + 测试为准，改文档。
