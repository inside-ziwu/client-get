# Migration Mapping · v3-data-foundation

> 范围：只定义旧数据到 V3 data foundation 的迁移映射与兼容边界。本文不实现 cleanup_service、worker 调度、raw→clean 复杂 ETL、AI 回填、competitor 重构。

## 1. Keyword Mapping

### 1.1 Source Tables

| 旧表 | 角色 | V3 处理 |
|---|---|---|
| `collection_keywords` | 租户历史关键词输入与兼容字段 | 迁移输入 / 兼容桥，不再是 V3 真源 |
| `collection_task_keywords` | 历史 task 与租户关键词归属 | 历史归属输入，不再是 V3 目标真源 |

### 1.2 Target Tables

| 目标表 | 角色 |
|---|---|
| `keyword_master` | 平台级关键词真源 |
| `tenant_keyword` | 租户级关键词订阅真源 |

### 1.3 Field Mapping

| 来源 | 目标 | 规则 |
|---|---|---|
| `collection_keywords.keyword` | `keyword_master.keyword` | 同一个 `keyword_normalized` 下取最早创建的原始展示词 |
| `collection_keywords.keyword` | `keyword_master.keyword_normalized` | 使用 V3 归一规则 |
| `collection_keywords.tenant_id` | `tenant_keyword.tenant_id` | 原样迁移 |
| `keyword_master.id` | `tenant_keyword.keyword_master_id` | 通过归一后平台关键词关联 |
| `collection_keywords.keyword` | `tenant_keyword.keyword_raw` | 保存租户原始输入 |
| `collection_keywords.created_by` | `tenant_keyword.created_by` | 可空迁移 |
| `collection_keywords.created_at` | `tenant_keyword.created_at` | 保留原始订阅时间 |
| `collection_keywords.status` | `tenant_keyword.status` | `deleted` → `deleted`；其他状态 → `active` |

### 1.4 Normalization Rule

V3 关键词归一规则：

| 输入 | 输出 | 说明 |
|---|---|---|
| `P.C.B` | `pcb` | `.` 是非语义分隔符，移除 |
| `pcb` | `pcb` | 大小写归一 |
| `PCB ` | `pcb` | 首尾空白移除 |
| `Ｐ．Ｃ．Ｂ` | `pcb` | 全角转半角 |
| `FR-4` | `fr-4` | `-` 可能承载语义，保留 |
| `FR4` | `fr4` | 不与 `FR-4` 合并 |
| `C++` | `c++` | `+` 可能承载语义，保留 |
| `C` | `c` | 不与 `C++` 合并 |

### 1.5 Upsert / Restore Semantics

新增租户关键词时：

1. `keyword_raw` 先按 V3 规则归一为 `keyword_normalized`。
2. `keyword_master` 按 `keyword_normalized` upsert。
3. `tenant_keyword` 按 `(tenant_id, keyword_master_id)` upsert。
4. 如果原订阅行是 `deleted`，恢复为 `active`，更新 `keyword_raw` / `created_by`，不刷新 `created_at`。
5. 同一租户重复添加同一平台关键词，不创建第二条 `tenant_keyword`。
6. 不同租户添加等价关键词，共用同一条 `keyword_master`，各自拥有独立 `tenant_keyword`。

## 2. Legacy Collection Task Mapping

| 旧表 / 字段 | V3 处理 |
|---|---|
| `collection_task_keywords.task_id` | 仅用于追溯历史 task 属于哪些租户关键词 |
| `collection_task_keywords.keyword_id` | 可回溯到 `collection_keywords.id`，再映射到 `keyword_master_id` |
| `collection_task_keywords.tenant_id` | 仅作为历史归属；V3 新任务不得以此为真源 |
| `collection_tasks.run_id` | V3 起指向 `collection_runs.id`，run 级关键词归属从 `collection_runs.keyword_master_id` 解析 |

V3 subscribed tenant 解析路径：

```text
collection_tasks.run_id
→ collection_runs.keyword_master_id
→ tenant_keyword(keyword_master_id, status='active')
```

禁止路径：

```text
collection_task_keywords → collection_keywords
```

该路径只允许历史兼容、审计和一次性迁移使用。

## 3. Raw / Clean Mapping Boundary

### 3.1 Raw Tables

| 旧数据 | V3 落点 | 边界 |
|---|---|---|
| `lixiaoyun_raw_companies` | `lixiaoyun_raw_companies` | 保留 raw 公司行；补 `keyword_master_id`；去除 `task_id / last_seen_at` 真源语义 |
| 励销云联系人 payload | `lixiaoyun_raw_contacts` | 本 change 只建表与去重规则；联系人抽取由后续 collection/cleanup change 实现 |
| `tendata_raw_companies.tid` | `tendata_raw_companies.source_id` | `tid` 作为来源侧唯一 key 承接，不再作为主键 |
| 腾道联系人 payload | `tendata_raw_contacts` | 本 change 只建表与去重规则；联系人抽取由后续 collection/cleanup change 实现 |

### 3.2 Clean Tables

| 目标表 | 写入边界 |
|---|---|
| `clean_companies` | 后续 cleanup/ETL 写入，本 change 不做 raw→clean 清洗 |
| `clean_contacts` | 后续 cleanup/ETL 写入，本 change 不做联系人清洗 |
| `clean_company_sources` | V3 只允许 `source_type='tendata'`；励销云 raw 不进入 clean source |
| `clean_company_keywords` | 保存平台级关键词命中事实，tenant API 再通过 `tenant_keyword` 透出租户关键词 |
| `tenant_companies` | 租户私有状态 overlay，不作为可见性唯一入口 |
| `tenant_contacts` | 租户联系人状态 overlay，不做联系人单独授权 |

## 4. Compatibility Policy

- `collection_keywords` 可以继续存在，作为旧接口和历史数据迁移输入。
- `collection_task_keywords` 可以继续存在，作为历史 task 归属追溯输入。
- 新 API、worker、tenant 可见性判断不得把旧表当 V3 真源。
- raw→clean ETL、联系人抽取、fan-out、worker 调度在后续 change 中实现。
