# 参考实现调研：aoqi-ai/sysdev-ft-marketing

> **目的**：用户提供的另一个 GitHub 仓库（外贸自动化营销系统）的当前运行逻辑调研，作为 V3 决策的参考基准。
> **重要**：这只是参考实现，**不是 V3 真源**。V3 真源是 [`_control/v3/00-v3-target-spec.md`](../v3/00-v3-target-spec.md)。
> **调研时间**：2026-05-05
> **仓库**：[aoqi-ai/sysdev-ft-marketing](https://github.com/aoqi-ai/sysdev-ft-marketing)（私有，已通过 gh CLI 探查）
> **最近推送**：2026-04-02（比当前 ClientGet 项目早 1 个月）

## 1. 项目定位

- **名称**：外贸获客营销系统（XAPCB 自用）
- **架构**：**单租户**——XAPCB 公司自己用，没有租户概念
- **栈**：Python 3.11+ / FastAPI / Prefect（工作流编排）/ PostgreSQL / OpenRouter / EngageLab / 网易外贸通
- **前端**：React 19 + TypeScript + Ant Design v6 + Vite

## 2. 核心 Flow 结构

4 个 Prefect Flow 串行：

```
Flow 01: keyword_collect    关键词采集（外贸通）
   ↓
Flow 02: company_analysis   公司清洗 + LLM 评分（A/B/C/D 等级）
   ↓ （此时 company_analysis.email_priority 自动赋值：grade A/B → selected, 其他 → skipped）
Flow 03: email_draft        AI 生成个性化开发信（draft 状态）
   ↓ （审批门控：需要 plan 审批 OR 草稿单独审批）
Flow 04: email_send         按工作时间窗口 + 预热档位调用 EngageLab 发送
```

**两个人工节点**：①审批计划 ②审批草稿

## 3. 你问的核心问题：**一公司一人 vs 多人？**

### 3.1 答案：**多人（默认所有有效联系人都发）**

### 3.2 实证（来自 `flows/flow_03_email_draft.py` 第 525-549 行）

```sql
SELECT c.sys_contact_id, c.sys_company_id, c.contact_id,
       c.email, cd.country, ca.grade, ca.score, ...
FROM contact_data c
INNER JOIN company_data cd ON c.sys_company_id = cd.sys_company_id
INNER JOIN company_analysis ca ON ca.sys_company_id = c.sys_company_id
  AND ca.grade IN ('A','B')
  AND ca.plan_id = %s
  AND ca.email_priority = 'selected'      -- 公司级过滤
LEFT JOIN email_drafts ed ON ed.sys_contact_id = c.sys_contact_id
  AND COALESCE(ed.round_number, 1) = %s
WHERE COALESCE(c.email, '') <> ''
  AND c.email ~ '^[a-zA-Z0-9._%%+\\-]+@...$'  -- 邮箱格式过滤
  AND ed.sys_contact_id IS NULL                 -- 未生成过草稿
  {functional_email_filter}                     -- 非功能性邮箱过滤
ORDER BY ca.score DESC NULLS LAST, c.id ASC
LIMIT %s                                         -- 全局限额（不按公司）
```

每条返回行 → 在 flow_03 末尾生成 1 条草稿（`INSERT INTO email_drafts ... ON CONFLICT (sys_contact_id, round_number) DO NOTHING`）。

### 3.3 二层过滤模型

| 层级 | 过滤项 | 来源 |
| --- | --- | --- |
| **公司级** | `company_analysis.grade IN ('A','B')` | flow_02 LLM 评分 |
| **公司级** | `company_analysis.email_priority = 'selected'` | flow_02 自动设置：grade A/B → 'selected'，其他 → 'skipped' |
| **联系人级** | 邮箱格式合法（正则） | flow_03 |
| **联系人级** | 非功能性邮箱（abuse/postmaster/info/support/... 等 30+ 关键词黑名单） | flow_03 第 444-454 行 |
| **联系人级** | 未生成过草稿（`ed.sys_contact_id IS NULL`） | flow_03 |
| **联系人级** | 排除中国 / 香港 / 台湾 / 澳门（v_buyer_contacts 非 plan 模式） | flow_03 |
| **限额** | 全局 `LIMIT %s`（不按公司分摊） | flow_03 |

**结果**：一家被选中（grade A/B）的公司，**所有有效联系人都生成草稿、都发送邮件**。每联系人每轮 1 封（唯一索引 `(sys_contact_id, round_number)`）。

### 3.4 没有"主联系人"概念

- 没有 `primary_contact_id` 字段
- 没有"职位优先级序列"配置
- 选谁发完全靠"过滤剩下谁就发谁"

## 4. 与 ClientGet 业务流的对照

| 维度 | aoqi 仓库当前实现 | ClientGet 业务流 §4.1 / §3.6 |
| --- | --- | --- |
| 目标人群策略 | **隐式"全部联系人"**（公司级筛 → 公司内全部有效联系人） | 显式 3 选 1：主联系人 / 全部联系人 / 自定义 |
| 主联系人概念 | ❌ 无 | ✅ 有（`tenant_companies.primary_contact_id`） |
| 联系人优先级规则 | ❌ 无（仅"非功能性邮箱"硬编码黑名单） | ✅ 租户配职位优先级序列（CEO > 总经理 > 老板 > ...） |
| 公司级中断（任一联系人回复 → 整公司停发） | ❌ 无 | ✅ 业务流 §4.2 Q17 必做 |
| 已回复识别 | ❌ 无 | ✅ UI 手动标（业务流 §4.5 Q20） |
| 多租户 | ❌ 单租户系统 | ✅ 多租户 + tenant 私有状态层 |
| 邮件 5 态状态机 | 简化版（draft / approved / sent / skipped） | 5 态：未开始 / 投递中 / 投递完成 / 已回复 / 已取消 |
| 客户库 UI（一公司一行） | ❌ 没有这种聚合 UI | ✅ 业务流 §3.5 Q13 必有 |

## 5. 对 V3 决策（§B 5 态聚合）的启示

### 5.1 §B 决策的真实背景

业务流 §4.6 末尾的"挂起，1.0 实施时需补一个 5 态聚合优先级表"——这个**聚合**是 ClientGet **新引入的能力**，aoqi 仓库没有：

- aoqi 仓库的 UI 大概率是"草稿列表 / 邮件列表"（每联系人一行）
- ClientGet 业务流要求"客户库列表"（每公司一行）+ 公司行有 5 态状态显示
- 聚合规则就是"同公司多个联系人的状态如何映射到公司行的单一状态"

### 5.2 §B 决策建议

既然 ClientGet 是要做**比 aoqi 更复杂的能力**，且**默认实现就是"一公司多人都发"**——那么：

- **聚合规则确实需要**（不是可挂起的细节，是客户库 UI 的必需品）
- **建议优先级**：`已取消 > 投递中 > 未开始 > 已回复 > 投递完成`
  - 已取消优先：让租户先看到"哪些公司被人停了"
  - 投递中优先于未开始：进展感
  - 已回复在投递完成之前：因为已回复触发公司级中断，状态比"还有人没收到"更重要
- 也可以选另一种顺序：`投递中 > 未开始 > 已回复 > 已取消 > 投递完成`（强调"业务进展"）

## 6. 对 V3 范围（§A）的启示

### 6.1 aoqi 仓库已经有的能力（V3 不是"从零开始"）

1. 网易外贸通采集（flow_01）
2. LLM 公司清洗 + 评分（flow_02，含 fallback 模型机制）
3. AI 个性化开发信生成（flow_03，含 16 个 PCB 子行业模板）
4. 工作时间 + 时区感知发送（flow_04，按收件人国家时区）
5. 预热档位（warmup_schedule.py，2026-02-25 起 20 天爬到 2500/天）
6. 多轮发送（round_number + linked_plan_id + interval_days）
7. EngageLab 集成（含限额检测、退避）

### 6.2 V3 需要新加的能力（aoqi 仓库没有）

1. **多租户**（核心架构差异，影响所有数据隔离）
2. **租户配置**：OpenRouter Key 自配 / SMTP 自配（aoqi 是 EngageLab 平台代发）
3. **客户库聚合 UI**（一公司一行 + 5 态聚合）
4. **主联系人 + 联系人优先级规则**
5. **公司级中断 + 已回复手动标记**
6. **租户私有状态层**（精选 / 拉黑 / 评分调整 / 备注 / 标签）
7. **3 数据源采集**（aoqi 只有外贸通；ClientGet 加腾道反推 + 励销云 stage 1）
8. **关键词归一 + 跨租户复用**（aoqi 没有"关键词"作为独立实体的概念，关键词嵌在 plan 里）
9. **平台运营 admin 端**（aoqi 是单租户，admin 直接是产品本身）

## 7. 给 V3 范围讨论的几个问题（你口述时可以参考）

1. V3 是否**复用 aoqi 仓库的代码**作为起点？还是当前 `backend/` 完全独立？
2. V3 邮件发送是否**保留 aoqi 的"按收件人国家时区 + 工作时间"逻辑**？业务流 §4.4 没明确说
3. V3 邮件是否**走 EngageLab 平台代发**还是**租户自配 SMTP**？业务流 §4.4 + UC-05 说"租户自配 SMTP"，但 aoqi 用 EngageLab 集中发——这是核心架构选择
4. V3 的"主联系人 + 联系人优先级"是否真做？aoqi 没做也能跑——这是 ClientGet 业务流新加的能力，做了才能做"3 选 1 策略"和聚合
5. V3 是否做 **多轮发送 + linked_plan_id 链式跟进**？aoqi 已实现，业务流 §4.2 Q16 有提"多步骤序列"

## 8. 工作区文件位置

- 本文件：`_control/inputs/reference-impl-aoqi.md`（参考材料，不是 V3 真源）
- 调研工具：`gh api` + Python 解码 base64
- 仓库源：[aoqi-ai/sysdev-ft-marketing](https://github.com/aoqi-ai/sysdev-ft-marketing)（私有）
