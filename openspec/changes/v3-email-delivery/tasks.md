# Tasks · v3-email-delivery

> Wave 2 主链 — Slice 5 是 V3 全链路收尾
> 任务编号：`T-ED-XX`

## 0. 前置

- [x] T-ED-00 v3-data-foundation 完成并已归档（sending worker 部署到位）
- [ ] T-ED-01 v3-contact-classification 完成（classify(position) 函数可调用）
- [ ] T-ED-02 起草 design.md（域名验证状态机 + sending worker 限速逻辑）
- [ ] T-ED-03 用户审 design.md

## 1. Slice 3.1 — admin 创建租户 Modal 改造（C7-G1）

- [ ] T-ED-10 Create Modal 加"发件域名"字段（按 mockup `admin-customers.html`）
- [ ] T-ED-11 Create Modal 加"起始预热档位 1-6"下拉
- [ ] T-ED-12 后端 POST `/api/admin/tenants` 改：事务里同步建 `domain_warmup_status` 行
- [ ] T-ED-13 字段校验 + 错误处理
- [ ] T-ED-14 行业字段默认锁 PCB（D-040）

## 2. Slice 3.2 — admin 域名 Tab 重做（C7-G2~G4）

- [ ] T-ED-20 "添加域名"API 改：调 EngageLab Domain API（Architecture C: 平台运营配 DNS）
- [ ] T-ED-21 写入 SPF / DKIM / DMARC 到 domain_warmup_status
- [ ] T-ED-22 "触发验证"按钮 + API（poll EngageLab 验证状态）
- [ ] T-ED-23 状态机：pending → verifying → verified / failed
- [ ] T-ED-24 前端状态轮询 + 错误提示
- [ ] T-ED-25 DNS 记录展开行 + "一键复制"clipboard 按钮（D-028）
- [ ] T-ED-26 "调整预热档位"保留现有 PASS 实现

## 3. Slice 3.3 — sending worker 实跑（C7-G5~G9）

- [ ] T-ED-30 sending worker 部署到 Sealos（worker base class 接入）
- [ ] T-ED-31 EngageLab API_USER 配置（环境变量 / Sealos secret）
- [ ] T-ED-32 实发前查 `domain_warmup_status.daily_limit` 限速（每域名每日上限）
- [ ] T-ED-33 emails 表写入 + 4 态状态机（未开始 / 投递中 / 投递完成 / 已取消）
- [ ] T-ED-34 失败 error_code / error_message 落库
- [ ] T-ED-35 防重复发送（email_send_locks 幂等键）
- [ ] T-ED-36 邮件文案 + 发件人模板渲染（变量替换）
- [ ] T-ED-37 sending worker 单测 + 集成测试

## 4. Slice 3.4 — UC-25 邮件计划新建（C7-G7）

- [ ] T-ED-40 tenant SendPlans/Create 移除"目标策略 3 选 1"UI（D-033）
- [ ] T-ED-41 调 classify(position) 自动取 is_sendable=true 联系人
- [ ] T-ED-42 多步骤序列：第 N 轮发未发过的其他联系人
- [ ] T-ED-43 联系人级 4 态展示（按 mockup `tenant-send-plans-detail.html`）

## 5. Slice 3.5 — EmailMonitor 监控 + D-041 投递追踪（C7 收尾）

### 5.1 数据库字段（D-041）

- [ ] T-ED-50A alembic 迁移：emails 表加 `first_opened_at timestamptz` / `open_count int default 0`（开信追踪）
- [ ] T-ED-50B alembic 迁移：emails 表加 `soft_bounce bool` / `invalid_email bool` / `report_spam bool` / `unsubscribe bool`（送达分级）
- [ ] T-ED-50C alembic 迁移：建 `email_events` 表（按事件级粒度记录所有 EngageLab 回写）

### 5.2 EngageLab 配置 + Webhook 接入（D-041）

- [ ] T-ED-50D sending worker 调 EngageLab 时设置 `open_tracking=true`（开信追踪）
- [ ] T-ED-50E EngageLab webhook 端点 `/api/webhook/engagelab`（接收 opens / bounces / spam / unsubscribe 事件）
- [ ] T-ED-50F webhook 签名校验（防伪）
- [ ] T-ED-50G webhook 事件 → email_events 表 + emails 表字段更新
- [ ] T-ED-50H 兜底：定时任务从 EngageLab API 拉取近 24h 状态（容错 webhook 丢失）

### 5.3 监控 UI（按原型）

- [ ] T-ED-51 tenant EmailMonitor 接 6 指标（按 mockup `tenant-email-monitor.html`）：发送量 / 送达率 / 独立打开率 / 软退信 / 举报垃圾 / 退订
- [ ] T-ED-52 多系列柱图数据接入（sent / delivered / opens）
- [ ] T-ED-53 详情时间轴弹窗（发送 / 送达 / 首次打开 / 退信 / 退订）
- [ ] T-ED-54 退信原因展示（软退信 / 无效邮箱 / 举报垃圾 不同 tag 颜色）

## 6. Slice 5 — Sealos E2E 收尾（C9-G1~G5）

- [ ] T-ED-60 EngageLab 账号 + 域名 + API_USER 生产配置
- [ ] T-ED-61 1 个真实租户域名 DNS 配置（线下，由运营完成）
- [ ] T-ED-62 域名验证 verified ✅
- [ ] T-ED-63 1 个真实关键词全链路：配 → 反推 → 客户库 → 邮件计划 → 真实发件
- [ ] T-ED-64 测试收件箱真实收到邮件 ✅
- [ ] T-ED-65 emails.status = delivered 验证
- [ ] T-ED-66 失败/重试场景验证（V3-WORKER-001/002）
- [ ] T-ED-67 输出 [`05-v3-pm-acceptance-report.md`](../../../_control/v3/05-v3-pm-acceptance-report.md)
- [ ] T-ED-68 输出 [`06-v3-release-manifest.md`](../../../_control/v3/06-v3-release-manifest.md)
- [ ] T-ED-69 输出 `docs/releases/2026-XX-XX-v3-sealos-release.md`

## 7. Review

- [ ] T-ED-90 CE review → `_control/reviews/ce-review-v3-email-delivery.md`
- [ ] T-ED-91 gstack eng review → `_control/reviews/gstack-eng-review-v3-email-delivery.md`
- [ ] T-ED-92 Codex code review → `_control/reviews/codex-code-review-v3-email-delivery.md`
- [ ] T-ED-93 修复 Blocker / High Risk

## 8. 验收

- [ ] T-ED-99-A V3-MAIL-001 通过：发件邮箱配置成功落库
- [ ] T-ED-99-B V3-MAIL-002 通过：拨测发件成功
- [ ] T-ED-99-C V3-MAIL-003 通过：邮件任务入库
- [ ] T-ED-99-D V3-MAIL-004 通过：worker pickup → EngageLab → 收件箱真收到
- [ ] T-ED-99-E V3-MAIL-005 通过：emails.status 状态回写正确
- [ ] T-ED-99-F V3-MAIL-006 通过：失败 error_code / error_message 有值
- [ ] T-ED-99-G V3-DEPLOY-001 通过：Sealos 全链路打通
