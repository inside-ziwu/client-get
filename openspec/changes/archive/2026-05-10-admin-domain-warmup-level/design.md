## Context

当前 admin 客户/租户详情的“添加域名”只提交域名地址。后端 `create_tenant_domain` 虽然已支持 `warmup_level` / `daily_limit` payload，但前端未提供档位选择，且后端默认日限是固定值，不能反映“预热规则”页面里 active warmup rule 的 levels 配置。

本 change 只修新增域名时的起始档位与每日可发上限初始化。它不处理联系人分类、邮件计划收件人选择、sending worker 执行，也不要求本次接入真实 EngageLab 域名验证 API。

## Goals / Non-Goals

**Goals:**

- Admin 添加租户发件域名时，运营必须选择起始预热档位。
- 档位选项来自当前 active warmup rule 的 levels，并展示每档日限。
- 后端以提交时最新 active warmup rule 的对应 level 为准查询 `warmup_rule_levels.daily_limit`，写入 `domain_warmup_status.daily_limit`。
- 后端拒绝过期或非法档位选择，避免 UI 打开后规则变化导致错误日限落库。
- 域名管理列表展示新增域名、预热档位、每日上限，让运营能看到最终落库结果。

**Non-Goals:**

- 不修改联系人分类或邮件计划选人逻辑。
- 不修改 sending worker 限速消费逻辑。
- 不新增 warmup rule 数据结构。
- 不在本 change 内实现 EngageLab 真实添加域名或 DNS 验证状态机。
- 不调整创建租户 Modal；本 change 只覆盖客户/租户详情内的“添加域名”入口。

## Decisions

1. **前端读取 active warmup rule 生成 Select 选项**

   使用已有 admin warmup rules API 获取规则列表，选择 `is_active=true` 的 rule。Select 的 value 使用 `warmup_level`，表单同时保存 `warmup_rule_id`。UI 中展示的日限用于辅助运营选择；最终落库日限以后端提交时查到的最新 active rule level 为准。

   备选方案是继续写死 1-6 档。该方案会让日限与预热规则页面配置漂移，已排除。

2. **前端不提交 `daily_limit`**

   `daily_limit` 是服务端根据规则推导出的业务结果，不应信任浏览器传入。前端只提交 `domain`、`warmup_rule_id`、`warmup_level`。

3. **后端按提交时最新 active rule level 推导日限**

   后端查询 active `warmup_rules` 与对应 `warmup_rule_levels`。若 `warmup_rule_id` 非 active 或没有对应 `warmup_level`，返回 422 校验错误，提示前端刷新后重选。若规则仍 active 且 level 仍存在，但 level 的 `daily_limit` 在弹窗打开后被修改，则接受请求并使用提交时后端查到的最新 `daily_limit`。

   备选方案是前端提交 rule `updated_at` 或 level 版本并要求严格一致。该方案会增加版本字段和交互复杂度；本需求只要求决定新增域名每日可发上限，因此采用 KISS 的“服务端最新配置为准”。

4. **域名列表展示最终档位和上限**

   `list_tenant_domains` 已返回 `warmup_level` 和 `daily_limit`，前端 shared 类型和表格列需要补齐。添加成功后刷新域名列表，运营应能看到新增域名、预热档位、每日上限。

5. **任务拆出独立 OpenSpec change**

   该修改只决定新增域名的起始预热档位与每日可发上限，和 `v3-contact-classification` 无直接关系。拆出独立 change 后，实施不再被邮件投递大链路的联系人分类前置任务阻塞。

## Risks / Trade-offs

- **Risk: 没有 active warmup rule** → 前端禁用提交并提示先配置预热规则；后端也返回校验错误。
- **Risk: 弹窗打开后日限被修改** → 后端使用提交时最新 active rule level 的 `daily_limit`；域名列表展示最终落库上限，避免运营只依赖弹窗旧值。
- **Risk: 旧调用方只传 domain** → 后端可返回明确校验错误；本 change 只要求 admin 新 UI 使用新契约。
