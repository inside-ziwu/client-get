## Why

当前 admin 添加域名时只能设置域名和暖机配置，无法维护发件邮箱地址，域名也不支持编辑和删除。tenant 端新建发送计划时，基本信息三个核心字段（发件人名称、发件邮箱、发送域名）没有默认值，用户每次都需要手动填写。

## What Changes

**Admin 域名管理增强**
- `domain_warmup_status` 表新增 `sender_email varchar(255)` 字段
- 添加域名时支持填写发件邮箱（完整邮箱格式，一域名一邮箱）
- 域名支持编辑：可修改发件邮箱、暖机规则、暖机档位；域名本身不可修改
- 域名支持删除：删除前确认，被活跃计划（running/scheduled）引用时禁止删除

**Tenant 新建计划默认值**
- 发件人名称默认取 tenant 租户名称（`tenants.name`）
- 发送域名默认取已验证域名中 `created_at` 最早的一个
- 发件邮箱默认取选中域名的 `sender_email`；未维护则留空
- 切换域名时发件邮箱自动联动更新

## Non-Goals

- Tenant 端不增加域名管理功能
- 不改动向导的其他步骤（配置步骤、收件人、确认）
- 不做 @ 前缀自动拼接，发件邮箱存完整地址

## Capabilities

### New Capabilities

- `domain-crud`: Admin 域名编辑与删除（含活跃计划引用检查）
- `plan-basic-info-defaults`: Tenant 新建计划基本信息字段默认值填充与域名联动

### Modified Capabilities

（无现有 spec 变更）

## Impact

| 层级 | 影响范围 | 说明 |
|------|---------|------|
| 数据库 | `domain_warmup_status` 表 | 新增 `sender_email` 字段，Alembic 迁移 |
| 后端 API | Admin 域名端点 | 新增 PATCH、DELETE 端点；CREATE 增加 sender_email 参数 |
| 后端 API | Tenant 域名列表 | 返回值增加 sender_email 字段 |
| Admin 前端 | 租户详情 > 域名 tab | 表单增加发件邮箱；行操作增加编辑、删除 |
| Tenant 前端 | 新建计划向导 > 基本信息 | 默认值逻辑 + 域名切换联动 |

依赖顺序：数据库迁移 → 后端 API → 前端（admin + tenant 可并行）
