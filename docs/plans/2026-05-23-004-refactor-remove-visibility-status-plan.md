---
title: "refactor: 移除 tenant_companies.visibility_status 列"
status: active
origin: openspec/changes/2026-05-23-remove-visibility-status/proposal.md
created: 2026-05-23
type: refactor
depth: lightweight
---

# refactor: 移除 tenant_companies.visibility_status 列

## 摘要

纯减法重构：彻底移除 `tenant_companies.visibility_status` 列及所有相关逻辑。当前阶段不支持关键词取消（关键词只增不减，公司只进不出），visibility 状态管理完全失去意义。17 处查询过滤、`hide_tenant_companies_for_cancelled_keyword` 函数、fan-out/lineage-repair 中的 visibility 逻辑一并清除。

(see origin: `openspec/changes/2026-05-23-remove-visibility-status/proposal.md`)

---

## 问题背景

- `visibility_status` 默认 `'hidden'` 导致收件人查询 bug（已修 commit 4b6772a）
- 17 处 `AND visibility_status = 'visible'` 增加每次改动的认知负担
- `hide_tenant_companies_for_cancelled_keyword` 在隐藏时无差别清空用户数据，行为过激
- 生产数据 99% tenant_companies 是扇出空壳，visibility 管理收益极低
- 线上无实际运营，可直接 DROP COLUMN

---

## 范围边界

**包含**：DROP COLUMN visibility_status（含约束/索引）、移除 17 处过滤、删除 hide 函数、fan-out/lineage-repair 简化、assert 函数重命名、rebuild 脚本清理

**不包含**：fan-out 架构重构、关键词取消功能、前端代码（无引用）、存量数据清理

### Deferred to Follow-Up Work

- fan-out 架构重构（直接查 wmt 替代预物化）— 当前规模无性能差异，未来再评估

---

## 关键技术决策

1. **直接 DROP COLUMN** — 线上无运营，不需先刷存量
2. **关键词只增不减** — delete_keyword 只 soft-delete keyword 记录，tenant_companies 不动
3. **孤儿清理改 DELETE** — lineage_repair stale 从 UPDATE hidden 改为 DELETE，ON DELETE CASCADE 清理关联
4. **assert 重命名** — `_assert_visible_tenant_company` → `_assert_tenant_company_exists`

---

## 执行姿态

TDD 驱动：每个实施单元先写测试验证预期行为，再改代码使测试通过。每单元 CC 耗时 2-5 分钟。

---

## 实施单元

### U1. fan_out — 简化 INSERT + 删除 hide 函数

**Goal**: 移除 `fan_out.py` 中全部 visibility_status 逻辑，删除 hide 函数

**Requirements**: proposal D2

**Dependencies**: 无

**Files**:
- `backend/app/workers/fan_out.py`（修改）
- `backend/tests/test_fan_out_no_visibility.py`（新建）

**Approach**:
- `run_fan_out_for_tenant_keyword` INSERT 去掉 `visibility_status` 列和 `'visible'` 值
- ON CONFLICT 去掉 `SET visibility_status = 'visible'`，保留 `data_status` 和 `updated_at` 更新；将 WHERE 条件从 `visibility_status <> 'visible'` 改为 `data_status IS DISTINCT FROM EXCLUDED.data_status`，避免无变更时触发冗余更新
- 删除整个 `hide_tenant_companies_for_cancelled_keyword` 函数

**Execution note**: 先写测试验证 SQL 不含 visibility_status 且 hide 函数不可导入

**Test scenarios**:
- `run_fan_out_for_tenant_keyword` 构造的 INSERT SQL 不包含 `visibility_status`
- ON CONFLICT 只更新 `data_status` 和 `updated_at`
- `hide_tenant_companies_for_cancelled_keyword` 不存在于 `fan_out` 模块

**Verification**: `grep visibility_status backend/app/workers/fan_out.py` 返回空

---

### U2. wmt_lineage_repair — 简化 SQL + stale 改 DELETE

**Goal**: 移除 lineage repair 的 visibility 逻辑，stale 处理从 UPDATE hidden 改为 DELETE

**Requirements**: proposal D3

**Dependencies**: 无

**Files**:
- `backend/app/workers/wmt_lineage_repair.py`（修改）
- `backend/tests/test_lineage_repair_no_visibility.py`（新建）

**Approach**:
- `_SQL_FAN_OUT_ACTIVE_KEYWORDS`：INSERT 去掉 `visibility_status` 列和 `'visible'`；ON CONFLICT 去掉全部 visibility_status 相关设置和 WHERE 条件，只保留 `data_status` 和 `updated_at`
- `_SQL_HIDE_STALE_RELATIONS` → `_SQL_DELETE_STALE_RELATIONS`：从 `UPDATE SET hidden` 改为 `DELETE FROM tenant_companies WHERE NOT EXISTS wmt`
- `_SQL_VISIBLE_JOIN_COUNT` → `_SQL_ACTIVE_JOIN_COUNT`：去掉 `WHERE visibility_status = 'visible'`
- 更新 `run_wmt_lineage_repair_on_connection` 中变量名和 stats key（`hidden_stale` → `deleted_stale`，`visible_join` → `active_join`）

**Execution note**: 先写测试验证 SQL 变量内容和 stats key

**Test scenarios**:
- `_SQL_FAN_OUT_ACTIVE_KEYWORDS` SQL 文本不含 `visibility_status`
- `_SQL_DELETE_STALE_RELATIONS` 执行 DELETE 而非 UPDATE
- `_SQL_ACTIVE_JOIN_COUNT` 不带 visibility 过滤
- `run_wmt_lineage_repair_on_connection` 返回 stats 使用 `deleted_stale` 和 `active_join` key

**Verification**: `grep visibility_status backend/app/workers/wmt_lineage_repair.py` 返回空

---

### U3. tenant_settings_service — 移除 hide 调用

**Goal**: 关键词更新/删除时不再调用 hide 函数，只保留 soft-delete

**Requirements**: proposal D2

**Dependencies**: U1（hide 函数已删除）

**Files**:
- `backend/app/services/tenant_settings_service.py`（修改）
- `backend/tests/test_settings_no_hide.py`（新建）

**Approach**:
- 删除 `from app.workers.fan_out import hide_tenant_companies_for_cancelled_keyword` 导入（只保留 `run_fan_out_for_tenant_keyword`）
- `update_keyword`（:124-129）：移除 hide 旧关键词调用，只保留 bind + fan-out 新关键词
- `delete_keyword`（:206-210）：移除 hide 调用，只保留 soft-delete keyword + tenant_keyword status 更新

**Execution note**: 先写测试验证 update/delete 不调用 hide

**Test scenarios**:
- 模块不再导入 `hide_tenant_companies_for_cancelled_keyword`
- `update_keyword` 更换关键词时只执行 fan-out，不调用 hide
- `delete_keyword` 只 soft-delete，不调用 hide，tenant_companies 不受影响

**Verification**: `grep hide_tenant backend/app/services/tenant_settings_service.py` 返回空

---

### U4. tenant_ops_service — 移除 7 处过滤 + INSERT 清理 + 重命名

**Goal**: 移除 ops 服务全部 visibility 逻辑，重命名 assert 函数

**Requirements**: proposal T2, D4

**Dependencies**: 无

**Files**:
- `backend/app/services/tenant_ops_service.py`（修改）
- `backend/tests/test_ops_no_visibility.py`（新建）

**Approach**:
- 移除 :28, :46, :69, :97, :298, :674, :720 共 7 处 `AND visibility_status = 'visible'` 过滤
- :208 INSERT 去掉 `visibility_status` 列和 `'visible'` 值
- :1154 `_assert_visible_tenant_company` → `_assert_tenant_company_exists`，移除 visibility 过滤
- :709 调用点同步更新方法名

**Execution note**: 先写测试验证 assert 函数不检查 visibility

**Test scenarios**:
- `_assert_tenant_company_exists` 只检查 tenant_id + company_id 存在性
- `create_company` INSERT 不含 `visibility_status` 列
- `dashboard_funnel` 查询不带 visibility 过滤
- `companies_filters` 各子查询不带 visibility 过滤
- 无 `_assert_visible_tenant_company` 残留引用

**Verification**: `grep visibility_status backend/app/services/tenant_ops_service.py` 返回空

---

### U5. tenant_query_service — 移除 4 处过滤

**Goal**: 移除公司列表/详情查询中的 visibility 过滤

**Requirements**: proposal T2

**Dependencies**: 无

**Files**:
- `backend/app/services/tenant_query_service.py`（修改）

**Approach**:
- :32-33 `dashboard_overview` 两个子查询移除 `AND visibility_status = 'visible'`
- :182 `companies_page` 移除 `tc.visibility_status = 'visible'` 条件
- :445/:453 `v3_company_detail` 移除 SELECT 中的 `tc.visibility_status` 和 WHERE 过滤
- :598 第二个列表方法移除过滤条件

**Test scenarios**:
- Test expectation: none — 纯 SQL 字符串删减，通过 grep 验证

**Verification**: `grep visibility_status backend/app/services/tenant_query_service.py` 返回空

---

### U6. tenant_messaging_service + webhook — 移除 6 处过滤

**Goal**: 移除发送计划和 webhook 查询中的 visibility 过滤

**Requirements**: proposal T2

**Dependencies**: 无

**Files**:
- `backend/app/services/tenant_messaging_service.py`（修改）
- `backend/app/services/webhook_service.py`（修改）

**Approach**:
- tenant_messaging_service.py：移除 :781, :2064, :2090, :2112, :2135 共 5 处 `AND visibility_status = 'visible'` / `AND tc.visibility_status = 'visible'`
- webhook_service.py：移除 :133 的 1 处过滤

**Test scenarios**:
- Test expectation: none — 纯 SQL 字符串删减，通过 grep 验证

**Verification**: 两文件 grep visibility_status 返回空

---

### U7. Alembic 迁移 + rebuild 脚本清理

**Goal**: DDL 移除 visibility_status 列，清理 rebuild 脚本

**Requirements**: proposal D1

**Dependencies**: U1-U6（所有代码引用已移除）

**Files**:
- `backend/alembic/versions/20260523_0200_drop_visibility_status.py`（新建）
- `backend/scripts/rebuild_tenant_companies.py`（修改）

**Approach**:
- 迁移按序执行：DROP CONSTRAINT `tenant_companies_visibility_status_check` → DROP INDEX `idx_tenant_companies_tenant_visibility` → DROP COLUMN `visibility_status`
- revision 命名 `20260523_0200`，down_revision 为 `20260523_0100`
- `rebuild_tenant_companies.py`：`_SQL_COUNT_CURRENT` 去掉 `FILTER (WHERE tc.visibility_status = 'visible') AS visible` 统计；`_SQL_INSERT_FOR_KEYWORD` INSERT 去掉 `visibility_status` 列和 `'visible'` 值；打印逻辑同步去掉 `visible` 字段引用

**Test scenarios**:
- Test expectation: none — 迁移通过 `alembic upgrade head` 验证

**Verification**: `alembic upgrade head` 成功，`\d tenant_companies` 无 visibility_status 列

---

### U8. 全局验证

**Goal**: 确认零残留，端到端完整性

**Dependencies**: U1-U7

**Approach**:
- `grep -rn visibility_status backend/` 排除 alembic 迁移文件和 `__pycache__`，确认零结果
- `grep -rn hide_tenant_companies backend/` 确认零结果
- `grep -rn _assert_visible_tenant_company backend/` 确认零结果
- 启动后端 `uvicorn` 确认无 import 报错

**Test scenarios**:
- Test expectation: none — 纯验证步骤

**Verification**: 所有 grep 零结果，后端启动正常

---

## 系统影响

| 路径 | 变更 | 影响 |
|------|------|------|
| `fan_out.py` | INSERT 简化 + 删除 hide 函数 | fan-out 写入逻辑变简单，不再有 visibility 状态切换 |
| `wmt_lineage_repair.py` | stale 从 UPDATE hidden 改为 DELETE | 孤儿公司直接删除，CASCADE 清理子表 |
| `tenant_settings_service.py` | 删除 hide 调用 | 关键词删除只 soft-delete，不触碰 tenant_companies |
| 4 个 service 文件 | 移除 17 处过滤 | 所有公司查询不再有 visibility 筛选 |
| alembic 迁移 | DROP COLUMN | 数据库永久移除该列 |

---

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| DROP COLUMN 不可逆 | 线上无运营；回退方案：ADD COLUMN + 重跑 fan-out |
| 部署顺序 | `/start.sh` 先跑 `alembic upgrade head` 再启 uvicorn，天然原子 |
| 孤儿 DELETE 的 CASCADE 影响 | 生产 0 条 sending_plan_recipients，4 个 FK 均 CASCADE |
