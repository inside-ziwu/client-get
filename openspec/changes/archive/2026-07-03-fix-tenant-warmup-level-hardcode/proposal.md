# Proposal: fix-tenant-warmup-level-hardcode

## Why

创建租户时若携带 `sender_domain`，起始预热档位与日发送上限走的是写死逻辑（档位钳制 1-6、日限映射 `{1:50 … 6:2000}`），与真实档位表 `warmup_rules` + `warmup_rule_levels` 完全脱节。生产激活规则已是 19 档（A/B 双实例同步），后果：

1. 管理端选 7 档及以上被 API 层（Pydantic `le=6`）直接拒绝，即便放行也会被服务层静默降到 6 档；
2. 写入 `domain_warmup_status.daily_limit` 的值与激活规则的 `warmup_rule_levels.daily_limit` 不一致（硬编码 6 档 2000，连 `init_instance` 种子的 4000 都对不上），而该字段是发送节流日配额台账与仪表盘配额的直接输入，写错会实际压低/放大发送量；
3. 初始化行缺 `warmup_rule_id` 与 `level_changed_at`，与管理端"添加域名"（`create_tenant_domain`）建立的行口径不一致，无法追溯所属规则。

DB 层 CHECK 约束已在迁移 `20260510_0037_domain_warmup_level_range` 放开为 `warmup_level >= 1`（意图即"跟随激活预热规则"），只剩 schema 与服务层没跟上。

## What Changes

- `backend/app/schemas/tenants.py`：`TenantCreateRequest.warmup_level` 去掉 `le=6` 上限（保留 `ge=1`），档位合法性改由服务层对照激活规则校验。
- `backend/app/services/tenant_service.py` `create_tenant`：
  - 删除档位钳制 `max(1, min(6, level))` 与硬编码日限映射；
  - `sender_domain` 非空时，查询**当前实例**（`instance_id`）激活（`is_active = true`）预热规则的档位表，校验所选档位存在；
  - 查不到（无激活规则或档位不存在）→ 抛 `AppError`（`VALIDATION_ERROR`, 422），拒绝创建（事务回滚，不产生半成品租户）；
  - 查到 → 以 `warmup_rule_levels.daily_limit` 真实值写入 `domain_warmup_status`，并补写 `warmup_rule_id` 与 `level_changed_at = now()`，与管理端添加域名的行口径对齐。
- 新增服务层测试 `backend/tests/test_tenant_create_warmup.py`（含 schema 校验用例）。

**BREAKING**（行为收紧）：创建租户携带 `sender_domain` 且档位在当前实例激活规则中不存在时，原先静默降档成功，现在返回 422 校验错误。这是本修复的目的（消除静默错误数据），管理端创建租户表单本就按规则档位提供选项，正常路径不受影响。

## Capabilities

### New Capabilities

- `tenant-domain-warmup-bootstrap`：创建租户时发件域名预热记录的初始化行为——档位以当前实例激活预热规则为准、日限取真实档位值、初始化行与管理端添加域名口径一致。

### Modified Capabilities

（无——`openspec/specs/` 下无既有 warmup / 租户创建相关能力域）

## Impact

| 影响面 | 说明 |
| --- | --- |
| API `POST /admin/api/v1/tenants`（`backend/app/api/admin/tenants.py`） | 请求体 `warmup_level` 不再限制 ≤6；非法档位从"静默降档"变为 422 |
| `backend/app/services/tenant_service.py` | 创建租户事务内新增一次档位查询（仅 `sender_domain` 非空时） |
| `domain_warmup_status` 数据 | 新建初始化行将带 `warmup_rule_id` / `level_changed_at`，`daily_limit` 与激活规则一致；存量行不回填（属数据订正，见 Non-Goals） |
| 发送链路（`tenant_messaging_service` 日配额台账、`tenant_query_service` 仪表盘配额） | 只读 `daily_limit` 消费方，无代码改动，受益于数据正确 |
| `backend/scripts/seed_demo_data.py` | 调用 `create_tenant`（warmup_level=3），种子规则含 3 档，行为不变；但 seed 前置要求库中存在激活规则（现状本已如此） |
| 数据库迁移 | **无**：`20260510_0037` 已放开 CHECK 约束，无新表/字段/索引 |
| 前端 | 无改动（管理端表单档位选项本就来自规则接口） |

历史决策关联：D-031（"创建租户时同步配置发件域名和起始预热档位"，见 `backend/app/schemas/tenants.py:15`、`backend/app/services/tenant_service.py:261` 代码注释；仓库内无 `_control/` 目录，无对应 C-xxx 编号可引）。本次为该决策实现与 19 档预热规则体系的对齐修复。

## Non-Goals

- 不回填/订正存量 `domain_warmup_status` 行（缺 `warmup_rule_id` 或 `daily_limit` 与规则不一致的历史数据订正另行处理）；
- 不写 `domain_warmup_history`（管理端添加域名写 history 是操作人视角；租户 bootstrap 已有租户创建审计，保持最小修复面）；
- 不改动管理端"添加域名 / 更新域名"既有校验逻辑（`admin_config_service`，其本就按规则表校验）；
- 不引入预热规则缺失时的自动建规则/兜底档位逻辑；
- 不改前端。
