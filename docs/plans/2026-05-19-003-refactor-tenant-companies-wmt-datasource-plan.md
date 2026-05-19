---
title: "refactor: Tenant 端公司/联系人数据源切换到外贸通表"
status: active
type: refactor
origin: openspec/changes/2026-05-19-tenant-companies-wmt-datasource/
created: 2026-05-19
depth: deep
tags: [tenant, waimaotong, migration, data-source, refactor]
---

# refactor: Tenant 端公司/联系人数据源切换到外贸通表

## 概述

将 tenant 端所有公司/联系人查询和写入从 `clean_companies` / `clean_contacts` 切换到 `waimaotong_clean_companies` / `waimaotong_clean_contacts`，使 tenant 和 admin 两端展示完全相同的客户数据。桥接表 `tenant_companies` / `tenant_contacts` 保留，FK 指向改变。

## 问题框架

tenant 端公司列表当前从 `clean_companies` + `tenant_companies` 取数据，admin 端客户数据页面从 `waimaotong_clean_companies` / `waimaotong_clean_contacts` 取数据。两套表完全独立、无关联，导致 tenant 和 admin 看到的客户数据不一致。(see origin: proposal.md)

## 需求追溯

- R1. tenant 端所有公司查询（列表、详情、筛选项、导出、潜客列表）切到 wmt 表
- R2. tenant 端联系人读写切到 `waimaotong_clean_contacts`（通过 `sys_company_id` 关联）
- R3. `tenant_companies` 桥接表 FK 从 `clean_companies.id` 改为 `waimaotong_clean_companies.id`
- R4. 创建公司去重策略改为 domain 优先 + name+country 回退 + `pg_advisory_xact_lock` (D9)
- R5. `clean_company_sources` 来源追溯改用 `data_source_tags` text[] 列
- R6. `_matched_tenant_keywords` 功能暂时移除 (D8)
- R7. migration 中基于 name+country 重建 `tenant_companies` 关联
- R8. API 响应 key 不变，后端映射 (D12)
- R9. `tenant_contacts` 全表清空 (D11/D14)

## 范围边界

- 不删除 `clean_companies` / `clean_contacts` / `clean_company_sources` 表结构
- 不修改 admin 端的 wmt API 和页面
- 不改造 fan_out keyword pipeline（标注 TODO）
- 不对 wmt 表加破坏性 UNIQUE 约束（只加索引）

### 延迟到独立任务

- fan_out keyword pipeline 改造：后续统一改造时切换到 wmt 表
- `_matched_tenant_keywords` 功能恢复：依赖 fan_out pipeline 改造

## 上下文与研究

### 相关代码与模式

- `backend/app/services/admin_collection_service.py` — `list_wmt_clean_companies()` (2432-2534) 和 `list_wmt_clean_company_contacts()` (2567-2594) 提供 wmt 表查询的参考模式
- `backend/app/services/company_filter_sql.py` — 共享过滤器帮助函数，硬编码 `alias="cc"`，含 `pcb_suppliers` 逻辑（wmt 无此列需移除）
- `backend/app/services/tenant_query_service.py` — 主读查询服务（855 行），6 个函数需改造
- `backend/app/services/tenant_ops_service.py` — 主写操作服务（1078 行），7 个函数需改造
- `backend/app/services/tenant_messaging_service.py` — 12 处 clean_companies/clean_contacts 引用
- `frontend/packages/shared-api/src/tenant/companies.ts` — Company 类型已有 `grade`、`total_score`、`domain`、`employee_scale` 字段

### 机构经验

- `docs/solutions/best-practices/fk-column-migration-null-old-values-before-constraint-2026-05-07.md` — FK 列迁移 8 步原子模式：先删约束 → NULL 化 → rename → 建新约束。本次 migration 参考此顺序但无需 rename
- `docs/solutions/database-issues/tenant-companies-bigint-uuid-type-mismatch-2026-05-07.md` — DROP CASCADE 引起的跨迁移类型漂移风险，本次 migration 不使用 DROP CASCADE 故无此风险
- `docs/solutions/best-practices/admin-waimaotong-fullstack-display-rewrite-2026-05-19.md` — wmt 表列补齐使用 `ADD COLUMN IF NOT EXISTS` 幂等迁移模式；共享 WHERE 分支必须拆分不能跨 provider 引用列

## 关键技术决策

| 决策 | 选项 | 理由 | 来源 |
|------|------|------|------|
| D2: 创建公司去重策略 | 应用层 SELECT-then-INSERT + advisory lock | wmt 表外部导入，不宜加 UNIQUE 约束 | (see origin: proposal.md D2+D9) |
| D6: sub_industries 匹配 | `wc.industry = ANY() OR wc.sub_industry = ANY()` 精确双列匹配 | 保持旧代码双列语义，值来自下拉（有限集） | (see origin: proposal.md D6+D13) |
| D8: keyword 功能 | 暂时移除 `_matched_tenant_keywords` | 依赖 clean_company_keywords 表，需 fan_out pipeline 统一改造 | (see origin: proposal.md D8) |
| D10: 未匹配 tenant_companies | 直接 DELETE | 用户偏好简洁，未匹配记录可接受损失 | (see origin: proposal.md D10) |
| D11: tenant_contacts | 全表清空 | 无不可恢复业务状态（退订状态丢失风险已知悉 D14） | (see origin: proposal.md D11+D14) |
| D12: API 响应 key | 后端映射保持不变 | `company_name` → 返回 `name`，前端零改动 | (see origin: proposal.md D12) |

## 已解决的问题

- **advisory lock hash key 对齐**：同 domain 不同 name 的并发请求不互锁，理论上可产生重复。已评估为低概率风险，维持现状 (D15)
- **退订/退信状态丢失**：tenant_contacts 含 `unsubscribed`/`bounced` 合规状态，全表清空有合规风险。已知悉并接受 (D14)
- **employee_count 解析**：`company_filter_sql.py` 中 `append_employee_count_range` 对 text 格式的 employee_num 做复杂解析（如 "51-200" → 提取数值）。wmt 的 `employee_size` 格式需确认兼容性

### 延迟到实施时

- wmt 表 `employee_size` 实际值域格式确认（是否与 `employee_num` 格式一致）
- `waimaotong_clean_contacts` 唯一约束情况确认（影响 `_ensure_contact_from_payload` 的 ON CONFLICT 写法）
- `data_source_tags` 实际值域确认（影响前端来源筛选器选项）

## 高层技术设计

> *以下说明仅为方向性指引，不是实施规范。实施时应以此为上下文，而非照搬。*

```
依赖关系图：

  IU-1 Migration
       │
       ▼
  IU-2 Filter Helpers (company_filter_sql.py)
       │
       ├────────────────┐
       ▼                ▼
  IU-3 Query Svc    IU-4 Ops Svc     ← 可并行
       │                │
       └────────────────┘
              │
              ▼
  IU-5 Peripheral Services
              │
              ▼
  IU-6 Frontend
              │
              ▼
  IU-7 Tests
              │
              ▼
  IU-8 E2E Verification
```

核心 JOIN 模式变更（所有 tenant 端查询共享）：

```sql
-- 旧
FROM clean_companies cc
JOIN tenant_companies tc ON tc.clean_company_id = cc.id AND tc.tenant_id = :tenant_id

-- 新
FROM waimaotong_clean_companies wc
JOIN tenant_companies tc ON tc.clean_company_id = wc.id AND tc.tenant_id = :tenant_id
```

联系人查询模式变更（从直接 FK 到间接 sys_company_id）：

```sql
-- 旧
FROM clean_contacts cc WHERE cc.clean_company_id = :id

-- 新
FROM waimaotong_clean_contacts wcc
WHERE wcc.sys_company_id = (
    SELECT sys_company_id FROM waimaotong_clean_companies WHERE id = :id
)
```

## 实施单元

### - [ ] IU-1: Migration — FK 变更 + 索引 + 关联重建

**目标：** 创建 alembic migration，将 tenant_companies/tenant_contacts 的 FK 从 clean 表切到 wmt 表，补建必要索引。

**需求：** R3, R7, R9

**依赖：** 无

**文件：**
- 创建: `backend/alembic/versions/20260519_0045_tenant_wmt_datasource_migration.py`

**方法：**

按以下顺序执行（参考机构经验：FK 迁移 8 步原子模式）：

1. 补建 wmt 表索引（幂等，CREATE INDEX IF NOT EXISTS）：
   - `waimaotong_clean_contacts.sys_company_id`
   - `waimaotong_clean_companies.domain`（partial: WHERE domain IS NOT NULL AND domain != ''）
   - `waimaotong_clean_companies(company_name, country_iso3)`

2. 删除 `tenant_companies.clean_company_id` 旧 FK 约束

3. 重建 `tenant_companies` 关联：UPDATE JOIN 基于 `clean_companies.name = wmt.company_name AND clean_companies.country_iso3 = wmt.country_iso3`

4. 直接 DELETE 未匹配的 tenant_companies（D10）

5. 清空 tenant_contacts 全表（D11）

6. 重建 `company_blacklist.shared_company_id` 关联（同样的 name+country 匹配）

7. 新建 `tenant_companies.clean_company_id` 索引（不加 FK 约束，避免阻碍 wmt 导入流程）

使用 `op.get_bind().exec_driver_sql()` 写原生 SQL（与项目现有 migration 模式一致）。

**模式参考：**
- `backend/alembic/versions/20260519_0044_sync_waimaotong_online_columns.py` — 最新 migration 格式
- `docs/solutions/best-practices/fk-column-migration-null-old-values-before-constraint-2026-05-07.md` — FK 迁移步骤顺序

**测试场景：**
- Happy path: migration up 执行成功，`tenant_companies.clean_company_id` 全部指向 wmt 表 id
- Happy path: migration down 可执行（结构性回滚，数据不可逆）
- Edge case: wmt 表中无匹配记录的 tenant_companies 行被正确删除
- Edge case: tenant_contacts 表被完全清空
- Edge case: company_blacklist 关联正确重建

**验收：**
- `SELECT count(*) FROM tenant_companies WHERE clean_company_id NOT IN (SELECT id FROM waimaotong_clean_companies)` 返回 0
- `SELECT count(*) FROM tenant_contacts` 返回 0
- 三个新索引存在

---

### - [ ] IU-2: company_filter_sql.py — 共享过滤器适配

**目标：** 适配共享过滤器帮助函数，使其支持 wmt 表的列名和别名。

**需求：** R1

**依赖：** IU-1

**文件：**
- 修改: `backend/app/services/company_filter_sql.py`

**方法：**
- `pcb_supplier_presence_clause()` 和相关的 `pcb_suppliers` 逻辑保留不动（admin 端可能仍在使用），但 tenant 端调用处移除对此函数的调用
- `append_employee_count_range()` 已支持 `alias` 参数，tenant 端调用时传 `alias="wc"` 即可
- `employee_count_lower_expr()` / `employee_count_upper_expr()` 引用 `{alias}.employee_num`，wmt 表列名为 `employee_size`。需确认 wmt 的 `employee_size` 值域格式：若格式一致（如 "51-200"），只需在 tenant 端调用时用 SQL 别名 `wc.employee_size AS employee_num` 对齐；若格式不同，需要新的解析逻辑
- 不改动函数签名，保持后向兼容

**模式参考：**
- `backend/app/services/company_filter_sql.py` — 现有实现

**测试场景：**
- Test expectation: none — 此单元为辅助适配，行为验证在 IU-3/IU-7 中覆盖

**验收：**
- `company_filter_sql.py` 对 admin 端调用无影响
- tenant 端传入 `alias="wc"` 后过滤逻辑正确

---

### - [ ] IU-3: tenant_query_service.py — 读查询全面切换

**目标：** 将所有 tenant 端读查询从 `clean_companies` 切到 `waimaotong_clean_companies`。

**需求：** R1, R2, R5, R6, R8

**依赖：** IU-1, IU-2

**文件：**
- 修改: `backend/app/services/tenant_query_service.py`

**方法：**

6 个函数逐一改造：

1. **`companies_page()`** (L139-411)
   - JOIN: `clean_companies cc` → `waimaotong_clean_companies wc`
   - SELECT: 列映射（见 design.md §2），用 SQL 别名保持返回 key 不变（R8）：`wc.company_name AS name`, `wc.industry AS industry_desc`, `wc.employee_size AS employee_num` 等
   - WHERE: 逐一替换过滤器（见 design.md §3）。移除 `reg_capital`、`pcb_suppliers` 过滤器
   - `sub_industries`: `wc.industry = ANY(:sub_industries) OR wc.sub_industry = ANY(:sub_industries)`
   - `sources`: 从 EXISTS 子查询改为 `wc.data_source_tags && :sources`
   - `founded_year`: 从 `EXTRACT(YEAR FROM cc.incorporation_date)` 改为 `wc.founded_year` 直接比较
   - 游标: `cc.id < :cursor` → `wc.id < :cursor`
   - `append_employee_count_range` 调用传 `alias="wc"`

2. **`v3_company_detail()`** (L413-497)
   - JOIN 改为 wmt，SELECT 列映射
   - `_company_sources()` 调用替换为直接从主查询 SELECT `wc.data_source_tags`，返回格式从对象数组简化为字符串数组
   - `_matched_tenant_keywords()` 调用移除，返回 `matched_keywords: []`

3. **`v3_company_contacts()`** (L499-544)
   - 改为查 `waimaotong_clean_contacts`，通过 `sys_company_id` 子查询关联（参考 admin 端 `list_wmt_clean_company_contacts()` 模式）

4. **`prospects()`** (L604-731)
   - JOIN 改为 wmt，过滤器同 `companies_page()`
   - `clean_company_sources` EXISTS 子查询改为 `data_source_tags &&`
   - 移除 `pcb_supplier_presence_clause` 调用

5. **`_company_sources()`** (L546-568)
   - 整个方法可删除或标注废弃（功能已内联到 `v3_company_detail`）

6. **`_matched_tenant_keywords()`** (L570-599)
   - 整个方法删除（D8）

**模式参考：**
- `backend/app/services/admin_collection_service.py:2432-2534` — wmt 表查询模式
- `backend/app/services/admin_collection_service.py:2567-2594` — sys_company_id 联系人查询模式

**测试场景：**
- Happy path: 公司列表 API 返回 wmt 数据，包含 grade/domain/english_name 新字段
- Happy path: 公司详情 API 返回 wmt 数据，sources 为字符串数组，matched_keywords 为空列表
- Happy path: 联系人 API 返回 wmt_clean_contacts 数据
- Happy path: 潜客列表返回 wmt 数据
- Edge case: 游标分页正常工作（cursor 值为 wmt id）
- Edge case: 页码分页 total 正确
- Edge case: 各过滤器工作正常——country、sub_industries（双列匹配）、employee_scale、sources（data_source_tags）、founded_year（int 比较）、product_tags
- Edge case: 移除的过滤器（reg_capital、pcb_suppliers）不影响请求
- Edge case: keyword 搜索匹配 `company_name` 和 `domain`
- Integration: API 响应 key 保持不变（name 而非 company_name）

**验收：**
- 所有 `/api/v1/companies` 读接口返回 wmt 数据
- 筛选器全部工作
- 分页正常
- API 响应 key 未变

---

### - [ ] IU-4: tenant_ops_service.py — 写操作全面切换

**目标：** 将所有 tenant 端写操作从 `clean_companies` 切到 `waimaotong_clean_companies`。

**需求：** R1, R2, R4, R8

**依赖：** IU-1, IU-2

**文件：**
- 修改: `backend/app/services/tenant_ops_service.py`

**方法：**

7 个函数逐一改造：

1. **`create_company()`** (L91-178)
   - 完全重写去重逻辑（D2/D9）：
     - `pg_advisory_xact_lock(hashtext(domain || company_name || country_iso3))` 防并发
     - SELECT domain 优先查重 → 回退 company_name + country_iso3 查重
     - 不存在则 INSERT INTO `waimaotong_clean_companies`（无 ON CONFLICT）
   - `tenant_companies` INSERT 保持不变（`clean_company_id` 指向 wmt id）
   - 移除 `normalize_company_name()` 调用

2. **`_ensure_contact_from_payload()`** (L924-985)
   - 写入目标改为 `waimaotong_clean_contacts`
   - 先通过 wmt company id 获取 `sys_company_id`
   - INSERT 使用 `sys_company_id` 关联
   - ON CONFLICT 写法需确认 wmt_clean_contacts 唯一约束（延迟到实施时）

3. **`get_company()`** (L194-252)
   - JOIN 改为 wmt，SELECT 列映射，API key 不变（R8）

4. **`company_contacts()`** (L295-328)
   - JOIN 改为 `waimaotong_clean_contacts`

5. **`blacklist_company()`** (L254-293)
   - `shared_company_id` 改为取 wmt company id

6. **`companies_filters()`** (L40-61)
   - JOIN 改为 wmt

7. **`export_companies()`** (L63-89)
   - JOIN 改为 wmt，导出列适配

**模式参考：**
- `backend/app/services/tenant_ops_service.py:91-178` — 现有 create_company 模式（替换对象）

**测试场景：**
- Happy path: 创建公司写入 wmt 表，tenant_companies 正确关联
- Happy path: 创建公司时 domain 去重命中已有记录
- Happy path: 创建公司时 name+country 回退去重命中
- Happy path: 黑名单操作正常
- Happy path: 导出返回正确数据
- Edge case: 并发创建同一公司不产生重复（advisory lock）
- Edge case: domain 为空时回退到 name+country 去重
- Edge case: 筛选项返回 wmt 数据
- Error path: wmt_clean_contacts 唯一约束冲突时的 upsert 行为

**验收：**
- 创建公司写入 wmt 表
- 导入、黑名单均正常
- 筛选项和导出返回正确数据

---

### - [ ] IU-5: 周边服务适配

**目标：** 将所有周边服务中的 clean_companies/clean_contacts 引用改为 wmt 表。

**需求：** R1, R2

**依赖：** IU-3, IU-4

**文件：**
- 修改: `backend/app/services/tenant_messaging_service.py`
- 修改: `backend/app/services/webhook_service.py`
- 修改: `backend/app/services/tenant_hard_delete_service.py`
- 修改: `backend/app/services/keyword_service.py`
- 修改: `backend/app/workers/fan_out.py`

**方法：**
- `tenant_messaging_service.py`：12 处引用机械替换。JOIN 别名 `cc` → `wc`，表名改为 wmt，字段 `cc.name` → `wc.company_name`（SQL 层保持 company_name，Python 返回值映射不变因为都用 row["name"] 读取 SQL 别名）
- `webhook_service.py`：1 处引用适配
- `tenant_hard_delete_service.py`：1 处引用适配
- `keyword_service.py`：2 处引用适配
- `fan_out.py`：标注 `TODO: 后续 keyword pipeline 改造时切换到 wmt 表`（D8 暂不改造）

**模式参考：**
- design.md §7 — messaging_service 适配模式

**测试场景：**
- Happy path: 邮件发送查询正常获取 wmt 公司名和联系人信息
- Integration: tenant_hard_delete 正确级联清理 wmt 关联
- Edge case: fan_out.py 现有 keyword pipeline 不受影响

**验收：**
- `grep -rn "clean_companies\|clean_contacts" backend/app/services/ backend/app/workers/` 在 tenant 侧代码中无活跃引用（fan_out.py TODO 除外）

---

### - [ ] IU-6: 前端适配

**目标：** 确认前端类型和展示与后端返回一致。

**需求：** R1, R8

**依赖：** IU-3, IU-4

**文件：**
- 修改: `frontend/packages/shared-api/src/tenant/companies.ts`
- 修改: `frontend/apps/tenant/src/app/(dashboard)/companies/page.tsx`

**方法：**
- 由于 D12 硬约束（API key 不变），前端改动量极小
- Company 类型：确认 `grade`、`total_score`、`domain`、`employee_scale` 等已有字段与后端返回对齐
- 新增字段按需加入类型定义：`english_name`、`sub_industry`、`description` 等
- `matched_keywords` 空列表兼容处理（已有组件在列表为空时不渲染，确认即可）
- 筛选器参数确认：`employee_scale[]` 值域、`sources[]` 值域是否因 wmt 数据变化

**模式参考：**
- `frontend/packages/shared-api/src/tenant/companies.ts` — 现有类型定义

**测试场景：**
- Happy path: 公司列表页正常展示 wmt 数据
- Happy path: 筛选器各项正常工作
- Happy path: 详情页正常展示（含空 matched_keywords）
- Edge case: 新字段（grade、domain）在列表中正确展示

**验收：**
- TypeScript 编译通过
- 列表/详情/筛选器/导出在浏览器中正常工作

---

### - [ ] IU-7: 测试适配

**目标：** 适配现有 5 个 tenant 端测试到新表结构，补充去重和来源测试。

**需求：** R1, R2, R4, R5

**依赖：** IU-3, IU-4, IU-5

**文件：**
- 修改: `backend/tests/test_v3_data_foundation_api_contract.py`

**方法：**

1. **`_seed_visible_company()` fixture 重写**：
   - INSERT 从 `clean_companies` 改为 `waimaotong_clean_companies`（列名映射：`name` → `company_name` 等）
   - 添加 `data_source_tags` 列值（如 `ARRAY['tendata']`）
   - 移除 `clean_company_sources` INSERT
   - 移除 `clean_company_keywords` INSERT（D8）
   - INSERT `waimaotong_clean_contacts` 替代 `clean_contacts`，通过 `sys_company_id` 关联
   - `tenant_contacts` INSERT 的 `clean_contact_id` 指向 wmt contact id

2. **5 个测试的断言适配**：
   - `sources` 断言从 `sources[0]["source_type"] == "tendata"` 改为检查 `sources` 包含 `"tendata"`
   - `matched_keywords` 断言改为 `matched_keywords == []`
   - filter 参数名更新：`industry_tags` → `sub_industries`，`employee_num` → `employee_scale`，`incorporation_date_from` → `founded_year_from`
   - 移除 `reg_capital_min` filter 参数
   - `test_tenant_company_detail_rejects_invisible_clean_company` fixture 适配

3. **补充测试**：
   - 去重逻辑测试（domain 优先 + name+country 回退 + advisory lock）
   - `data_source_tags` 来源展示测试

**模式参考：**
- `backend/tests/test_v3_data_foundation_api_contract.py` — 现有测试结构

**测试场景：**
- Happy path: 所有 5 个现有测试通过（适配后）
- Happy path: 创建公司 domain 去重正确
- Happy path: 创建公司 name+country 回退去重正确
- Happy path: data_source_tags 在详情页正确返回
- Edge case: 创建公司 domain 为空时走 name+country 路径

**验收：**
- `pytest backend/tests/test_v3_data_foundation_api_contract.py` 全部通过

---

### - [ ] IU-8: 端到端验证

**目标：** 本地全链路验证所有功能路径正常。

**需求：** R1-R9

**依赖：** IU-1 ~ IU-7

**文件：**
- 无代码改动

**方法：**
- 本地启动后端 + 前端（使用 wmt 数据）
- 逐一验证：
  1. 公司列表页
  2. 筛选器（国家、行业、规模、来源、分数范围、成立年份）
  3. 公司详情页（字段展示、联系人列表、来源标签）
  4. 创建公司（去重逻辑、写入 wmt 表）
  5. 黑名单操作
  6. 导出
  7. 潜客列表
- `grep -rn "clean_companies\|clean_contacts" backend/app/services/ backend/app/workers/` 确认无残留引用

**测试场景：**
- Test expectation: none — 此单元为手动端到端验证，不产生自动化测试

**验收：**
- 所有功能路径正常
- 无 `clean_companies` 活跃依赖（fan_out TODO 除外）

## 系统影响

- **交互图：** tenant_query_service → wmt 表 → tenant_companies 桥接 → 前端。tenant_ops_service → wmt 表写入 → tenant_companies 关联。tenant_messaging_service → wmt 表读取联系人信息用于邮件发送
- **错误传播：** advisory lock 失败不应阻塞请求（lock 在事务结束时自动释放）。sys_company_id 为 NULL 时联系人查询返回空列表
- **状态生命周期风险：** migration 清空 tenant_contacts 导致退订/退信状态丢失（D14 已知悉）。migration DELETE tenant_companies 导致租户私有状态丢失
- **API 表面一致性：** API 响应 key 不变（D12），前端无感知
- **集成覆盖：** 邮件发送流程需验证（messaging_service 12 处引用）；webhook/hard_delete 需验证
- **不变的接口：** admin 端 wmt API 不受影响；`dashboard_overview()` 不受影响（仅查 tenant_companies）

## 风险与依赖

| 风险 | 缓解措施 |
|------|---------|
| 字段映射遗漏 | 逐列对照 design.md §2 映射表，SQL 用别名保持 API key 不变 |
| tenant_companies 关联重建匹配率不确定 | name+country 匹配是最佳可用方案，未匹配直接 DELETE (D10) |
| wmt 表无 migration 管理 | 只加索引不加约束，写入操作确认字段兼容性 |
| sys_company_id 数据质量 | 联系人查询对 NULL sys_company_id 做防御性处理（返回空列表） |
| 退订/退信状态丢失 | D14 已知悉，接受风险 |
| employee_size 格式差异 | 实施时确认值域，必要时调整解析逻辑 |

## 来源与参考

- **Origin document:** [openspec/changes/2026-05-19-tenant-companies-wmt-datasource/](openspec/changes/2026-05-19-tenant-companies-wmt-datasource/)
  - [proposal.md](openspec/changes/2026-05-19-tenant-companies-wmt-datasource/proposal.md) — 15 个工程决策（D1-D15）
  - [design.md](openspec/changes/2026-05-19-tenant-companies-wmt-datasource/design.md) — 11 节详细设计
  - [tasks.md](openspec/changes/2026-05-19-tenant-companies-wmt-datasource/tasks.md) — 7 个任务分解
- 相关代码: `backend/app/services/admin_collection_service.py` — wmt 查询参考模式
- 机构经验: `docs/solutions/best-practices/fk-column-migration-null-old-values-before-constraint-2026-05-07.md`
- 机构经验: `docs/solutions/best-practices/admin-waimaotong-fullstack-display-rewrite-2026-05-19.md`
