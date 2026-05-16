# Codex Review · design.md · Round 7

## 0. 总体结论

**不签字。**

本轮 4 项验证里，函数命名已统一，§5.4.1 的 schema 方向也改对了：`collection_tasks` 无 `tenant_id`，应通过 `collection_task_keywords.task_id` 反查租户，且 `ctk.created_at ASC, ctk.id ASC` 有 schema 字段支撑。

但仍有 3 个阻塞：

1. **§5.4.1 SQL 语义仍不正确**：当前 `JOIN openrouter_providers` 会跳过未配置 OpenRouter 的首采租户，可能错误改用后续租户的 key，破坏“最早加入者付费 / 未配则字段 NULL”的业务模型。
2. **§9.3 与 §11.2 仍残留 `collection_tasks.tenant_id` 旧路径**：与 §5.4.1 和真实 schema 冲突。
3. **§11.2 YAML 注释仍残留 `PLATFORM_OPENROUTER_API_KEY`**：虽然不是 env name，但本轮要求是“共享 env 注释不再残留”，目前仍未满足。

## 1. 4 项验证表

| ID | 状态 | 证据（行号） |
|---|---|---|
| V7-1 | ⚠️ 部分通过，仍阻塞 | `design.md:1070-1075` 已明确 `collection_tasks` 无 `tenant_id`，多租户通过 `collection_task_keywords`；`design.md:1091-1096` 从 `ctk.task_id` 反查并按 `ctk.created_at ASC, ctk.id ASC` 排序；schema 支撑见 `schema.sql:352-372`、`schema.sql:378-384`。但 `design.md:1092-1094` 使用 `JOIN openrouter_providers`，首采租户未配 key 时会被过滤，可能取到后续租户 key。 |
| V7-2 | ✅ 通过 | `rg` 仅命中 `_get_task_first_tenant_openrouter_key`：`design.md:1010`、`1084`、`1128`、`1137`；无 `_get_task_tenant_openrouter_key` 残留。 |
| V7-3 | ❌ 未通过 | §11.2 YAML 注释仍有 `PLATFORM_OPENROUTER_API_KEY`：`design.md:1481`、`1484`；全篇另有 `design.md:1168`、`1395`。本轮要求重点是 §11.2 YAML 共享 env 注释不再残留，当前不满足。 |
| V7-4 | ⚠️ 部分通过，仍需修 | “最早加入者付费 + 后续租户复用免费”的业务模型在 `design.md:1050-1065`、`1077-1081` 写清楚；R10 也写了未配 key 留 NULL、后续租户不补齐：`design.md:1520`。但 §5.4.2 UPDATE 分支又允许已有 shared_company 字段为 NULL 时用当前 task key 补全：`design.md:1124-1131`，与“一次性回填 / 后续不补齐”冲突。 |

## 2. 关键问题 A/B/C 分析

### A. `collection_task_keywords` 反查是否对

**方向正确，但 SQL 需要改。**

真实 schema：

- `collection_tasks` 定义在 `schema.sql:352-372`，字段包括 `id`、`keyword`、`keyword_normalized`、`status`、lease、时间戳等，**没有 `tenant_id`**。
- `collection_task_keywords` 定义在 `schema.sql:378-384`，包含 `id`、`task_id`、`keyword_id`、`tenant_id`、`created_at`。
- `task_id` 外键指向 `collection_tasks(id)`：`schema.sql:380`。
- `created_at` 与 `id` 都存在，支持 `ORDER BY ctk.created_at ASC, ctk.id ASC`：`schema.sql:379`、`383`。

因此，`collection_tasks.id ← collection_task_keywords.task_id` 关联是正确建模。

问题在 `design.md:1091-1096`：

```sql
SELECT op.api_key_encrypted
FROM collection_task_keywords ctk
JOIN openrouter_providers op ON op.tenant_id = ctk.tenant_id
WHERE ctk.task_id = $1
ORDER BY ctk.created_at ASC, ctk.id ASC
LIMIT 1
```

这个 SQL 取到的是“最早且已配置 OpenRouter 的租户”，不是“最早加入 task 的租户”。

极端但本轮明确要求覆盖的场景：

1. A 最早加入 task，`ctk.created_at=T1`，但 A 未配 OpenRouter。
2. B 后加入 task，`ctk.created_at=T2`，B 已配 OpenRouter。
3. 当前 SQL 因 `JOIN openrouter_providers` 过滤掉 A，返回 B 的 key。
4. 结果：B 被错误计费，且 AI 字段被补齐；这与 R10 “首采租户未配 OpenRouter → 字段 NULL”冲突。

建议语义应为：

```sql
SELECT ctk.tenant_id, op.api_key_encrypted
FROM collection_task_keywords ctk
LEFT JOIN openrouter_providers op ON op.tenant_id = ctk.tenant_id
WHERE ctk.task_id = $1
ORDER BY ctk.created_at ASC, ctk.id ASC
LIMIT 1
```

然后在代码里判断 `api_key_encrypted IS NULL`，返回 `None`，而不是继续找后续租户。

### B. 业务模型完整性

**A 配 / B 后配同关键词时，cleanup_service 目前不能稳定锁定 A 作为付费者。**

如果 A 已配置 OpenRouter，当前 SQL 会返回 A，语义正确。

如果 A 未配置 OpenRouter、B 已配置 OpenRouter，当前 SQL 会返回 B，语义错误。

如果 A 和 B 都未配置 OpenRouter，当前 SQL 返回空，表现与“字段 NULL”一致，但这是偶然成立。

所以当前实现说明不足以支撑“首采租户精确锁定”。需要把“选首采 ctk 行”和“取 OpenRouter key”解耦，避免 key 表 join 改变付款人选择。

此外，`design.md:1124-1131` 的 UPDATE 分支允许已有 shared_company 缺 AI 字段时，用当前 task 触发租户 key 补全。这会把“后续租户复用免费”变成“后续触发者可能补账付费”，与 `design.md:1520` 的一次性模型冲突。

如果业务决策是“一次性回填，后续不补齐”，那么 UPDATE 分支应明确：

- 已有 shared_company：不调 AI。
- 即使 `product_tags` / `factory_type` 为 NULL，也不在普通 cleanup 中补齐。
- 需要补齐时只允许运维手动回填脚本，并明确付款 / key 来源。

### C. 退化情况

**C1. 同 task 多租户 `created_at` 相同**

`ORDER BY ctk.created_at ASC, ctk.id ASC` 合理。

schema 支持：

- `ctk.id uuid PRIMARY KEY`：`schema.sql:379`
- `ctk.created_at timestamptz NOT NULL DEFAULT now()`：`schema.sql:383`

UUID 排序不是业务顺序，但在 `created_at` 完全相同时可作为稳定 tie-breaker，至少保证幂等和可复现。若未来要更严格，可引入显式 sequence；本轮不阻塞。

**C2. 首采租户未配 OpenRouter**

文档目标正确：

- `design.md:1100-1103` 写“首采租户未配 OpenRouter / ctk 异常缺失 → 跳过 AI 回填，字段留 NULL”。
- `design.md:1154-1156` 写失败兜底字段留 NULL。
- `design.md:1520` R10 也写首采租户未配 / 余额耗尽 → 字段留 NULL。

但 SQL 当前不能保证该目标。必须改为 `LEFT JOIN` 或先取首采 `tenant_id` 再查 key。

**C3. 后续租户配 OpenRouter 后不补齐**

R10 写得正确：`design.md:1520` 明确后续租户配 OpenRouter 不会补齐已有 shared_company 字段。

但 §5.4.2 冲突：`design.md:1124-1131` 在 UPDATE 分支允许字段 NULL 时用当前 task key 补齐。

这会引入两个问题：

- 破坏“一次性回填”。
- 让后续租户可能为历史 shared_company 的 AI 字段付费。

该段必须改成“UPDATE 分支永不调 AI；补齐只能走运维手动回填脚本”。

## 3. 新引入问题（如有）

### N7-1. §9.3 仍使用不存在的 `collection_tasks.tenant_id`

`design.md:1389` 写：

```text
cleanup_queue.task_id → collection_tasks.tenant_id → 取该租户 key
```

这与 §5.4.1 的修订和 schema 冲突。应改为：

```text
cleanup_queue.task_id → collection_task_keywords(task_id) ORDER BY created_at ASC, id ASC → first tenant_id → openrouter_providers
```

### N7-2. §11.2 YAML 注释仍使用旧路径

`design.md:1483` 写：

```text
openrouter_providers 表查 cleanup_queue.task_id → collection_tasks.tenant_id 对应行
```

这同样应改成 `collection_task_keywords` 首行反查。

### N7-3. `PLATFORM_OPENROUTER_API_KEY` 注释残留

本轮要求 §11.2 yaml 共享 env 注释不再残留 `PLATFORM_OPENROUTER_API_KEY`。

当前 §11.2 仍残留两处：

- `design.md:1481`
- `design.md:1484`

全篇保留“撤销平台级 key”的正文说明可以接受，但 §11.2 YAML 示例不应继续携带旧变量名，否则部署者仍会误以为需要配置该 secret。

### N7-4. key 解密路径表述仍偏乐观

`design.md:1390` 写“复用 openrouter_providers 现有解密路径（admin 端解密能力本 change 沿用）”。

本轮不展开审实现，但这里至少应提醒：cleanup_service 是 worker，不是 admin API；设计应明确 worker 能否访问同一解密工具与 `OPENROUTER_DECRYPT_KEY`，避免实现时临时穿透 admin 层。

## 4. 无技术背景版摘要

这轮改动把“从采集任务找到租户”的大方向修对了：任务表本身没有租户字段，确实应该去任务-关键词关联表里找。

但现在还有一个关键漏洞：文档里的 SQL 会先过滤“配了 OpenRouter 的租户”，再选最早的。这样会出现 A 最先采集但没配 key，B 后来配了 key，系统却拿 B 的 key 去付费的情况。这不符合“谁最先采集谁付费；如果他没配，就不生成 AI 字段”的规则。

另外，部署 YAML 注释和安全章节还残留旧说法，仍写成从 `collection_tasks.tenant_id` 找租户，还出现 `PLATFORM_OPENROUTER_API_KEY` 旧变量名。§5.4.2 还允许后续租户补齐 AI 字段，也和“后续复用免费、不补齐”冲突。

结论：**Round 7 不能签字**。需要先修正 SQL 为先锁定首采租户，再查 key；清掉 §9.3 / §11.2 的旧路径；并统一 UPDATE 分支不再调 AI。
