# 14 数据迁移方案（修复版）

## 1. 当前前提

用户已明确：新后端代码尚未开始写。因此迁移方案主要用于：

1. 将旧系统数据导入新 Schema。
2. 帮代码 Agent 理解旧表与新表的对应关系。
3. 避免照搬旧 9 状态流水线。

如果没有旧库需要保留，可跳过历史数据迁移，只执行新 Schema 初始化与 seed。

## 2. 旧系统到新系统的关键变化

| 旧系统 | 新系统 |
|---|---|
| 单用户、无 tenant_id | 多租户 + RLS。 |
| `email_plans` 承载采集/清洗/生成/发送 | `sending_plans` 只承载发送。 |
| `company_data` | `shared_companies` + `company_sources` + `tenant_companies`。 |
| `contact_data` | `shared_contacts` + `tenant_contacts`。 |
| A/B/X 评分 | S/A/B/C/D 评分。 |
| `email_drafts` | `emails` + `sequence_steps` + `sequence_enrollments`。 |
| `system_config` | platform config / encrypted credentials / env。 |

## 3. 默认迁移策略

1. 建立默认租户 `default`。
2. 建立默认平台管理员。
3. 旧数据全部归入 default tenant。
4. 旧计划迁移为只读归档；除非明确要恢复发送，否则不自动继续发送。
5. 所有可恢复发送的旧计划迁移后先进入 `paused`，人工确认后 resume。

## 4. 修复后的映射要点

### 4.1 company_data

- 先构造 canonical company map。
- 优先 domain 去重；无 domain 用 name + country。
- 写 `shared_companies`。
- 写 `company_sources`。
- 写 `tenant_companies`。

### 4.2 contact_data

- 写 `shared_contacts`。
- 写 `tenant_contacts`。
- 根据联系人规则或旧 classify_contact 结果设置 grade。
- 每家公司选一个默认联系人：优先 A 级且有效邮箱。

### 4.3 company_analysis

旧 A/B/X 映射：

| old | score | new |
|---|---:|---|
| A | >= 80 | S |
| A | < 80 | A |
| B | >= 50 | B |
| B | < 50 | C |
| X | any | D |

同时写 `tenant_companies.total_score/grade/business_status='scored'`。

### 4.4 keyword_list

- `country` → `countries`。
- normalized keyword → `keyword_normalized`。
- 默认 source_types 为 `["waimao_tong"]`，除非旧数据能识别更多来源。

### 4.5 email_plans

旧计划链按 `linked_plan_id` 收敛到 root plan：

- root plan → `sending_plans`。
- 每个 round → `sequence_steps`。
- 每个 contact → `sequence_enrollments`。
- 旧草稿/发送记录 → `emails`。

迁移后默认：

- done → completed。
- sending/pending_approval → paused。
- 其他中间态 → draft 或 archived，具体由迁移报告标记。

### 4.6 system_config

- OpenRouter key → 环境变量或平台 secret，不建议迁入 DB 明文。
- 外贸通 cookie/token → `data_source_credentials.credentials_encrypted`。
- EngageLab credentials → 环境变量或 encrypted config。
- mail daily limit → `warmup_rules` 或 tenant/domain config。

## 5. 执行顺序

详见 `../03_database/MIGRATION_ORDER_AND_NOTES.md`。

推荐批次：

1. 新 Schema。
2. seed platform admin + default tenant。
3. ID mapping 表。
4. shared companies/sources。
5. tenant companies/scores。
6. contacts/default contacts。
7. templates/scoring/contact rules。
8. sending plans/steps/enrollments/emails。
9. billing/config/credentials。
10. 验证与报告。

## 6. 验证

必须输出迁移报告：

- 旧表行数 vs 新表行数。
- 去重合并数量。
- 无法匹配的 contact/company。
- 无法恢复的 plan。
- 无 from_email 的 email 记录。
- 无默认联系人的 tenant_company。
