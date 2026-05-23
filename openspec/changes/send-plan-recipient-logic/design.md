## Context

发送计划创建流程第 3 步"收件人"，用户选择群组后展示收件人预览。当前存在两个独立的代码路径：

1. **预览路径**：`step-recipients.tsx` → `tenantApi.groups.listMembers()` → `ops_service.list_group_members()` — 每公司显示 1 个联系人，用于群组管理
2. **实际选取路径**：`tenant_messaging_service._recipients_from_group()` — 返回群组内所有有邮箱联系人，无排序、无限数

两条路径逻辑不一致，且都未接入联系人分类等级体系。

现有分类基础设施：
- `position_classification_levels` 表：等级定义（sort_order, is_sendable）
- `v_tenant_contact_classified` 视图：实时匹配联系人职位 → 等级
- `contact_classification_service`：分类 CRUD

## Goals / Non-Goals

**Goals:**
- 统一预览和实际选取的收件人逻辑
- 接入联系人分类等级进行排序和过滤
- 每公司收件人上限 8 人

**Non-Goals:**
- 不重构 `_build_recipient_candidates()` 的排除过滤逻辑（blacklist/unsubscribed/bounced 等）
- 不修改手动选择 / 筛选器来源的收件人逻辑

## Decisions

### D1. 修改 `_recipients_from_group()` 而非新建方法

**选择**：直接在 `_recipients_from_group()` 中加入分类 LEFT JOIN 和 `ROW_NUMBER() OVER (PARTITION BY company)` 窗口函数。

**理由**：此方法是群组收件人的唯一入口，修改它可同时影响预览和实际发送，保持逻辑统一。无需引入新的抽象层。

**替代方案**：创建 `_recipients_from_group_ranked()` 新方法 — 增加了两个方法要维护的负担，且需要确保调用方切换，复杂度不值得。

### D2. 新增预览 API 端点

**选择**：在 messaging 路由新增 `GET /api/v1/send-plans/preview-recipients?group_id={id}`，内部调用 `_build_recipient_candidates()` 获取完整候选人列表（含排除过滤），返回按公司分组的结果。

**理由**：
- 预览应使用与实际发送完全相同的选取逻辑（分类排序 + 8 人限制 + 排除过滤）
- 现有 `list_group_members()` 是群组管理端点，不应承担收件人选取职责
- 前端只需改一个 API 调用地址

**返回格式**：
```json
{
  "companies": [
    {
      "tenant_company_id": "...",
      "company_name": "...",
      "recipient_count": 3,
      "recipients": [
        {
          "contact_name": "...",
          "contact_email": "...",
          "level_name": "A级（决策层）",
          "excluded_reason": null
        }
      ]
    }
  ],
  "summary": {
    "company_count": 14,
    "recipient_count": 42
  }
}
```

### D3. SQL 排序策略

**选择**：在 `_recipients_from_group()` 的 SQL 中使用 LEFT JOIN + ROW_NUMBER 窗口函数：

```sql
LEFT JOIN v_tenant_contact_classified vcc ON vcc.contact_id = shc.id
LEFT JOIN position_classification_levels pcl ON pcl.id = vcc.level_id
```

排序规则：
1. `pcl.is_sendable DESC NULLS LAST` — 可发送的优先
2. `pcl.sort_order DESC NULLS LAST` — 等级高的优先
3. `shc.id ASC` — 稳定排序兜底

然后用 `ROW_NUMBER() OVER (PARTITION BY gm.tenant_company_id ORDER BY ...)` 筛选 `rn <= 8`。

**注意**：使用 LEFT JOIN 确保未分类联系人不被丢弃（NULLS LAST 排到最后）。

**排除过滤时机（工程审查 D2 override）**：排除过滤（blacklist、unsubscribed、bounced、is_sendable=false、无邮箱）必须在 SQL 层面、ROW_NUMBER 之前完成，确保每公司 8 人名额全部是有效收件人，而非先取 8 个再排除。

**邮箱去重（工程审查补充）**：同一公司下同一邮箱可能关联多条联系人记录（不同职位）。在 ROW_NUMBER 之前按 `(tenant_company_id, email)` 去重，保留等级最高的记录，避免同一邮箱占用多个名额。

### D4. is_sendable 判断来源

**选择**：在 `_recipients_from_group()` 返回行中将 `is_sendable` 字段改为取自 `position_classification_levels.is_sendable`（通过 `v_tenant_contact_classified` 视图），而非 `tenant_contacts.is_sendable`。

**理由**：`tenant_contacts.is_sendable` 当前无前端配置入口，默认全部 true，实际无控制作用。admin 分类等级的 is_sendable 才是真正的发送控制开关。

未分类联系人（LEFT JOIN 不到分类等级）的 is_sendable 默认为 true（COALESCE），允许其作为候选人。

**前置检查（工程审查补充）**：实施前需查询生产数据确认是否存在 `tenant_contacts.is_sendable = false` 的记录。若存在，需评估这些记录的意图，决定是否在新逻辑中保留对该字段的兼顾。

## Risks / Trade-offs

- **[性能] 窗口函数对大量联系人的查询开销** → `v_tenant_contact_classified` 是 LATERAL JOIN 视图，对于联系人较多的公司可能较慢。当前业务规模下可接受，后续如有性能问题可考虑将分类结果物化到 `tenant_contacts` 表。
- **[分类覆盖率] 联系人职位为空或关键词未覆盖时全部走兜底** → 未分类联系人排最后但仍入选，不会因分类不全导致无收件人。

## Open Questions

（无）
