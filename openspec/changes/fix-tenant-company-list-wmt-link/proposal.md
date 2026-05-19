## Why

Tenant 公司列表已经按 `20260519_0045` 切换为读取 `waimaotong_clean_companies`，但当前线上 `tenant_companies.clean_company_id` 大量仍指向旧 `clean_companies.id`，导致列表 JOIN 结果为 0。

这不是 0045 方向错误，而是关键词订阅到 wmt clean 的血缘链路没有补齐：`waimaotong_clean_companies.keyword_master_ids` 为空，现有 `fan_out.py` 仍从旧 `clean_company_keywords` 写入旧 clean id，且采集程序写出的部分 `waimaotong_raw_companies` 缺少可直接归因字段，需要一次性数据补全。

## What Changes

- 新增 wmt tenant 可见关系生成逻辑：只把匹配当前租户 active 关键词的 `waimaotong_clean_companies` 写入 `tenant_companies`。
- 血缘链路以 `waimaotong_clean_companies.sys_company_id -> waimaotong_raw_companies.sys_company_id -> source_competitor -> lixiaoyun_api_clean_companies.entname_eng -> keyword_master_ids` 为主路径。
- 当 lixiaoyun clean 缺失但 lixiaoyun raw 存在时，允许 fallback 到 `lixiaoyun_api_companies.entname_eng -> keyword_master_id`。
- 对当前采集程序缺字段造成的 25 条 wmt clean 做一次性数据补全：
  - `APCB ELECTRONICS (KUNSHAN) CO., LTD.` 可从 lixiaoyun raw 补回关键词血缘。
  - `SHENZHEN KINWONG ELECTRONIC CO LTD` 需要补齐来源同行标准身份或手工确认映射后再入 tenant。
- 清理或隐藏线上悬空的旧 `tenant_companies` 记录，重建指向 wmt id 的租户可见关系。
- 改造或停用旧 `fan_out.py` 写入路径，禁止继续把旧 `clean_companies.id` 写入 `tenant_companies.clean_company_id`。
- 增加诊断/校验：任何没有关键词血缘的 wmt clean 不能静默进入 tenant 列表，必须输出 unresolved lineage 清单。

## Non-Goals

- 不回退 `20260519_0045`，tenant 公司列表继续以 `waimaotong_clean_companies` 为唯一公司数据源。
- 不恢复 tenant 端对 `clean_companies` / `clean_company_keywords` 的列表依赖。
- 不依赖模糊匹配自动归因未确认的 `source_competitor`，避免把错误同行扩散到租户列表。
- 不修改外部采集程序本身；本 change 只在本仓库内补齐数据血缘、修复 tenant 可见关系，并增加防复发校验。
- 不自动执行线上补数、生产迁移或镜像发布；这些生产副作用必须由用户显式触发。

## Capabilities

### New Capabilities

- `tenant-wmt-lineage-fanout`: 从 wmt clean 的来源同行血缘生成 tenant 可见公司关系，并诊断无血缘数据。
- `tenant-wmt-lineage-repair`: 一次性补全当前线上 wmt 数据血缘，清理旧 clean id 悬空关联，重建 wmt id 关联。

### Modified Capabilities

- `tenant-companies-list`: tenant 公司列表只展示匹配当前租户 active 关键词且有可解释 wmt 血缘的公司。

## Impact

| 层 | 影响范围 | 说明 |
|----|---------|------|
| 后端 Worker / Service | `backend/app/workers/fan_out.py` 或新增 wmt fan-out service | 旧 clean_company fan-out 必须改造或停用，新增 wmt lineage fan-out |
| 后端 Tenant 查询 | `backend/app/services/tenant_query_service.py` | 列表仍读 wmt，但依赖修复后的 `tenant_companies.clean_company_id = wmt.id` |
| 后端 Ops | `backend/app/services/tenant_ops_service.py` | 筛选、导出等依赖修复后的 wmt tenant 关系 |
| 数据库迁移/脚本 | `backend/alembic/versions/`、可选 `backend/scripts/` | 补索引、补数据、清理悬空关系、重建 tenant_companies |
| 测试 | `backend/tests/` | 增加 wmt lineage fan-out、fallback、unresolved 诊断、tenant 列表恢复测试 |
| 线上数据 | PostgreSQL `clientget` | 需要显式授权后做一次性只针对本问题的数据补全与修复 |

## Evidence

- 线上 `tenant_companies` 两个租户各有约 15458/15459 条 visible，但与 `waimaotong_clean_companies` JOIN 为 0。
- 线上 `tenant_companies.clean_company_id` 与旧 `clean_companies.id` 可 JOIN 出约 24465 条，说明旧语义数据仍在。
- `waimaotong_clean_companies` 506 条均可通过 `sys_company_id` 回连 `waimaotong_raw_companies`。
- 481 条可通过 `raw.source_competitor = lixiaoyun_api_clean_companies.entname_eng` 获取关键词血缘。
- 16 条 `APCB ELECTRONICS (KUNSHAN) CO., LTD.` 可从 `lixiaoyun_api_companies.entname_eng` fallback 获取 `电路板` 关键词血缘。
- 9 条 `SHENZHEN KINWONG ELECTRONIC CO LTD` 仍需补齐来源同行标准身份，不能用模糊匹配自动归因。
