# 08 UI 规格（后端对齐修复版）

本文件不替代 UI 细节，而是把 UI 对后端的要求修成明确 API/数据合同。

## 1. Admin UI 对后端要求

### 数据源管理

后端必须返回：

- 渠道列表：name、source_type、alias_code、purpose、is_active。
- 账号列表：account_no、username_masked、daily_quota、current_day_used、last_error、is_active。
- 采集配置：request_interval_seconds、batch_size、execution_window、landing_rules。

禁止返回明文 credentials。

### 评分模板管理

后端必须支持平台模板，而不是直接改租户模板。

- 平台模板用于新租户复制。
- 已入驻租户不受平台模板后续修改影响。

### 域名预热规则

UI 可能展示 20/50/100/200/500/1000，也可能展示 50/100/200/500/1000/4000。最终以后端 `warmup_rule_levels` 为准，默认采用 50/100/200/500/1000/4000。

### AI 配置

UI 显示“API Key”时，后端只返回 masked key 或 key version。真实 Key 不从 API 返回。

## 2. Tenant UI 对后端要求

### AI 余额

- admin 可以看余额。
- operator/viewer 只能看能力态，不看金额。
- Phase 1 自助充值按钮应隐藏或 disabled。

### 公司详情 Drawer

`GET /companies/{id}` 必须一次返回或可并行返回：

- 基本信息。
- 评分明细。
- 联系人列表 + is_default。
- 邮件记录。

### 优选客户与群组

群组显示的是公司集合，不是联系人集合。发送时才解析默认联系人。

### 发送计划 6 步

后端支持两种实现：

1. 一次性 `POST /sending-plans` 提交完整 payload。
2. 渐进保存：先创建 draft，再 PATCH、steps、recipients/preview、recipients/lock。

推荐实现 2，因为前端向导可保存草稿。

## 3. 状态与颜色

后端只返回机器状态，前端负责颜色：

- plan status：draft/scheduled/running/paused/completed/cancelled。
- email status：pending/queued/sent/delivered/opened/clicked/replied/bounced/complained/unsubscribed/failed。
- company business_status 与 data_status 分开返回。

## 4. 空态与错误

后端应为 UI 提供可解释错误：

- `NO_VERIFIED_DOMAIN`
- `NO_RECIPIENTS`
- `INSUFFICIENT_AI_BALANCE`
- `DOMAIN_QUOTA_EXCEEDED`
- `RECIPIENTS_NOT_LOCKED`
- `TEMPLATE_MISSING`
- `TENANT_ONBOARDING_REQUIRED`
