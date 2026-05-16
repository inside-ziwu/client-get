# API 参考文档

> 基础URL: `http://localhost:8000`
> 认证方式: JWT Bearer Token（`Authorization: Bearer <token>`）
> 公开路径: `/`, `/health`, `/docs`, `/redoc`, `/openapi.json`, `/api/auth/*`

---

## 1. 认证 (`/api/auth`)

### POST `/api/auth/login`
登录获取 JWT Token。

**请求体**:
```json
{ "username": "admin", "password": "admin123" }
```

**响应**:
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

**实现细节**: 密码使用 bcrypt 验证，Token 有效期 24 小时（HS256），凭证存储在 `system_config` 表。

---

## 2. 计划管理 (`/api/plans`) - 最核心模块

### GET `/api/plans`
分页获取计划列表。

| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认1 |
| page_size | int | 每页数量，默认20 |
| status | string | 按状态筛选 |

### GET `/api/plans/{plan_id}`
获取单个计划详情。

### GET `/api/plans/{plan_id}/progress`
获取计划流水线进度。返回 collect/clean/draft/send 四阶段的完成数和百分比。

**响应结构**:
```json
{
  "collect": { "total": 100, "done": 80, "pct": 80.0 },
  "clean": { "total": 80, "done": 60, "pct": 75.0 },
  "draft": { "total": 40, "done": 30, "pct": 75.0 },
  "send": { "total": 20, "done": 15, "pct": 75.0 }
}
```

### GET `/api/plans/{plan_id}/preview`
预览匹配计划筛选条件的联系人。

### GET `/api/plans/{plan_id}/sending-preview`
预览发送排期（时区感知，按工作日/工作时间排布）。

### POST `/api/plans`
创建计划。

**请求体**:
```json
{
  "plan_name": "US PCB Campaign",
  "country": "US",
  "industry": "PCB",
  "target_collect": 1000,
  "target_clean": 500,
  "target_send": 200,
  "priority": 5,
  "round_number": 1
}
```

### PUT `/api/plans/{plan_id}`
更新计划字段。

### POST `/api/plans/{plan_id}/transition`
状态流转。

**请求体**: `{ "target_status": "approved" }`

### POST `/api/plans/{plan_id}/approve`
审批计划（draft → approved）。

### POST `/api/plans/{plan_id}/approve-drafts`
批量审批计划下所有草稿，自动触发发送 Flow。

### POST `/api/plans/{plan_id}/reject`
拒绝计划。

### POST `/api/plans/{plan_id}/assign-companies`
分配未清洗公司到计划。

**请求体**: `{ "country": "US", "limit": 100 }`

### POST `/api/plans/{plan_id}/select-companies`
选择/跳过 A/B 级公司（设置 `email_priority`）。

**请求体**: `{ "company_ids": [1,2,3], "action": "selected" }`

### POST `/api/plans/{plan_id}/trigger/{flow_name}`
手动触发指定 Flow（collect/clean/generate/send），后台线程执行。

### DELETE `/api/plans/{plan_id}`
删除计划（限制：状态不能是 done，且无关联的 follow-up 计划）。

---

## 3. 仪表盘 (`/api/dashboard`)

### GET `/api/dashboard/overview`
全量仪表盘数据：漏斗转化、分布趋势。

### GET `/api/dashboard/stats`
管道计数、昨日 Flow 运行、审批统计。

### GET `/api/dashboard/engagelab-stats`
EngageLab 邮件发送/追踪统计（外部 API 调用）。

| 参数 | 类型 | 说明 |
|------|------|------|
| start_date | string | 开始日期 YYYY-MM-DD |
| end_date | string | 结束日期 YYYY-MM-DD |

### GET `/api/dashboard/llm-balance`
OpenRouter LLM API 余额查询。

### GET `/api/dashboard/daily-quota`
每日邮件发送配额（限额/已用/剩余）。

### GET `/api/dashboard/plan-overview`
按计划的统计概览。

| 参数 | 类型 | 说明 |
|------|------|------|
| plan_id | int | 可选，不传返回聚合数据 |

---

## 4. 关键词 (`/api/keywords`)

### GET `/api/keywords`
分页列表，支持搜索和计划筛选。

### GET `/api/keywords/{keyword_id}`
详情。

### POST `/api/keywords`
创建关键词（含重复检查）。

**请求体**: `{ "keyword": "PCB manufacturer", "country": ["US","DE"], "daily_limit": 10, "plan_id": 1 }`

### PUT `/api/keywords/{keyword_id}`
更新。

### DELETE `/api/keywords/{keyword_id}`
删除。

---

## 5. 公司 (`/api/companies`)

### GET `/api/companies`
已分析公司列表（分页+多条件筛选）。

| 参数 | 类型 | 说明 |
|------|------|------|
| country | string | 国家 |
| grade | string | A/B/X 等级 |
| plan_id | int | 计划ID |
| sub_industry | string | 细分行业 |
| product_tags | string | 产品标签（JSONB包含查询） |
| search | string | 公司名模糊搜索 |

### GET `/api/companies/{company_id}`
公司详情。

---

## 6. 联系人 (`/api/contacts`)

### GET `/api/contacts`
全部联系人分页列表。

### GET `/api/contacts/buyer`
清洗后的买家联系人（带优先级分类 A/B/X）。

### GET `/api/contacts/buyer/filters`
买家联系人筛选器下拉选项。

### GET `/api/contacts/{contact_id}`
联系人详情。

---

## 7. 邮件草稿 (`/api/drafts`)

### GET `/api/drafts`
草稿列表（分页，支持按计划/状态筛选）。

### GET `/api/drafts/{draft_id}`
草稿详情。

### POST `/api/drafts/{draft_id}/approve`
审批单条草稿。

**请求体**: `{ "approved_by": "admin" }`

### POST `/api/drafts/{draft_id}/rewrite`
AI 重写草稿正文（DeepSeek via OpenRouter）。

**请求体**: `{ "advice": "更加突出PCB定制能力", "operator": "admin" }`

### GET `/api/drafts/{draft_id}/rewrite-history`
重写审计日志。

---

## 8. 邮件模板 (`/api/templates`)

### GET `/api/templates`
模板列表（支持按轮次/语言/国家/行业筛选）。

### GET `/api/templates/{template_id}`
模板详情。

### GET `/api/templates/{template_id}/preview`
渲染模板预览（用示例变量替换）。

### POST `/api/templates`
创建模板。

**请求体**:
```json
{
  "name": "PCB First Contact EN",
  "subject_template": "Custom PCB Solutions for {company_name}",
  "body_template": "Dear {contact_name}, ...",
  "round_number": 1,
  "language": "en",
  "country": "US",
  "industry": "PCB"
}
```

### PUT `/api/templates/{template_id}`
更新。

### DELETE `/api/templates/{template_id}`
删除。

---

## 9. 清洗规则 (`/api/product-config`)

### GET `/api/product-config`
所有产品行业配置（按 sort_order 排序）。

### POST `/api/product-config`
创建配置。

### PUT `/api/product-config/{config_id}`
更新。

### DELETE `/api/product-config/{config_id}`
删除。

### POST `/api/product-config/reorder`
批量排序。

**请求体**: `{ "ids": [3, 1, 2] }`

### GET `/api/product-config/scoring-template`
获取启用的规则，格式化为 LLM Prompt 模板。

---

## 10. 任务管理 (`/api`)

### GET `/api/task-runs`
Flow 运行记录列表。

| 参数 | 类型 | 说明 |
|------|------|------|
| flow_id | string | 筛选特定Flow |
| status | string | running/completed/failed |

### GET `/api/task-runs/latest`
每个 Flow 的最近一次运行。

### GET `/api/scheduled-tasks`
调度任务列表。

### PUT `/api/scheduled-tasks/{flow_id}`
更新调度配置。

### POST `/api/task-runs/{run_id}/stop`
取消运行中的任务。

### POST `/api/task-runs/trigger/{flow_id}`
手动触发 Flow。

---

## 11. 原始公司数据 (`/api/company-assets`)

### GET `/api/company-assets/stats`
聚合统计：总量、按国家分布、按来源分布。

### GET `/api/company-assets/filters`
筛选器选项。

### GET `/api/company-assets`
原始采集公司列表。

---

## 12. 健康检查

### GET `/`
服务状态。

### GET `/health`
数据库连通性检查。

### GET `/metrics`
Prometheus 指标端点。

---

## 13. 产品化标注

| 现状 | 产品化需求 |
|------|-----------|
| 单用户 JWT | 多用户注册/登录 + OAuth |
| 无权限控制 | RBAC（管理员/操作员/只读） |
| 无分页标准化 | 统一分页响应格式 |
| 错误码不统一 | 标准化错误响应结构 |
| 无 API 版本 | URL 前缀 `/api/v1/` |
| 无速率限制 | 按租户限流 |
| CORS `allow_origins=["*"]` | 收紧为白名单域名 |
