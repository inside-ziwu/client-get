# V3 · 04 · E2E Test Plan

> **状态**：占位模板（每个 Slice 完成后增补对应场景；最终 Sealos 上跑通全部）
> **责任**：AI 起草 → 用户审 → Slice 5 时实跑
> **Gate**：本文件全部场景 PASS 前，[Gate 7](../../AGENTS.md#6-门禁规则v3-工作流-10-gates) 阻止"V3 完成"声明
> **关联**：[`01-v3-acceptance-matrix.md`](01-v3-acceptance-matrix.md)、[`03-v3-delivery-plan.md`](03-v3-delivery-plan.md)

## 0. 元数据

- 版本：v0.0（占位）
- 起草日期：__待补__
- 测试环境：本地 → Sealos（最终）

---

## 1. E2E 场景表

> 每个场景对应至少 1 个 Requirement ID，必须可在 Sealos 真实环境复现。

| # | 场景 | 关联 ID | 前置条件 | 步骤 | 期望结果 | 测试租户 | 真实邮箱/采集源 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E2E-1 | 租户登录 + 隔离 | V3-AUTH-001 | 租户 A、B 已建 | 1) A 登录 2) B 登录 3) A 看不到 B 数据 | A 不可见 B | A、B（见 [`inputs/test-data/`](../inputs/test-data/)） | — | __PENDING__ |
| E2E-2 | 真实采集闭环 | V3-COL-001 ~ 005 | 采集源凭证已配 | 1) Admin 配置数据源 2) 创建关键词任务 3) Worker 处理 4) 看入库 | 至少 1 家公司入库 | A | 真实关键词 + 外贸通账号 | __PENDING__ |
| E2E-3 | 采集去重 | V3-COL-006 | E2E-2 已跑过 1 次 | 重复运行同关键词 | 不产生重复行 | A | 同 E2E-2 | __PENDING__ |
| E2E-4 | 跨租户隔离 | V3-COL-007 | A、B 都创建采集任务 | 1) A 创建 2) B 创建 3) 看 A 是否看到 B 的结果 | A 看不到 B 的 | A、B | 同上 | __PENDING__ |
| E2E-5 | 邮件账号配置 + 验证 | V3-MAIL-001、002 | 真实发件账号 | 配置 + 拨测 | 拨测成功 | A | 真实发件邮箱 | __PENDING__ |
| E2E-6 | 真实邮件投递 + 状态回写 | V3-MAIL-003 ~ 005 | E2E-5 已通过 | 1) 创建任务 2) Worker 发送 3) 收件箱收到 4) DB 看 sent | 收到邮件 + sent | A | 真实收件箱 | __PENDING__ |
| E2E-7 | 邮件失败记录 | V3-MAIL-006 | 故意配错收件人 | Worker 处理 → 看 error_* | error_code 与 error_message 有值 | A | 错误邮箱 | __PENDING__ |
| E2E-8 | 任务重试 | V3-WORKER-001 | E2E-7 失败任务 | 触发重试 | 看到重试记录 | A | 同上 | __PENDING__ |
| E2E-9 | 防重复采集/发送 | V3-WORKER-002 | 任务已存在 | 双击触发 | 1 次执行 | A | 任意 | __PENDING__ |
| E2E-10 | 前端状态展示 | V3-UI-001 | E2E-2、E2E-6 跑过 | 打开任务列表页 | 状态正确显示 | A | — | __PENDING__ |
| E2E-11 | Worker 重启不丢任务 | V3-WORKER-001 | 有 pending 任务 | 重启 worker | 任务继续被 pickup | A | 任意 | __PENDING__ |
| E2E-12 | Sealos 全链路 | V3-DEPLOY-001 | Sealos 部署完成 | E2E-1 ~ E2E-11 在 Sealos 上重跑 | 全部 PASS | A、B | 全套 | __PENDING__ |

## 2. 测试数据

> 全部从 [`_control/inputs/test-data/test-materials.md`](../inputs/test-data/test-materials.md) 引用，**不在本文件粘贴敏感值**。

- 测试租户 A：__引用 inputs/test-data__
- 测试租户 B：__引用__
- 测试发件邮箱：__引用__
- 测试收件邮箱：__引用__
- 真实采集源：__引用__
- 失败场景配置：__引用__

## 3. 状态枚举

- `PENDING` 未跑
- `PASS` 已跑通且证据齐全
- `FAIL` 跑了但失败
- `BLOCKED` 因前置场景未通过而无法跑

## 4. 证据清单（每个 PASS 场景必填）

> 不能只写"通过"。必须给：

- 截图（前端 UI、Sealos 控制台）
- 日志路径（worker stdout / API access log）
- DB 行 ID（关键表 row id 或时间戳）
- 邮件原文（E2E-6 需附收件箱截图或邮件 source）

## 5. PM Review Checklist

- [ ] 全部 E2E 场景 PASS 或 BLOCKED 已说明原因
- [ ] 每个 PASS 场景有完整证据
- [ ] Sealos 上实跑过 E2E-12
- [ ] 与 [`05-v3-pm-acceptance-report.md`](05-v3-pm-acceptance-report.md) 的结论一致

签字行：

```
__________________________ (用户)   日期：__________
```
