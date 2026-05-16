# 11 前端架构设计（后端对齐修复版）

本文件只定义后端需要满足的前端合同，不要求重新开发前端。

## 1. 双前端应用

| 应用 | URL | 后端 API |
|---|---|---|
| Admin App | `https://client-get-admin.vercel.app/` | `/admin/api/v1/*` |
| Tenant App | `https://client-get-tenant.vercel.app/` | `/t/{slug}/api/v1/*` |

Tenant 前端路由不带 slug。登录页收集 slug，登录成功后写入 JWT 与 auth store。

## 2. Admin 页面与后端资源

| 页面 | 后端资源 | 状态 |
|---|---|---|
| 数据源管理 | `data_sources`, `data_source_credentials` | 已补齐。 |
| 评分模板管理 | `platform_scoring_templates`, versions | 已补齐。 |
| 情报源管理 | `intelligence_sources` where tenant_id null | 已补齐。 |
| 邮件模板管理 | `platform_email_templates` | 已补齐。 |
| 域名预热规则 | `warmup_rules`, `warmup_rule_levels` | 已补齐。 |
| AI 配置 | `ai_models`, `ai_scene_defaults`, pricing fields | 已补齐。 |
| 租户管理 | `tenants`, `users`, `domain_warmup_status`, `balance_transactions` | 已补齐。 |

## 3. Tenant 页面与后端资源

| 页面 | 后端资源/API | 后端注意事项 |
|---|---|---|
| 登录 | `/auth/login` | body 包含 slug/email/password；JWT 含 tid/slug/roles。 |
| 首次向导 | `/auth/change-password`, `/keywords`, `/scoring-templates`, `/contact-rules` | 完成后 `needs_onboarding=false`。 |
| Dashboard | `/dashboard/overview`, `/dashboard/funnel`, `/notifications` | AI 余额 admin 可见；operator/viewer 只读 capability。 |
| 公司列表 | `/companies`, `/companies/{id}` | 返回 data_status 与 business_status。 |
| 优选客户 | `/prospects`, `/groups` | 群组成员按公司入组。 |
| 邮件模板 | `/email-templates`, `/email-templates/ai-generate` | AI 生成由 `/ai-capabilities` 控制。 |
| 发送计划 | `/sending-plans` 系列 | 创建向导可渐进保存；start 前锁定 recipients。 |
| 邮件监控 | `/emails/stats`, `/emails/stats/trend`, `/emails/ai-analysis` | 分区表双字段游标。 |
| 情报中心 | `/intelligence/articles` | 余额不足隐藏摘要。 |
| 设置 | keywords/scoring/contact-rules/billing/team/domains | admin only。 |

## 4. 前端需要的能力态

```json
{
  "data": {
    "features": [
      { "feature": "email_generate", "available": true, "reason": null },
      { "feature": "email_analysis", "available": false, "reason": "insufficient_balance" },
      { "feature": "intelligence_summary", "available": true, "reason": null }
    ],
    "self_recharge_available": false
  }
}
```

## 5. 前端 mock 到真实 API 的切换原则

1. API 返回字段使用 snake_case。
2. 时间统一 ISO 8601 UTC。
3. 列表统一 `{data, pagination}`。
4. 错误统一 `{error}`。
5. Tenant 前端所有 query key 需包含 slug，防止多租户缓存串数据。
6. 运行中发送计划详情建议 10 秒轮询。
