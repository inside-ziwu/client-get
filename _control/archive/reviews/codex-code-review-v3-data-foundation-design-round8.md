# Codex Review · design.md · Round 8

## 0. 总体结论

**签字。**

Round 7 要求验证的 5 项修复均已落到 `openspec/changes/v3-data-foundation/design.md`，未发现新的阻塞问题。

本轮重点结论：

- §5.4.1 已改为先锁定 `collection_task_keywords` 最早行，再 `LEFT JOIN openrouter_providers` 取 key；首采租户未配 key 时返回 `None`，不会 fallback 到后续租户。
- §5.4.2 UPDATE 分支已明确“已有 shared_company 永不调 AI”，字段残缺补齐只允许走运维手动回填脚本。
- §9.3 与 §11.2 已统一到 `collection_task_keywords` 反查路径，全文无 `collection_tasks.tenant_id` 旧路径残留。
- §11.2 YAML env 注释不再含 `PLATFORM_OPENROUTER_API_KEY` 变量名；全文仅在“撤销/不需要平台级 key”的否定语义中出现该变量名。
- worker 解密路径已明确为通过 `OPENROUTER_DECRYPT_KEY` 直接解密，不穿透 admin API。

残留阻塞：**无**。

## 1. 5 项验证表

| ID | 状态 ✅/⚠️/🔴 | 证据(行号) |
|---|---|---|
| V7-1 | ✅ | `design.md:1070-1081` 明确 `collection_tasks` 无 `tenant_id`，首采租户来自 `collection_task_keywords` 最早行；`design.md:1094-1099` SQL `SELECT ctk.tenant_id, op.api_key_encrypted` 且 `LEFT JOIN openrouter_providers`，按 `ctk.created_at ASC, ctk.id ASC` 取首位；`design.md:1107-1110` 判 `api_key_encrypted IS NULL` 后直接 `return None`，注释明确不能 fallback 到后续租户。 |
| V7-4 | ✅ | `design.md:1132-1138` UPDATE 分支注释明确“已有 shared_company 永不调 AI”，即使 `product_tags/factory_type` 为 NULL 也不补；`design.md:1137` 明确字段残缺补齐只能走运维手动回填脚本；`design.md:1142-1148` AI 调用仅出现在 INSERT 分支。 |
| V7-3 | ✅ | §11.2 YAML env 注释 `design.md:1463-1492` 只包含 `DATABASE_URL` 与 `OPENROUTER_DECRYPT_KEY`，未出现 `PLATFORM_OPENROUTER_API_KEY`；全文扫描该变量仅命中 `design.md:1174` “不需要”与 `design.md:1401` “撤销之前”两处否定语义。 |
| N7-1 + N7-2 | ✅ | §9.3 `design.md:1395` 写为 `cleanup_queue.task_id → collection_task_keywords (ORDER BY created_at ASC, id ASC LIMIT 1) → first tenant_id → openrouter_providers`；§11.2 YAML 注释 `design.md:1488-1491` 写同一路径；全文扫描无 `collection_tasks.tenant_id` 旧路径，仅 `design.md:1070`、`design.md:1073` 在说明 `collection_tasks` 无 `tenant_id`。 |
| N7-4 | ✅ | §9.3 `design.md:1396` 明确 cleanup_service worker 通过 k8s secret `OPENROUTER_DECRYPT_KEY` 直接解密 `openrouter_providers.api_key_encrypted`，并加粗说明“不通过 admin API 层穿透”；§11.2 `design.md:1483-1487` YAML 也声明 worker 使用 `OPENROUTER_DECRYPT_KEY` 解密。 |

## 2. 新引入问题（如有）

未发现新的阻塞问题。

本轮额外扫到的非阻塞确认点：

- `design.md:1088` 仍出现 `INNER JOIN openrouter_providers`，但语义是“不能用 INNER JOIN”的禁止说明，不是 SQL 实现残留。
- `design.md:1174` 与 `design.md:1401` 仍出现 `PLATFORM_OPENROUTER_API_KEY`，但均为“不需要/撤销之前”的否定语义，符合本轮验收口径。
- `design.md:1166` 与 `design.md:1527` 再次强化同一 shared_company 重复采集走 UPDATE 分支跳过 AI、后续租户不会补齐已有字段，与 §5.4.2 保持一致。
- `design.md:790-797` 的 task 内 fan-out 使用 `collection_task_keywords` 参与租户映射，没有回退到 `collection_tasks.tenant_id`。

因此，Round 7 的 5 项 finding 已关闭。

### 2.1 V7-1 细化核验

SQL 层已满足“先选首采租户，再看该租户是否有 key”的语义。

- `design.md:1094` 同时选出 `ctk.tenant_id` 与 `op.api_key_encrypted`。
- `design.md:1095-1096` 从 `collection_task_keywords ctk` 出发，使用 `LEFT JOIN openrouter_providers`。
- `design.md:1097-1099` 仅按 `ctk.task_id` 过滤，并按 `ctk.created_at ASC, ctk.id ASC` 取首位。
- 该写法不会因为首采租户未配置 OpenRouter 而过滤掉首采租户行。

代码层也已满足“不 fallback 后续租户”的语义。

- `design.md:1103-1105` 处理 task 无关联租户的异常情况，返回 `None`。
- `design.md:1107-1110` 处理首采租户无 `api_key_encrypted` 的情况，返回 `None`。
- 注释明确说明不能 fallback 到后续租户，否则破坏首采付费模型。

### 2.2 V7-4 细化核验

UPDATE 分支已从“机会性补齐 AI 字段”改为“永不调 AI”。

- `design.md:1132` 进入 `if existing:` 分支后直接走已有 shared_company 处理。
- `design.md:1133-1136` 明确即使 AI 字段仍为 NULL，cleanup 也不补。
- `design.md:1137` 将补齐责任限定到运维手动回填脚本。
- `design.md:1142-1148` 显示 `_get_task_first_tenant_openrouter_key()` 与 AI enrich 只在 INSERT 分支出现。

这与 R10 的一次性回填边界一致：`design.md:1527` 明确后续租户不会补齐已有 shared_company 字段。

### 2.3 V7-3 / N7-1 / N7-2 细化核验

YAML 注释已按 worker 实际运行模型重写。

- §11.2 共享 env 行 `design.md:1465` 仅列 `DATABASE_URL / OPENROUTER_DECRYPT_KEY`。
- env 列表 `design.md:1481-1484` 只配置数据库连接与解密 key。
- `design.md:1488-1491` 明确路径为 `cleanup_queue.task_id → collection_task_keywords → first tenant_id → openrouter_providers LEFT JOIN`。

全文残留扫描结果：

- 未发现 `collection_tasks.tenant_id` 旧路径。
- 未发现 `existing.product_tags is None` 旧补齐条件。
- 未发现 §11.2 YAML 内 `PLATFORM_OPENROUTER_API_KEY`。
- `PLATFORM_OPENROUTER_API_KEY` 仅在正文否定语义中保留，作用是提醒撤销旧平台级 key 决策。

### 2.4 N7-4 细化核验

worker 解密路径已经从“复用 admin 端解密能力”的模糊说法，收敛为 worker 自己可执行的部署路径。

- §9.3 `design.md:1396` 写明 worker 通过 k8s secret `OPENROUTER_DECRYPT_KEY` 解密。
- 同一行写明解密对象是 `openrouter_providers.api_key_encrypted`。
- 同一行写明“不通过 admin API 层穿透”。
- §11.2 `design.md:1483-1487` 与安全章节保持一致，给出实际 env 配置。

## 3. 无技术背景版摘要

1. 这次修复把“谁付 AI 费用”的规则落稳了：系统先找最早触发采集的租户，如果这个租户没配 OpenRouter，就不生成 AI 字段，而不是改用后面租户的 key。

2. 已有公司数据不会因为后续租户再次采集而偷偷补 AI 字段；如果历史字段缺失，只能由运维明确选择 key 和付费方后手动回填。

3. 部署说明也同步清理了旧口径：不再配置平台级 OpenRouter key，worker 自己拿解密 key 读租户级密文，不绕 admin API。

## 4. 原始需求 → 已实现/未实现 对照清单

| 原始需求 | 已实现/未实现 | 证据 |
|---|---|---|
| V7-1：§5.4.1 SQL 改 `LEFT JOIN`，SELECT 含 `ctk.tenant_id`，代码判 NULL 返回 None，不 fallback 后续租户 | 已实现 | `design.md:1094-1110` |
| V7-4：§5.4.2 删除 UPDATE 分支 AI 补全代码块，注释明确 UPDATE 永不调 AI，补齐走运维手动脚本 | 已实现 | `design.md:1132-1138`、`design.md:1142-1148` |
| V7-3：§11.2 YAML env 注释不再含 `PLATFORM_OPENROUTER_API_KEY` 变量名，除撤销/否定语义 | 已实现 | `design.md:1463-1492`；否定语义残留见 `design.md:1174`、`design.md:1401` |
| N7-1 + N7-2：§9.3 与 §11.2 YAML 改为 `collection_task_keywords ORDER BY created_at ASC LIMIT 1` 路径 | 已实现 | `design.md:1395`、`design.md:1488-1491` |
| N7-1 + N7-2：全文无 `collection_tasks.tenant_id` 旧路径 | 已实现 | `rg` 仅命中“无 tenant_id 字段”的说明行 `design.md:1070`、`design.md:1073` |
| N7-4：worker 解密路径明确通过 `OPENROUTER_DECRYPT_KEY` 直接解密，不穿透 admin API | 已实现 | `design.md:1396`、`design.md:1483-1487` |
