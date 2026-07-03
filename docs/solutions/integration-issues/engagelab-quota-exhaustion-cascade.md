---
title: EngageLab 额度耗尽引发发送 worker 级联空转（熔断+defer 解法）
date: 2026-07-03
category: integration-issues
module: email_sending
problem_type: integration_issue
component: background_job
symptoms:
  - "一夜之间 13,950 封排队邮件全部变为 failed，sent_at 与 engagelab_message_id 均为 NULL（实际一封未发出）"
  - "对应 13,913 个 sequence_enrollments 被误判永久失败而终止，联系人序列不会自动恢复"
  - "仪表盘「已发送/计费数」把 failed 计入，显示 22,679 而实发 8,729"
  - "worker 日志每小时约 2,500 条 send_failed，成功发送在撞额时刻（约 23:30 北京）后戛然而止"
root_cause: logic_error
resolution_type: code_fix
severity: critical
tags: [engagelab, quota, circuit-breaker, sending-worker, cascade, defer]
---

# EngageLab 额度耗尽引发发送 worker 级联空转（熔断+defer 解法）

## Problem

2026-07-02 晚 EngageLab 账户余额耗尽后，发送 worker 缺少熔断机制，整夜把队列剩余邮件逐封发送、逐封被拒、全部打成 `failed` 并终止序列；仪表盘口径又把这批从未发出的邮件计入「已发送/计费」。

## Symptoms

- 撞额后 `send_failed` 以稳定速率持续整夜（每封约 1.4 秒），成功发送在某一时刻后归零
- failed 邮件全部无 `sent_at`、无 `engagelab_message_id`——服务商从未接单
- `sequence_enrollments.send_attempt_count = 0` 却直接 `status='failed'`（被判永久失败，未走重试链）

## What Didn't Work

- **按 `status='sent'` 统计当日发送**：发出后状态会流转到 delivered/opened/bounced，`sent` 桶恒为 0——统计实际发出必须用 `sent_at IS NOT NULL`
- **期待重试链兜底**：重试链上限 3 次（15m/1h/4h），撑不到次日额度恢复；且配额错误被 `_classify_provider_error` 的「未知 4xx → 永久失败」默认分类直接判死
- **期待本地日配额挡住**：`mark_email_failed` 会释放 `domain_daily_usage.reserved_count`，本地计数永远差一点到顶、闸门永开，worker 持续取新邮件空转

## Solution

四件套（openspec 归档 change `fix-quota-exhaustion-cascade`，主 spec `sending-quota-circuit-breaker`）：

1. **错误分类三分**：额度耗尽（文本签名，见下）→ 临时 + 熔断；单次 429/`rate limit` → 走既有重试链；同域名 10 分钟 3 次限流才升级熔断；未知 4xx 默认从永久改为临时。**文本匹配仅对 4xx 生效**（5xx 含 "rate limit" 字样不得升级为整天熔断）。
2. **按域熔断**：worker 内存态 `domain_quota_paused`，当天停发、次日北京零点被动恢复（空闲轮询秒级）；重启丢态后首封错误即重建。全部熔断时走显式空转分支——**空列表绝不能流入 `min()`**。
3. **配额错误删行 defer**：不留 failed 记录——删除未发出的邮件行（`emails` 无入向外键；分区表 DELETE 带 `id + created_at` 双条件）、锁置 `released`、配额回退、enrollment 保持 `active` 推迟次日由 claim 重建（与「每次领取新建行」的取件模型同构，勿试图复用旧行——全库无任何代码消费 `emails.scheduled_at`）。
4. **连续 defer 上限**：同 enrollment 连续 3 次后降级走重试链且**不熔断域名**——防关键词误判的毒药邮件连续封域。

**EngageLab 额度耗尽实测签名**（生产日志校准）：HTTP 400 + 响应体 `{"code": 30877, "message": "mail failed to send. 552 {'code':-7,'message':'your account balance is not enough,please recharge soon',...}"}`。额度为**预付费余额型**（需充值恢复），非每日自动重置。排障取证注意：`send_failed` 结构化事件只有 `status_code` 没有错误文本；错误文本在 worker 每轮结果 JSON 的 `items[].reason`（`str(exc)` 含响应体，`_sanitize_provider_text` 截断至 1000 字符）。

## Why This Works

级联的根源是三个独立缺陷叠加：失败释放配额（闸门永开）× 配额错误判永久（序列被杀）× 口径含 failed（灾难被仪表盘掩饰为「已发送」）。熔断切断空转、defer 保住序列、口径修正让数字说真话；毒药上限与 4xx 守护防止新机制被误判反噬。

## Prevention

- **两个评审抓出的通用 P0 坑，写代码时默诵**：
  - worker/脚本把结果 dict 交给 `json.dumps` 时存在隐含「JSON 安全」不变量——新增返回字段带 `datetime` 会让进程崩溃循环（恰在最需要保护的时刻）；服务层返回 `isoformat()` 字符串 + 打印处 `default=str` 双保险
  - **Python 的 except 处理器内再抛异常不会路由给兄弟 handler**——降级/兜底调用必须自带 try/except，否则「兜底」本身成为击穿点
- 引入外部服务商时先问：配额/余额耗尽时它返回什么？该错误在我们的分类里落到哪个分支？消耗品额度必须有熔断而非重试
- 对「失败会释放资源计数」的循环，检查是否构成永动机（释放 → 有余量 → 再试 → 再失败 → 再释放）
- 仪表盘统计口径与服务商语义对齐：平台内部状态（如 failed=从未交付）不得混入服务商漏斗指标

## Related Issues

- openspec 归档：`openspec/changes/archive/2026-07-03-fix-quota-exhaustion-cascade/`（含 U6 冒烟记录）与 `2026-07-03-restore-quota-incident-enrollments/`（13,941 个序列的数据修复）
- 主 spec：`openspec/specs/sending-quota-circuit-breaker/spec.md`、`openspec/specs/quota-incident-data-repair/spec.md`
- 相邻经验：`docs/solutions/workflow-issues/sealos-victorialogs-log-search-pitfalls.md`（本次取证签名时踩的日志检索坑）
