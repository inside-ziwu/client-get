# 质量与验证

> 事实来源：`pyproject.toml`、`tests/`（45 文件 / 307 用例，2026-07 基线）、原 docs/solutions/conventions 的「SQL 语义验证」与「sanitize 三张清单」约定（已迁入本文并删除原文件）。

## 门禁

- `cd backend && uv run pytest -q`：全 mock，无真库也能跑；5 个可选真库用例在未设 `TEST_DATABASE_URL` 时 skip。
- `ruff`（`select = E, F, I, UP, B, C4, SIM`，行宽 100，目标 py311）；**无 mypy**。
- CI 只构建镜像、不跑测试（#50）——本地门禁是唯一门禁，收尾必须附输出。
- 已知失效命令（修复前不得作为门禁）：前端根 `pnpm lint`（#50）、tenant `test:contract`（#56）。

## 测试模式

- `tests/conftest.py` 只设环境变量默认值；`Settings(...)` 在用例里显式构造（`test_sending_worker.py::_settings`）。
- 连接替身：`MagicMock()` 的 `execute` 返回 `_result(first=..., all_rows=...)`，断言 SQL 文本片段与参数；`engine.begin()` 用自定义 `_Begin` 上下文。
- 时间：注入 `clock` callable；不用 freezegun。
- 真库可选用例：读 `TEST_DATABASE_URL`，在事务内建 TEMP 表并回滚（`test_lineage_repair_postgres.py`），没有连接串就 `pytest.skip`。
- 迁移测试：对破坏性迁移写原子回滚用例（`test_drop_retired_collection_tables_migration.py`）。
- 隔离测试族：`test_*_instance_isolation.py`、`test_*_no_visibility.py`——改隔离逻辑必须保留 / 新增。
- 源码级断言（`inspect.getsource` 检查某逻辑已移除）是本仓库接受的"退役锁定"手法。

## 真库验证纪律

mock 只能断言"SQL 文本包含什么、参数是什么、返回值怎么映射"，验证不了 SQL 语义。以下改动**必须**在 Neon 开发库做可回滚的断言式验证（`/db-verify` 技能，三段式：借外键 → 事务内断言 → ROLLBACK 复核零残留），执行记录作为收尾证据：

- SQL 口径（FILTER、聚合、窗口边界）、多表联动写路径；
- 时区 / 发送窗口 / 北京自然日；
- 状态机推进（条件更新行数、RETURNING）；
- 分区表操作、`ON CONFLICT` 语义。

值得留的断言转正为 `tests/` 里的 mock 用例 + 执行记录。

## 禁止模式

- `payload: dict` 裸收参；service 省略 `tenant_id` / `instance_id` 过滤。
- SQL 端写时区表达式；向 timestamptz 范围传裸 date。
- `:param::type` 写法；凭记忆写列清单。
- 改 sanitize / 转义行为却不盘点三张清单：**写入点**（谁调 sanitize 入库）、**存量面**（SQL 统计历史数据是否带旧行为痕迹）、**出口**（grep 所有外发调用，如 `send_test_email`）。新增发送出口必须与 `claim_due_emails` 同序 sanitize（`sanitize_html → text fallback → sanitize_plain_text → sanitize_subject`），防回归见 `tests/test_send_test_email_sanitize.py`。
- 无需求的重构、过度防御（KISS）。

## 代码评审清单

- [ ] 分层正确，route 无业务逻辑
- [ ] 隔离过滤显式存在且有测试
- [ ] 迁移：一个 revision、FK 链核对、带数据预演
- [ ] 响应结构变化已同步前端类型
- [ ] 日志无凭证与客户数据
- [ ] 验证证据齐全，失败与未验证项如实列出
