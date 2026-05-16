# V3 · 05 · PM Acceptance Report

> **状态**：占位模板（Slice 5 完成、E2E 全跑过后填）
> **责任**：用户填写并签字（AI 仅辅助整理证据）
> **Gate**：[Gate 9](../../AGENTS.md#6-门禁规则v3-工作流-10-gates) 阻止 OpenSpec archive 直到本文件签字

## 0. 元数据

- 版本：v0.0（占位）
- 验收日期：__待补__
- 用户签字：__未签字__
- 关联：
  - [`01-v3-acceptance-matrix.md`](01-v3-acceptance-matrix.md)
  - [`04-v3-e2e-test-plan.md`](04-v3-e2e-test-plan.md)

---

## 1. PM 验收表（来自 ChatGPT §13）

| Requirement ID | 验收项 | 测试环境 | 结果 | 证据 | 结论 |
| --- | --- | --- | --- | --- | --- |
| V3-AUTH-001 | 登录与租户隔离 | Sealos | __Pass/Fail__ | 截图/日志/DB | __Y/N__ |
| V3-COL-001 | 采集配置 | Sealos | __Pass/Fail__ | __证据__ | __Y/N__ |
| V3-COL-002 | 创建采集任务 | Sealos | __Pass/Fail__ | 截图/日志/DB | __Y/N__ |
| V3-COL-003 | Worker 执行真实采集 | Sealos | __Pass/Fail__ | Worker 日志 | __Y/N__ |
| V3-COL-004 | 采集结果结构化 | Sealos | __Pass/Fail__ | DB | __Y/N__ |
| V3-COL-005 | 采集结果入库 | Sealos | __Pass/Fail__ | DB / 页面 | __Y/N__ |
| V3-COL-006 | 采集结果去重 | Sealos | __Pass/Fail__ | DB 行计数 | __Y/N__ |
| V3-COL-007 | Tenant 隔离 | Sealos | __Pass/Fail__ | A/B 验证 | __Y/N__ |
| V3-MAIL-001 | 邮件账号配置 | Sealos | __Pass/Fail__ | 页面/API | __Y/N__ |
| V3-MAIL-002 | 邮件账号验证 | Sealos | __Pass/Fail__ | 拨测日志 | __Y/N__ |
| V3-MAIL-003 | 创建邮件发送任务 | Sealos | __Pass/Fail__ | 页面/DB | __Y/N__ |
| V3-MAIL-004 | 真实发送邮件 | Sealos | __Pass/Fail__ | 收件箱截图 | __Y/N__ |
| V3-MAIL-005 | 状态回写 | Sealos | __Pass/Fail__ | 页面/DB | __Y/N__ |
| V3-MAIL-006 | 失败记录 | Sealos | __Pass/Fail__ | 错误日志/DB | __Y/N__ |
| V3-WORKER-001 | 失败可重试 | Sealos | __Pass/Fail__ | 日志/状态 | __Y/N__ |
| V3-WORKER-002 | 防重复 | Sealos | __Pass/Fail__ | 日志 | __Y/N__ |
| V3-UI-001 | 前端状态展示 | Sealos | __Pass/Fail__ | 截图 | __Y/N__ |
| V3-DEPLOY-001 | 7 个应用正常 | Sealos | __Pass/Fail__ | 应用状态截图 | __Y/N__ |

## 2. 总体结论（三选一）

- [ ] **Go** — 可以上线（所有 P0 PASS）
- [ ] **No-Go** — 不能上线（至少 1 个 P0 FAIL，列出阻塞项）
- [ ] **Conditional Go** — 带已知问题上线（列出风险与补救方案）

### 阻塞项（如适用）

| ID | 状态 | 原因 | 补救方案 | 责任人 | 期限 |
| --- | --- | --- | --- | --- | --- |
| | | | | | |

## 3. 已知风险（Conditional Go 时填）

| 风险 | 影响范围 | 缓解措施 | 监控指标 |
| --- | --- | --- | --- |
| | | | |

## 4. 遗留事项（进入 V3.x 或 V4 的 backlog）

- `<TODO>`

## 5. 验收证据归档

> 所有截图、日志、DB 导出归档到 `docs/releases/2026-XX-XX-v3-sealos-release/evidences/`，本文件只引用路径。

签字行：

```
__________________________ (用户 / PM)   日期：__________
```
