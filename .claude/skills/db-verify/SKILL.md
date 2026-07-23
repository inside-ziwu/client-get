---
name: db-verify
description: ClientGet 真库验证：Neon 开发库断言（SQL 语义/状态机，事务回滚零残留）与生产库只读体检/取证（强制 read_only、对照组设计）。当用户要求真库断言、开发库冒烟、生产数据体检、数据侧取证、验证 SQL 语义时使用。生产写操作不属本技能默认范围，须走文末协议逐次确认。
---

# ClientGet 真库验证（DEV 断言 / PROD 只读体检）

固化自 2026-07-23 实践（幂等闸门断言、别名遮蔽验证、&amp; 污染体检与清洗）。何时必须真库验证的**约定**见 `docs/solutions/conventions/sql-semantics-verification-under-pure-mock-tests.md`（本技能只管怎么执行，不复述判据）。

## 连接纪律（不可协商）

- 两条连接都在 `backend/.env.local`（用户手维护，禁改）；脚本内读取，**URL 与凭证不得打印**（展示时打码 `:****@`）。
- `CLIENTGET_DEV_DATABASE_URL`（Neon）：可写可断言。psycopg **直连、不带 startup options**（Neon pooler 会拒绝，见 `docs/solutions/database-issues/neon-pooler-rejects-startup-options-use-psycopg-read-only.md`）。
- `CLIENTGET_PROD_DATABASE_URL`（Sealos 生产）：连接后**立即 `conn.read_only = True`** 作技术兜底；任何写入不属本技能默认范围，见文末协议。

## DEV 断言模式（三段式，事务内零残留）

1. **借外键**：`SELECT` 现有行取 tenant/enrollment/contact 等 FK 值，不修改原行；库空则报告改走造链，不硬造。
2. **断言**：单事务内 INSERT 测试行（新 uuid 主键）→ 执行与线上**逐字一致**的 SQL → 断言行为（条件更新行数、RETURNING、状态门槛）。并发互斥语义用条件更新的行数差断言，不开双连接。
3. **回滚复核**：`ROLLBACK` 后按测试标记（专用 locked_by / subject 值）查 count=0，证据写进输出。
- 脚本放 scratchpad（一次性）；值得留的断言转正为 `backend/tests/` mock 测试 + 本模式的执行记录。

## PROD 只读体检模式

- 聚合 + 时间窗过滤（分区裁剪），禁止无窗口 `LIKE` 拖全表；样本输出截断、不含收件人邮箱等客户数据。
- **对照组设计**防假阴性：断言「期望消失的模式归零」时，必须同时验证「正常模式仍出现」（例：`&amp;` 归零 + 裸 `&` 仍在）；窗口无产出时如实标 pending，不硬凑。
- 版本疑问先用 openapi 指纹排除「容器没更新」（见 release skill 部署后验证节）。

## PROD 写操作协议（超出默认范围，逐次授权）

1. 只读预览 before/after 与精确影响行数；2. 向用户展示完整 SQL + 预告行数，**等明确确认**；3. 事务内执行，`rowcount ≠ 预告值即回滚`并报告；4. 提交后立即只读复核并抽查。先例：2026-07-23 模板 `&amp;` 清洗（7 行 replace）。
