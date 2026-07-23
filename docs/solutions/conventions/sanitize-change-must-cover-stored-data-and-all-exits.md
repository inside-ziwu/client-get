---
title: 改 sanitize/转义行为必须同时盘点存量数据与全部发送出口
date: 2026-07-23
category: conventions
module: backend_messaging
problem_type: convention
component: sanitizer
severity: high
applies_when:
  - "修改 sanitize_* / 转义 / 编码行为（html_sanitizer.py 及同类）"
  - "新增任何把内容发出系统的出口（邮件、webhook 回执、导出）"
tags: [sanitize, escaping, legacy-data, send-path]
---

# 改 sanitize/转义行为必须同时盘点存量数据与全部发送出口

## Context

2026-07-23 修复「`&` 被发成 `&amp;`」（PR #90）当天，用户测试发送仍收到 `&amp;`。排查结论是修复正确但漏了两层：

1. **存量污染**：旧 sanitize 在模板**入库时**就把 `&` 转成 `&amp;` 存进库——修 sanitize 只保新写入，两个月存量（7 个现役模板）仍脏；
2. **出口不全**：`send_test_email` 是全后端唯一**不过 sanitize** 的发送出口（正式链路 claim 有 sanitize 动态修正存量，test-send 没有），脏数据经它原样发出（PR #92 补齐）。

## Guidance

1. 改转义/清洗行为时列三张清单：**写入点**（谁调 sanitize 入库）、**存量面**（历史数据是否带旧行为的痕迹，SQL 统计确认）、**出口**（grep 实际外发调用，如 `EngageLabClient().send_email` 的全部调用方），三张都处理完才算修完。
2. 存量处理二选一并写明依据：出口动态修正（全部出口都过新 sanitize 时可行）或一次性 UPDATE 清洗（生产写需用户逐次确认，本次 7 行 replace 先例见 2026-07-23 会话）。
3. 新增发送出口必须与 `claim_due_emails` 同序 sanitize（`sanitize_html` → text fallback → `sanitize_plain_text` → `sanitize_subject`），防回归见 `backend/tests/test_send_test_email_sanitize.py`。
4. 部署后验证不能只探活：**`/health` OK ≠ 新代码在跑**。用 `openapi.json` 的本次变更指纹（新增/删除的路由或参数）做无认证版本判定。

## Why This Matters

转义类 bug 无异常无报错，且入库转义会把污染固化成数据；只修函数不盘存量与出口，修复在用户可见面上等于没修——本次用户实测踩中的正是这个组合。

## Related

- PR #90（sanitize 修复）、PR #92（test-send 出口补齐）
- `docs/solutions/database-issues/select-duplicate-alias-shadowing-in-mappings.md`（同日另一类静默数据错误）
