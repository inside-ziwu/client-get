## Context

发送计划页后端已完整就绪（计划 CRUD、complete-create、步骤配置、收件人锁定/预览、生命周期控制、Worker 发送、EngageLab 集成），前端只有骨架页面。需要将新建页重写为向导式，详情页改造为纵向分区+执行控制。

现有代码资产：
- 后端 `complete-create` API + `_normalize_complete_plan_payload()` 校验逻辑（`tenant_messaging_service.py:1659-1716`）
- 后端生命周期控制：start/pause/resume/cancel（`messaging.py:154-210`）
- 前端 `sending-plans.ts` API 客户端已有 CRUD + steps + recipients + 执行控制方法（缺 `completeCreate`）
- 前端 `email-templates.ts` API 客户端已完整（含 list、detail、preview）
- 前端 `groups.ts` API 客户端已完整（含 list）
- 共享 UI 组件库无 Stepper/Wizard 组件，需自建向导步骤指示器

## Goals / Non-Goals

**Goals:**
- 新建页重写为四步向导（基本信息 → 配置步骤 → 收件人 → 确认），调用 `complete-create` 一次提交
- 详情页改造为纵向分区（概览+步骤+收件人+发送日志）+ 执行控制按钮
- 后端 3 处 JOIN 微调 + 1 处过滤参数（listSteps 返回模板名、listRecipients 返回 enrollment 状态、GET /emails 加 plan_id）
- 前端 API 客户端新增 `completeCreate` 方法

**Non-Goals:**
- 不改数据库 schema
- 不在详情页提供编辑步骤/追加收件人
- 不做邮件模板编辑
- 不做 A/B 测试或发送时间优化

## Decisions

### D1: 向导步骤结构

```
┌─────────────────────────────────────────────────────────────┐
│  ① 基本信息    ② 配置步骤    ③ 收件人    ④ 确认             │
│  ━━━━━━━━━     ──────────    ────────    ────              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  当前步骤的表单内容                                          │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                              [上一步]  [下一步 / 创建计划]   │
└─────────────────────────────────────────────────────────────┘
```

四步向导，步骤指示器用简单的编号+标题横排，当前步骤高亮。不引入独立 Stepper 组件，直接在页面内用 div+样式实现。第四步为只读确认页，展示前三步配置摘要，用户确认后点"创建计划"提交。

### D2: 向导 Step 1 — 基本信息

表单字段与 `complete-create` payload 的 `plan` 对象对应：

| 字段 | 组件 | 必填 | 数据源 |
|------|------|------|--------|
| 计划名称 `name` | Input | 是 | 用户输入 |
| 描述 `description` | Textarea | 否 | 用户输入 |
| 发件人名称 `sender_name` | Input | 是 | 用户输入 |
| 发件邮箱 `sender_email` | Input | 是 | 用户输入 |
| 发送域名 `domain_id` | Select | 是 | `GET /sending-domains` |

发送域名下拉列表从后端获取，只显示 `verification_status = 'verified'` 的域名。选中域名后自动填充 `sender_email` 的域名部分（如有需要）。

### D3: 向导 Step 2 — 配置步骤

```
┌─────────────────────────────────────────────────────────────┐
│  步骤 1                                                     │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ 邮件模板 [下拉]   │  │ 延迟天数 [0]     │                 │
│  └──────────────────┘  └──────────────────┘                 │
│  触发条件: 始终发送（第一步固定）                              │
│  □ 启用 AI 个性化   AI 指令: [...]                          │
├─────────────────────────────────────────────────────────────┤
│  步骤 2                                                     │
│  ┌──────────────────┐  ┌──────────────────┐                 │
│  │ 邮件模板 [下拉]   │  │ 延迟天数 [3]     │                 │
│  └──────────────────┘  └──────────────────┘                 │
│  触发条件: [下拉: 未回复 / 已打开 / 已点击]                   │
│  □ 启用 AI 个性化   AI 指令: [...]                          │
│                                                      [删除] │
├─────────────────────────────────────────────────────────────┤
│                                            [+ 添加步骤]     │
└─────────────────────────────────────────────────────────────┘
```

每个步骤对应 `steps[]` 数组中的一个对象：

```typescript
{
  step_number: number,      // 自动递增，从 1 开始
  template_id: string,      // 从模板列表选择
  delay_days: number,       // 输入框，默认 0（第一步）/ 3（后续）
  condition_type: string,   // 第一步固定 "always"，后续默认 "no_reply"
  use_ai_personalization: boolean,
  ai_instructions?: string
}
```

规则：
- 至少 1 个步骤
- 第一步 `condition_type` 固定为 `"always"`，`delay_days` 固定为 `0`，前端锁定不可改
- 后续步骤 `condition_type` 可选：`no_reply`（默认）/ `opened` / `clicked`
- 模板列表从 `GET /email-templates` 加载
- 添加步骤：在末尾追加，`step_number` 自动递增
- 删除步骤：删除后重新编号

### D4: 向导 Step 3 — 收件人选择

```
┌─────────────────────────────────────────────────────────────┐
│  收件人来源: [下拉: 按群组]                                   │
│                                                             │
│  选择群组: [下拉: 群组列表]                                   │
│                                                             │
│  □ 创建后立即锁定收件人                                       │
│                                                             │
│  ┌─ 收件人预览 ───────────────────────────────────────────┐ │
│  │ 公司          │ 联系人       │ 邮箱          │ 状态     │ │
│  │ ABC Corp     │ 张三         │ z@abc.com    │ 可发送   │ │
│  │ XYZ Ltd      │ 李四         │ l@xyz.com    │ 可发送   │ │
│  │ DEF Inc      │ 王五         │ w@def.com    │ 已排除   │ │
│  └─────────────────────────────────────────────────────────┘ │
│  合计 3 人，可发送 2 人，已排除 1 人                           │
└─────────────────────────────────────────────────────────────┘
```

数据流：
- 收件人来源：第一期只实现 `group` 模式，Select 下拉选择
- 选择群组后，`recipient_config` 设为 `{ group_id: selectedGroupId }`
- 收件人预览：调 `GET /sending-plans/{plan_id}/recipients/preview` — 但此时计划尚未创建，无法调用。改为前端展示群组成员列表（调 `groups.listMembers(groupId)`）作为参考预览
- "锁定收件人" 勾选框控制 `lock_recipients` 字段，默认勾选（true）

### D5: 向导 Step 4 — 确认总览

```
┌─────────────────────────────────────────────────────────────┐
│  § 基本信息                                                  │
│  计划名称: xxx    发件人: xxx    发件邮箱: xxx@yyy.com        │
│  发送域名: yyy.com    描述: xxxxxxx                          │
├─────────────────────────────────────────────────────────────┤
│  § 发送步骤 (3 步)                                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ # │ 模板名称     │ 延迟  │ 触发条件  │ AI 个性化      │   │
│  │ 1 │ 首次联系     │ 立即  │ 始终发送  │ 否             │   │
│  │ 2 │ 跟进提醒     │ 3 天  │ 未回复    │ 是             │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  § 收件人                                                    │
│  来源: 群组 — "重点客户"    锁定收件人: 是                     │
│  预估收件人数: 42 人                                          │
└─────────────────────────────────────────────────────────────┘
```

只读展示前三步所有配置。模板名称从前端已加载的模板列表中取（无需额外 API 调用）。用户可点"上一步"修改任意步骤。

### D5b: 向导提交

在确认步骤点击"创建计划"后：

```
前端构建 payload:
{
  plan: {
    name, description, sender_name, sender_email, domain_id,
    recipient_source: "group",
    recipient_config: { group_id: selectedGroupId }
  },
  steps: [{ step_number, template_id, delay_days, condition_type, ... }],
  lock_recipients: boolean  // 默认 true
}

↓ POST /sending-plans/complete-create

成功 → toast + router.push(`/send-plans/${plan.id}`)
失败 → toast.error(message)，留在当前页
```

### D6: 详情页纵向分区

```
┌─────────────────────────────────────────────────────────────┐
│  PageHeader: {plan.name}                                    │
│  状态 Badge        [开始] [暂停] [恢复] [取消]  ← 按状态显隐  │
├─────────────────────────────────────────────────────────────┤
│  § 概览                                                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 发件人: xxx    发件邮箱: xxx@yyy.com    域名: yyy.com │   │
│  │ 收件人数: 42   已发送: 18   创建时间: 2026-05-19      │   │
│  │ 描述: xxxxxxx                                        │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  § 发送步骤（后端 JOIN email_templates 返回模板名称）          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ # │ 模板名称     │ 延迟  │ 触发条件  │ AI 个性化      │   │
│  │ 1 │ 首次联系     │ 立即  │ 始终发送  │ 否             │   │
│  │ 2 │ 跟进提醒     │ 3 天  │ 未回复    │ 是             │   │
│  │ 3 │ 最后通知     │ 7 天  │ 未回复    │ 否             │   │
│  └──────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  § 收件人（后端 LEFT JOIN sequence_enrollments）              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 公司       │ 邮箱           │ 状态    │ 当前步骤      │   │
│  │ ABC Corp  │ z@abc.com     │ active │ 2             │   │
│  │ XYZ Ltd   │ l@xyz.com     │ sent   │ 1             │   │
│  │ ...                                                  │   │
│  └──────────────────────────────────────────────────────┘   │
│  分页: [< 1 2 3 >]                                          │
├─────────────────────────────────────────────────────────────┤
│  § 发送日志                                                  │
│  数据源: GET /emails?plan_id={id}（后端加 plan_id 过滤参数）  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ 收件人     │ 主题           │ 状态    │ 发送时间      │   │
│  │ z@abc.com │ 首次联系...    │ sent   │ 05-19 10:30  │   │
│  │ l@xyz.com │ 首次联系...    │ opened │ 05-19 10:31  │   │
│  └──────────────────────────────────────────────────────┘   │
│  分页: [< 1 2 3 >]                                          │
└─────────────────────────────────────────────────────────────┘
```

### D7: 执行控制按钮状态映射

```typescript
const ACTION_MAP: Record<string, { label: string; action: string; variant: string }[]> = {
  draft:     [{ label: '开始发送', action: 'start',  variant: 'default' }],
  scheduled: [{ label: '立即开始', action: 'start',  variant: 'default' },
              { label: '取消计划', action: 'cancel', variant: 'destructive' }],
  running:   [{ label: '暂停',    action: 'pause',  variant: 'outline' },
              { label: '取消',    action: 'cancel', variant: 'destructive' }],
  paused:    [{ label: '恢复',    action: 'resume', variant: 'default' },
              { label: '取消',    action: 'cancel', variant: 'destructive' }],
  completed: [],
  cancelled: [],
};
```

取消操作弹出 AlertDialog 二次确认："确定取消此发送计划？已发送的邮件不受影响。"

### D8: 前端文件结构

```
send-plans/
  page.tsx                    # 列表页（不改）
  new/
    page.tsx                  # 向导主页面（状态管理 + 步骤切换）
    step-basic-info.tsx       # Step 1 基本信息表单
    step-configure-steps.tsx  # Step 2 步骤配置
    step-recipients.tsx       # Step 3 收件人选择
    step-confirmation.tsx     # Step 4 确认总览（只读）
  [id]/
    page.tsx                  # 详情页（纵向分区 + 执行控制）
```

### D9: 向导状态管理

用 `useState` 管理向导整体状态，不引入额外状态库：

```typescript
const [currentStep, setCurrentStep] = useState(0);  // 0, 1, 2, 3
const [formData, setFormData] = useState<WizardFormData>({
  plan: { name: '', description: '', sender_name: '', sender_email: '', domain_id: '', recipient_source: 'group', recipient_config: {} },
  steps: [{ step_number: 1, template_id: '', delay_days: 0, condition_type: 'always', use_ai_personalization: false }],
  lock_recipients: true,
});
```

每个步骤组件接收 `formData` 和 `onChange` 回调，实时更新父组件状态。点"下一步"前做当前步骤的前端校验（必填项检查），不通过则不允许前进。

### D10: 发送域名数据源

向导 Step 1 加载发送域名列表：调 `GET /domains`（`ops.py:403`），前端客户端 `tenantApi.domains.list()` 已就绪。下拉列表只显示 `verification_status = 'verified'` 的域名。
