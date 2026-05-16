# Wave 2 代码审查报告

**审查日期**：2026-05-07  
**审查人**：code-reviewer agent（Claude Sonnet 4.6）  
**代码根**：`backend/` + `frontend/`  
**对应 Gate**：Gate 6（涉及数据库/worker/邮件/tenant 改动，必须有 Codex review）

---

## 一、总体结论

**发现 2 个 major 问题，已修复后方可部署。** 无 critical（安全）级别问题。所有 minor 问题不阻塞部署。

**修复状态**：M-1 / M-2 已在同次 session 修复并 commit。

---

## 二、逐文件/模块审查结论

### 2.1 Alembic 迁移

| 文件 | 结论 | 说明 |
|---|---|---|
| `0016_keyword_master_tables.py` | WARN | 重复唯一索引（见 §3.1，minor，不阻塞） |
| `0017_collection_keywords_master_fk.py` | PASS | 数据回填逻辑正确，UPSERT 幂等，downgrade 路径完整 |
| `0020_emails_tracking_fields.py` | PASS | D-041 字段定义合理，downgrade 完整，条件索引设计合理 |
| `0021_email_events_index.py` | PASS | merge point tuple 格式正确，downgrade 完整 |
| `0025_tenant_companies_private_fields.py` | PASS | CHECK 约束正确，downgrade 完整 |
| `0026_scoring_templates_industry.py` | PASS | downgrade 完整 |
| `0027_tenant_scoring_weights.py` | PASS | RLS 使用已有 `current_tenant_id()` 函数，`trigger_set_updated_at` 已在 canonical schema 确认存在 |
| `0029_contact_classification_tables.py` | PASS | `%%` 转义正确（psycopg placeholder），downgrade 完整 |

**迁移 DAG**：主链 0016→0017→0025→0026→0027；分支 0016→0029→0020；merge 0021(0027,0020)，合法，无循环依赖。

### 2.2 后端服务

| 文件 | 结论 | 说明 |
|---|---|---|
| `keyword_service.py` | PASS | 归一化幂等，参数化 SQL 无注入风险 |
| `contact_classification_service.py` | PASS | CRUD 完整，幂等 |
| `tenant_scoring_weights_service.py` | WARN | f-string SQL 拼接（见 §3.3，minor，不阻塞） |
| `fan_out.py` | **FAIL→已修复** | EXISTS 子查询未关联关键词与公司（见 §3.4，major） |
| `sending.py` | PASS | error_code/error_message 正确传入 mark_email_failed |
| `admin_collection_service.py` | PASS | D-035 白名单 400 路径正确 |
| `tenant_messaging_service.py` | **FAIL→已修复** | mark_email_failed 未写 error_code/error_message（见 §3.5，major） |
| `webhook_service.py` | WARN | occurred_at_open fallback key 名错误（见 §3.6，minor，不阻塞） |
| `tenant_service.py` | PASS | create_tenant 写 domain_warmup_status 正确，ON CONFLICT DO NOTHING 幂等 |

### 2.3 API 层

| 文件 | 结论 | 说明 |
|---|---|---|
| `admin/collection.py` | PASS | TriggerCollectionRequest 正确，路由完整 |
| `admin/contact_classification.py` | PASS | 路由完整，已注册到 admin router |

### 2.4 前端

| 文件 | 结论 | 说明 |
|---|---|---|
| `CollectionTasks/index.tsx` | PASS | renderDirectActions 已删除，无遗留引用，D-035 禁用逻辑正确 |
| `ContactClassification/index.tsx` | PASS | 三列布局，类型导入正确 |
| `Tenants/index.tsx` | PASS | sender_domain/warmup_level 字段与服务端一致 |
| `EmailMonitor/index.tsx` | WARN | useState 声明顺序（见 §3.7，minor，不阻塞） |

### 2.5 配置/集成

| 文件 | 结论 | 说明 |
|---|---|---|
| `core/config.py` | PASS | ENGAGELAB_SENDER 已正确移除，Basic Auth 字段完整 |
| `integrations/engagelab.py` | PASS | Basic Auth 优先，Bearer 向后兼容，_validate_config 配对校验正确，无硬编码凭证 |

---

## 三、具体问题清单

### 3.1 [minor] 0016：keyword_master 重复唯一索引

`keyword_master.keyword_normalized` 同时有 `UNIQUE` 约束（自动创建索引）和 `CREATE UNIQUE INDEX uq_keyword_master_normalized`。浪费存储但不影响正确性。迁移已产出，downgrade 时 DROP TABLE 一并清理。

### 3.2 [minor] 0027：trigger_set_updated_at 前置依赖

迁移引用 `trigger_set_updated_at()` 函数，已确认在 0001 canonical schema 中定义，无实际风险。建议注释标注前置依赖。

### 3.3 [minor] tenant_scoring_weights_service.py：f-string SQL 拼接

WHERE 子句使用字符串拼接，但拼接内容为代码内部硬编码字符串（不含用户输入），无 SQL 注入风险。代码风格不一致，建议后续迭代改为两个独立查询。

### 3.4 [major → 已修复] fan_out.py：EXISTS 子查询未关联关键词与公司

**原问题**：步骤 2 的 SQL EXISTS 子查询只检查"是否存在 keyword_master_id 的记录"，未关联 `ck.tenant_id = tc.tenant_id`，导致所有其他租户的所有公司被错误 fan-out。

**修复**：将 EXISTS 改为 JOIN：
```sql
-- 修复后
FROM tenant_companies tc
JOIN collection_keywords ck ON ck.tenant_id = tc.tenant_id
WHERE ck.keyword_master_id = :kmid
  AND tc.tenant_id != :tenant_id
```

**修复文件**：`app/workers/fan_out.py`，已 commit。

### 3.5 [major → 已修复] tenant_messaging_service.py：mark_email_failed 丢弃错误字段

**原问题**：`mark_email_failed` 的 SQL 仅更新 `status = 'failed'`，payload 中 `error_code`/`error_message` 被丢弃，影响 D-041 投递监控故障排查能力。

**修复**：UPDATE SQL 补入 `error_code = :error_code, error_message = :error_message`。

**修复文件**：`app/services/tenant_messaging_service.py`，已 commit。

### 3.6 [minor] webhook_service.py：occurred_at_open fallback key 名错误

`payload.get("occurred_at_dt")` 总返回 None（key 不存在），但第一个分支 `status_updates.get("opened_at")` 会命中正确值，fallback 不会被触发，功能不受影响。建议清理无效 fallback。

### 3.7 [minor] EmailMonitor/index.tsx：hooks 声明顺序

`setAiError` 在 `aiMutation.onError` 回调中被引用，但 `useState` 声明在后。运行时因闭包机制正常，但违反 hooks 可读性规范，可能触发 eslint 警告。

---

## 四、安全性专项结论

**PASS。**
- RLS 隔离：`tenant_scoring_weights` 使用已验证的 `current_tenant_id()` 函数，与其他表一致。
- EngageLab 鉴权：凭证通过环境变量注入，无硬编码，配对校验正确。
- D-035 白名单：渠道校验在早期 return，防护有效。
- SQL 注入：所有用户输入均参数化。

## 五、并发安全性专项结论

**PASS。** `claim_due_emails` 的 FOR UPDATE SKIP LOCKED + email_send_locks 并发防护机制经审查正确。

## 六、数据一致性专项结论

**PASS（修复后）。** 0017 数据回填 UPSERT 幂等。fan_out 步骤 2 SQL 错误已修复，幂等性由 ON CONFLICT DO NOTHING 保证。

---

## 七、部署阻塞结论

| 问题 | 修复状态 | 阻塞 |
|------|----------|------|
| M-1 fan_out EXISTS 错误 | ✅ 已修复 commit | 不再阻塞 |
| M-2 mark_email_failed 丢字段 | ✅ 已修复 commit | 不再阻塞 |
| minor 问题（3.1/3.3/3.6/3.7） | 待后续迭代 | 不阻塞 |

**Gate 6 结论**：major 问题已修复，**审查通过，可进行部署。**
