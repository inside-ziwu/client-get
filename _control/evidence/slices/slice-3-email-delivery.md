# Slice 3 — 邮件投递监控（D-041 + EngageLab 鉴权修复 + 租户创建域名预热）

状态：**✅ 本地验证通过，已签字**

创建日期：2026-05-07

---

## 目标

| 变更项 | 规格来源 | 说明 |
|--------|----------|------|
| EngageLab 鉴权改为 HTTP Basic | D-EngageLab | `Basic base64(api_user:credential)`，旧 Bearer 作兜底 |
| 新增 2 个 config 字段 | D-EngageLab | `ENGAGELAB_API_USER` / `ENGAGELAB_CREDENTIAL`（`ENGAGELAB_SENDER` 已移除：from_email 取自 send_plans.sender_email，无需全局静态地址） |
| Migration 0020：emails 表补 6 个跟踪列 | D-041 | `first_opened_at` / `open_count` / `soft_bounce` / `invalid_email` / `report_spam` / `unsubscribed` |
| Migration 0021：email_events 补索引（merge point）| D-041 | `idx_email_events_type_time` + `idx_email_events_tenant_type`；合并 0027 + 0020 双头 |
| Webhook 扩展：写 D-041 字段 | D-041 | open/bounce/spam/unsubscribe 事件 → UPDATE emails 对应列 |
| Sending worker：open_tracking + error 记录 | D-041 | `open_tracking=True`，失败记 `error_code` + `error_message` |
| Admin 创建租户 Modal：域名 + 预热档位 | D-031 | 发件域名输入 + 1-6 档下拉，自动写 `domain_warmup_status` |
| 租户 EmailMonitor：6 张 D-041 统计卡 | D-041 | 发送量、送达率、独立打开率、软退信率、举报垃圾率、退订率 |
| schema.sql 同步 | — | 反映新列 + 新索引 |

---

## 迁移清单

| 版本号 | 文件 | 类型 | 说明 |
|--------|------|------|------|
| `20260507_0020` | `20260507_0020_emails_tracking_fields.py` | DDL | emails 表补 6 列 + 2 索引 |
| `20260507_0021` | `20260507_0021_email_events_index.py` | DDL + merge | email_events 补索引；down_revision = (0027, 0020) 合并双头 |

---

## 验证结果

```
$ alembic current
20260507_0021 (head) (mergepoint)
```

数据库单头，无分叉。

---

## 阻塞问题（已解决）

1. **多头错误**：0020 接 0029、0021 接 0020 导致 0021 与 0027 形成双头  
   → 修复：`0021.down_revision = ("20260507_0027", "20260507_0020")` 合并为单 merge point

2. **`emails.status` CHECK 不含 'sending'**：Worker 尝试写中间状态失败  
   → 修复：移除中间状态，继续用 `email_send_locks` 表做并发控制

3. **SendPlans/New D-033**：检查后发现新建页面已使用 `recipient_source: 'group'` 模式，无"3选1策略"UI  
   → 无需改动，D-033 已满足

---

## 修改文件清单

### 后端

| 文件 | 类型 | 说明 |
|------|------|------|
| `alembic/versions/20260507_0020_emails_tracking_fields.py` | 新建 | D-041 跟踪列迁移 |
| `alembic/versions/20260507_0021_email_events_index.py` | 新建 | 索引补充 + 双头合并 |
| `app/core/config.py` | 修改 | 新增 3 个 EngageLab 配置字段 |
| `app/integrations/engagelab.py` | 重写 | HTTP Basic 鉴权 + `open_tracking=True` |
| `app/services/webhook_service.py` | 重写 | 扩展 D-041 字段写入逻辑 |
| `app/workers/sending.py` | 修改 | 失败记 error_code/error_message |
| `app/services/tenant_messaging_service.py` | 修改 | email_stats 补 D-041 指标 + 计算率 |
| `app/services/tenant_service.py` | 修改 | create_tenant 写 domain_warmup_status（D-031） |
| `app/schemas/tenants.py` | 修改 | TenantCreateRequest 补 sender_domain + warmup_level |
| `03_database/schema.sql` | 修改 | emails 表补列 + 新索引 |

### 前端

| 文件 | 类型 | 说明 |
|------|------|------|
| `apps/admin/src/pages/Tenants/index.tsx` | 修改 | 创建租户 Modal 加域名输入 + 预热档位选择 |
| `packages/shared-types/src/api.ts` | 修改 | EmailStats 接口补 D-041 字段 |
| `apps/tenant/src/pages/EmailMonitor/index.tsx` | 修改 | 4 卡 → 6 卡 D-041 布局 |

---

## 备注

- `email_events` 表在 migration 0001 已建立，0021 仅补索引
- EngageLab 旧 `ENGAGELAB_API_KEY`（Bearer）保留向后兼容
- domain_warmup_status ON CONFLICT (tenant_id, domain) DO NOTHING，幂等安全
- sending worker open_tracking 已移入 EngageLabClient._build_request_body，不再由 worker 传参
