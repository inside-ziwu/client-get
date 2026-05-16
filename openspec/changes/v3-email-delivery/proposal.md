# Proposal · v3-email-delivery

> **Wave 2（v3-data-foundation 已完成并归档后启动）** + Slice 5 是全 V3 收尾
> 关联：[`_control/v3/02-current-implementation-gap-audit.md`](../../../_control/v3/02-current-implementation-gap-audit.md) C7 + C9

## Why

V3 业务能力 R-3 = "完整邮件投递流程（配域名 → 创建邮件计划 → 真实发送 → 状态追踪 全链路）"。

当前真实状态：
- **emails 表 0 行** — 实际从未真发过任何邮件（D-018 from-scratch）
- **sending worker 代码 ready 但未部署** — backend/app/workers/sending/ 已实现 EngageLab 接入，但 Sealos 没跑
- **域名验证流程未实现** — domain_warmup_status 表在，但调 EngageLab Domain API + DNS 验证状态机缺失
- **预热档位限速逻辑未接入 sending worker** — daily_limit 字段在但不约束实发

业务后果：租户即使创建邮件计划也发不出去 → V3 上线即不可用。

## What Changes

### 引入

- **admin 创建租户 Modal +"发件域名 + 起始预热档位"两字段（D-031）**
  - Modal 提交时事务里同步建 domain_warmup_status 行
  - 起始预热档位 1-6 由运营选择
- **admin 域名 Tab 重做（D-002 / D-024 / D-028）**
  - "添加域名"调 EngageLab Domain API → 写 SPF / DKIM / DMARC 到 domain_warmup_status
  - "触发验证"按钮 + 状态轮询（pending → verifying → verified / failed）
  - DNS 记录"一键复制"clipboard 按钮
- **sending worker 部署 + 接入预热档位限速**
  - sending worker Sealos 部署
  - 实发前查 domain_warmup_status.daily_limit 限速
  - emails 表写入 + 状态回写（联系人级 4 态：未开始 / 投递中 / 投递完成 / 已取消）
  - 失败 error_code / error_message 落库
- **UC-25 邮件计划新建调 classify(position) 取联系人**
  - 依赖 v3-contact-classification 完成
  - 自动取 is_sendable=true 的所有联系人（不限每公司数量）
  - 多步骤序列：第 N 轮发未发过的其他联系人
- **EngageLab API_USER 配置 + 1 测试租户首发拨测**
- **Slice 5 Sealos E2E 全链路验收**

### 修改

- `admin/Tenants/index.tsx` Create Modal + Domain Tab（按 `mockups/admin-customers.html` 域名 Tab 设计）
- `tenant/SendPlans/Create` UC-25 移除目标策略 3 选 1 UI（D-033 已确认）
- emails 表写入逻辑（V3 期间 replied_at 字段保留但永远 NULL，D-034 推迟 UC-30）

### 移除

- ❌ 不做回复识别 IMAP / Webhook / 手动标已回复（V3 N-02 / D-034）
- ❌ 不做公司级中断（V3 N-03 / D-021）
- ❌ 不做模板 A/B 测试（V3 N-11）
- ❌ 不做租户自配 SMTP 凭证（V3 N-12 — 改用 EngageLab 集中通道）

### 新增（2026-05-06 D-041 撤销 N-08 / N-09）

- ✅ **开信追踪**（撤销原 N-08）：EngageLab 通道 `open_tracking=true`，emails 表加字段 `first_opened_at` / `open_count`
- ✅ **送达分级 / 退信记录**（撤销原 N-09）：EngageLab webhook 或 API 拉取回写软退信 / 无效邮箱 / 举报垃圾 / 退订；emails 表加字段 `soft_bounce` / `invalid_email` / `report_spam` / `unsubscribe`
- ✅ **6 项监控指标**：发送量 / 送达率 / 独立打开率 / 软退信 / 举报垃圾 / 退订（按原型 `tenant-email-monitor.html`）

## Non-Goals

- ❌ 不实现 KeywordMaster（→ v3-collection-pushback）
- ❌ 不实现 classify(position) 函数（→ v3-contact-classification；本 change 引用 API）
- ❌ 不实现 sending worker 容器化（已在 v3-data-foundation 完成）
- ❌ 不重写 tenant Companies 页面（→ v3-tenant-companies）

## Impact

| 维度 | 影响 |
|---|---|
| **破坏兼容** | 否 — Modal 字段增加；sending worker 行为变化但接口兼容 |
| **DB 改动** | 中（codex N-04 修订）— domain_warmup_status 已有；**D-041 新增**：emails 表加 6 字段（first_opened_at / open_count / soft_bounce / invalid_email / report_spam / unsubscribe）+ 新建 `email_events` 事件表（按 EngageLab 事件粒度记录所有回写）|
| **Worker** | 是 — sending worker 部署 + 限速逻辑接入 |
| **前端** | 大 — admin Create Modal + Domain Tab 重做；tenant SendPlans Create 简化 |
| **EngageLab** | 是 — API_USER 配置 + 1 测试域名 + 真实拨测 |
| **依赖** | `2026-05-09-v3-data-foundation` 已完成并归档（worker 部署）+ v3-contact-classification（classify 函数） |

## 关联

- **能力域**：C7 邮件投递端到端 + C9 EngageLab 真接入
- **覆盖 Slice**：Slice 3（真实邮件投递）+ Slice 5（Sealos E2E 收尾）
- **覆盖验收 ID**：V3-MAIL-001 ~ V3-MAIL-006、V3-DEPLOY-001、V3-WORKER-002（防重复发送）
- **决策追溯**：D-002（域名验证架构 C）/ D-013（预热档位）/ D-018（emails from-scratch）/ D-024（单端原则）/ D-028（DNS 一键复制）/ D-031（创建租户同步配域名）/ D-033（目标策略改）/ D-034（UC-30 推迟）/ **D-041（开信追踪 + 退信记录 V3 必做，撤销 N-08/N-09）**
