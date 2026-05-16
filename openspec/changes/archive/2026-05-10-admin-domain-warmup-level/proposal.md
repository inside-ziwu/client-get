## Why

Admin 在客户/租户详情中新增发件域名时，目前只能填写域名地址，后端默认按固定 1 档日限写入 `domain_warmup_status.daily_limit`。这会让新增域名的每日可发上限脱离“预热规则”页面的 active rule 配置，运营无法在添加域名时决定正确起始档位。

## What Changes

- Admin 客户管理/租户详情的“添加域名”弹窗增加“起始预热档位”选择。
- 档位选项从当前 active warmup rule 的 levels 读取，展示档位与对应日限。
- 添加域名提交 `domain`、`warmup_rule_id`、`warmup_level`；前端不提交 `daily_limit`。
- 后端创建 `domain_warmup_status` 时，以提交时后端最新 active warmup rule 的对应 level 为准，查询 `warmup_rule_levels.daily_limit` 并落库。
- 后端校验提交的 warmup rule 仍为 active 且包含该 level；若规则失效或档位不存在，返回校验错误，提示运营刷新后重选。
- 域名管理列表新增后必须显示新增域名、预热档位、每日上限，便于运营确认最终落库结果。
- 不改联系人分类、邮件计划选人、sending worker、EngageLab 域名验证状态机。

## Capabilities

### New Capabilities
- `admin-domain-warmup-level`: Admin 添加租户发件域名时选择起始预热档位，由后端按提交时最新 active warmup rule 推导每日可发上限，并在域名列表显示最终档位和上限。

### Modified Capabilities

## Impact

- 前端：admin客户/租户管理页域名添加弹窗和域名管理列表、admin shared-api tenant domain 类型。
- 后端：admin tenant domain 创建服务校验和 `daily_limit` 推导。
- 数据库：不新增表和字段；继续使用 `warmup_rules`、`warmup_rule_levels`、`domain_warmup_status`。
- OpenSpec：该窄范围从 `v3-email-delivery` 大 change 中拆出，避免被联系人分类等后续投递链路任务阻塞。
