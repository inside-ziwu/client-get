## 概述

本变更主要是前端页面重做 + 少量后端 API 新增 + 一个 migration。后端已有的 email template CRUD 能力基本不变，核心工作量在 Tenant 前端。

变更范围：
1. **数据库**：`email_templates` 表加 `body_design` 列
2. **后端**：TenantMessagingService 新增浏览/复制平台模板方法；更新现有 CRUD 支持 body_design；废弃 Admin 同步接口
3. **共享包**：GrapesJS 编辑器提取到 `@shared/ui`；tenant API 层新增方法和类型
4. **前端**：Tenant 模板页面全面重写；Admin 移除同步按钮

---

## 数据库变更

### email_templates 表新增 body_design 列

```sql
ALTER TABLE email_templates ADD COLUMN body_design jsonb;
```

- 类型：`jsonb`，可为 NULL（纯 HTML 编辑的模板无此字段）
- 无默认值，无索引需求
- `platform_email_templates` 表已有 `body_design` 列（迁移 `20260423_0006` 已添加），本次仅补齐 `email_templates`

**Alembic 迁移文件**：`backend/alembic/versions/20260522_xxxx_email_template_body_design.py`

---

## 后端 API 变更

### 新增接口

#### 1. GET /t/{slug}/api/v1/platform-templates

浏览平台模板库。按当前租户的 industry 筛选 `platform_email_templates`。

**权限**：`get_current_tenant_user`（任何已认证租户用户）

**逻辑**：
1. 从 `tenants` 表查询当前 `tenant_id` 对应的 `industry`
2. 查询 `platform_email_templates WHERE industry = :industry AND is_active = true ORDER BY updated_at DESC`
3. 返回列表

**响应体**：
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": "uuid",
        "name": "PCB 首次触达模板",
        "description": "适用于 PCB 行业的首次客户触达",
        "category": "cold_outreach",
        "subject": "Competitive PCB Solutions – {{company_name}}",
        "body_html": "<p>...</p>",
        "variables": [{"name": "company_name", "label": "公司名称"}],
        "created_at": "2026-03-01T00:00:00+00:00",
        "updated_at": "2026-03-01T00:00:00+00:00"
      }
    ],
    "total": 2
  }
}
```

**注意**：路由路径使用 `/platform-templates` 而非 `/email-templates` 下的子路径，避免和现有 email-templates CRUD 路由冲突。静态路由 `/platform-templates` 无动态路由冲突问题。

#### 2. POST /t/{slug}/api/v1/platform-templates/{template_id}/copy

将平台模板复制到租户的模板列表。

**权限**：`require_tenant_roles("admin", "operator")`

**逻辑**：
1. 从 `tenants` 表查询当前租户的 `industry`
2. 从 `platform_email_templates` 查询目标模板（验证 `is_active = true AND industry = :industry`，确保租户只能复制本行业模板）
3. 调用现有 `create_email_template`，payload 从平台模板复制所有字段：
   - `source_type = 'platform_copy'`
   - `platform_template_id` = 平台模板 ID
   - `body_design` = 平台模板的 body_design
   - `name`、`category`、`subject`、`body_html`、`body_text`、`variables` 全部复制
3. 返回新创建的租户模板

**响应体**：与现有 `create_email_template` 一致

### 现有接口变更

#### create_email_template / update_email_template

- INSERT SQL 增加 `body_design` 字段
- UPDATE SQL：`body_design` **不用** COALESCE，直接赋值（支持前端传 `null` 清空设计数据，用于切换编辑模式场景）
- `_serialize_template` 增加 `body_design` 字段返回
- `_sanitize_template_content`：**不跳过清洗**，改为扩展 `html_sanitizer.py` 白名单加入 table/img/style/td/tr/th/thead/tbody/div/span/h1-h6/center/hr 等邮件标签及 style/class/width/height/src/alt/align 等属性，始终执行 sanitize_html（安全审查修正：绕过清洗→扩展白名单）
- `get_email_template` SELECT 增加 `body_design`
- `list_email_templates` SELECT **不增加** `body_design`（列表页不需要设计数据，避免响应体膨胀）

#### preview_email_template

- 调用 `get_email_template`，无需独立修改 SELECT

### 废弃接口

#### POST /admin/api/v1/email-templates/{template_id}/sync

- 从 `backend/app/api/admin/config.py` 移除路由
- 从 `backend/app/services/admin_config_service.py` 移除 `sync_platform_email_template` 方法
- 保留 `platform_email_templates` 的其他 CRUD 不变

### 补充修复

#### tenant_service._copy_platform_email_templates

创建租户时自动复制平台模板的方法（`backend/app/services/tenant_service.py:349`）也需补齐 `body_design` 字段：
- SELECT 增加 `body_design`
- INSERT 增加 `body_design`

---

## 共享包变更

### @shared/ui — GrapesJS 编辑器组件

**提取方式**：将 `frontend/apps/admin/src/components/grapes-email-editor.tsx` 移入共享包

**目标路径**：`frontend/packages/shared-ui/src/components/grapes-email-editor.tsx`

**变更清单**：
- `frontend/packages/shared-ui/package.json`：新增依赖 `grapesjs@^0.22.15`、`grapesjs-preset-newsletter@^1.0.2`
- `frontend/packages/shared-ui/src/index.ts`：导出 `GrapesEmailEditor` 和 `GrapesEmailEditorHandle`
- `frontend/apps/admin/src/components/grapes-email-editor.tsx`：删除，改为从 `@shared/ui` 导入
- `frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx`：更新导入路径
- `frontend/apps/admin/package.json`：移除 `grapesjs` 和 `grapesjs-preset-newsletter` 直接依赖（通过 `@shared/ui` 间接依赖）

**组件接口不变**：
```typescript
interface GrapesEmailEditorHandle {
  getHtml: () => string;
  getDesign: () => unknown;
}

// Props: html?: string, design?: unknown, onReady?: () => void
```

### @shared/api — Tenant API 扩展

**文件**：`frontend/packages/shared-api/src/tenant/email-templates.ts`

**变更**：

1. `EmailTemplate` 接口增加 `body_design?: unknown` 字段

2. 新增 `PlatformTemplate` 接口：
```typescript
export interface PlatformTemplate {
  id: string;
  name: string;
  description?: string;
  category: string;
  subject: string;
  body_html: string;
  body_design?: unknown;
  variables: Array<{ name: string; label: string }>;
  created_at: string;
  updated_at: string;
}
```

3. `emailTemplatesApi` 新增方法：
```typescript
platformList: () =>
  client.get<PaginatedResponse<PlatformTemplate>>('/api/v1/platform-templates'),
platformCopy: (id: string) =>
  client.post<ApiResponse<EmailTemplate>>(`/api/v1/platform-templates/${id}/copy`),
```

**Admin API 变更**：`frontend/packages/shared-api/src/admin/email-templates.ts`
- 移除 `sync` 方法和 `SyncEmailTemplateResult` 类型

---

## 前端 Tenant 页面

### 页面结构

**文件**：`frontend/apps/tenant/src/app/(dashboard)/templates/page.tsx`（全面重写）

**布局**：
```
PageHeader（标题 + 「新建模板」按钮 + 「AI 生成」按钮）
├── Tabs
│   ├── Tab「平台模板库」(N)
│   │   └── DataTable（名称 / 分类 / 主题 / 更新时间 / 操作[预览|复制]）
│   └── Tab「我的模板」(N)
│       └── DataTable（名称 / 分类 / 主题 / 来源Badge / 更新时间 / 操作[预览|编辑|复制|删除]）
├── Sheet（编辑器 Drawer，760px 宽）
│   ├── 表单：名称、分类（Select）、主题、变量 chips
│   └── Tabs：可视化编辑器 | HTML 源码 | 纯文本
├── Dialog（预览 Modal，860px 宽）
│   └── iframe srcdoc 渲染变量替换后的 HTML（sandbox="allow-same-origin" 禁止脚本执行）
└── Dialog（AI 生成 Modal）
    └── 表单：名称、分类、公司描述、生成要求、主题偏好
```

### 数据流

**平台模板库 Tab**：
- `useQuery(['tenant', 'platform-templates'])` → `tenantApi.emailTemplates.platformList()`
- 「复制」按钮 → `useMutation` → `tenantApi.emailTemplates.platformCopy(id)` → invalidate `['tenant', 'templates']` → 切换到「我的模板」Tab + toast

**我的模板 Tab**：
- `useQuery(['tenant', 'templates'])` → `tenantApi.emailTemplates.list()`
- 「编辑」按钮 → `tenantApi.emailTemplates.detail(id)` → 打开 Drawer 填充表单
- 保存 → `tenantApi.emailTemplates.update(id, data)` 或 `tenantApi.emailTemplates.create(data)`

**AI 生成流程**：
- AI Modal 表单提交 → `tenantApi.emailTemplates.aiGenerate(data)` → 关闭 Modal → 用返回的 subject/body_html/variables 打开 Drawer 编辑器 → 用户微调后保存

**Drawer 编辑器状态管理**：
- `mode: 'visual' | 'html' | 'text'` 控制编辑器 Tab
- `editorRef: useRef<GrapesEmailEditorHandle>` 引用 GrapesJS 实例
- 保存时：`mode === 'visual'` 则从 `editorRef.current.getHtml()` / `getDesign()` 取值

### 变量 chips

从 mock 中的 VARIABLES 定义，前端硬编码可用变量列表：
- `contact_name`、`contact_email`、`contact_title`、`company_name`
- `sender_name`、`sender_company`、`sender_title`、`sender_email`
- `product_name`、`website`、`unsubscribe_link`

点击 chip 复制 `{{变量名}}` 到剪贴板。

### 分类

前端硬编码 4 个分类选项（与 mock 一致）：
- `cold_outreach`（首次触达）
- `follow_up`（跟进）
- `promotion`（推广）
- `festival`（节日问候）

后端 `category` 字段为 `varchar(50)`，不做枚举约束。

### 来源标记

「我的模板」Tab 中，通过 `source_type` 字段区分来源：
- `custom`：无特殊标记
- `platform_copy`：显示 Badge「平台」

---

## Admin 端变更

**文件**：`frontend/apps/admin/src/app/(dashboard)/email-templates/client-page.tsx`

- 移除 `syncing` 状态和 `syncTemplate` 方法
- 移除模板列表中的同步按钮（`<RefreshCw>` 图标按钮）
- 更新 GrapesJS 编辑器导入路径：`import { GrapesEmailEditor } from '@shared/ui'`

---

## 依赖顺序

```
U1 数据库迁移（body_design 列）
  ↓
U2 后端：更新现有 CRUD 支持 body_design
  ↓
U3 后端：新增平台模板浏览/复制 API
  ↓
U4 共享包：GrapesJS 组件提取到 @shared/ui
  ↓
U5 共享包：tenant API 层扩展
  ↓
U6 前端：Tenant 模板页面重写
  ↓
U7 清理：Admin 废弃同步功能
```
