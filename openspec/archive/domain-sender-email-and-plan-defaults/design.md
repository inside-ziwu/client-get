## Context

当前 `domain_warmup_status` 表没有 `sender_email` 字段，域名只能通过 admin 创建和验证，无编辑/删除端点。tenant 端新建计划向导的基本信息步骤（`step-basic-info.tsx`）三个字段默认为空字符串，用户每次手动填写。

admin 域名管理嵌在租户详情 sheet 的"域名" tab 内（`client-page.tsx:617-687`），目前只有添加表单和域名列表表格，列表操作只有"验证域名"按钮。

## Goals / Non-Goals

**Goals:**
- `domain_warmup_status` 表新增 `sender_email` 列
- Admin 域名端点支持编辑（PATCH）和删除（DELETE）
- Admin 创建域名时支持传入 `sender_email`
- Tenant 域名列表 API 返回 `sender_email`
- Tenant 新建计划向导自动填入默认值（发件人名称、发件邮箱、发送域名）

**Non-Goals:**
- 不修改 tenant 端域名 CRUD（保持只读）
- 不改动向导其他步骤
- 不做发件邮箱格式校验以外的业务校验

## Decisions

### D1: sender_email 存储在 domain_warmup_status 表

**选择**: 在 `domain_warmup_status` 表新增 `sender_email varchar(255)` 可空字段

**替代方案**: 新建 domain_config 表单独存储 → 增加表数量和 JOIN，数据量不支撑分表

**理由**: 一域名一邮箱的关系简单，直接加字段最简洁

### D2: 域名删除使用物理删除

**选择**: 直接 DELETE，不做软删除

**替代方案**: 增加 deleted_at 软删除 → 增加查询复杂度，域名删除前已有活跃计划检查保护

**理由**: 域名数据量小，删除前有引用检查保护，物理删除足够

### D3: 编辑域名时暖机规则变更触发 daily_limit 重算

**选择**: 编辑暖机规则/档位时，根据新规则的 level 查询对应 daily_limit 并更新

**理由**: 与创建时的逻辑一致，保持 daily_limit 始终与暖机规则档位同步

### D4: 默认域名选择逻辑放在前端

**选择**: 前端加载 verified 域名列表后按 `created_at` 排序取第一个

**替代方案**: 后端提供 /default-domain 端点 → 多一次请求，域名列表已包含足够信息

**理由**: 域名列表已返回 `created_at`，前端排序取默认无额外请求开销

### D5: 域名切换联动发件邮箱在前端完成

**选择**: 域名下拉变更时，前端从已加载的域名列表中查找对应 `sender_email` 并填入

**理由**: 域名列表已包含 `sender_email`，无需额外 API 调用

### D6: 域名行操作使用 DropdownMenu 三点菜单

**选择**: 所有行操作（验证域名、编辑、删除）收纳在 DropdownMenu 中

**替代方案**: 编辑按钮外露 + 菜单藏验证/删除 → 与现有 tab 不统一

**理由**: 三个操作用三点菜单更整洁，表格列宽可控

### D7: 删除域名 409 错误在弹窗内展示

**选择**: AlertDialog 保持打开，显示红色 destructive 错误文本

**替代方案**: 关闭弹窗 + toast.error → 项目全局用 toast，但重要错误信息需要更显眩

**理由**: 用户需要明确知道为什么删不掉，弹窗内展示不会被错过

### D8: 编辑弹窗域名显示在 DialogDescription 中

**选择**: 域名作为 Dialog 描述文本，如"编辑 example.com 的配置"

**替代方案**: disabled Input 放在表单中 → 引入新的 disabled 输入模式

**理由**: 域名是弹窗的上下文信息而非可编辑字段，语义更清晰

### D9: 编辑弹窗字段垂直排列

**选择**: 发件邮箱、预热规则、预热档位三个字段单列垂直排列

**替代方案**: 邮箱独占一行 + 预热两字段并排 → 认知分组更好但复杂度高

**理由**: 用户选择简单布局，三个字段垂直排列清晰直观

### D10: 新建计划页镜像 edit 页预加载模式

**选择**: new/page.tsx 预加载 /me + 域名列表，包含 loading + error + 正常三种状态

**替代方案**: 简化版只处理 loading → 失败时用户看到空表单不知原因

**理由**: 与 edit 页代码模式对称，已有模板可复制

## Risks / Trade-offs

- [现有域名无 sender_email] → 迁移后默认 NULL，tenant 端遇到无邮箱的域名时留空提示用户填写
- [域名删除不可恢复] → 删除前强制检查活跃计划引用 + 前端确认弹窗双重保护
