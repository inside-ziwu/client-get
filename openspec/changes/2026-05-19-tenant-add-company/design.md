## Context

Tenant 公司列表页（`companies/page.tsx`）已具备列表展示、筛选、批量操作、公司详情 Sheet 等功能，但缺少手动新增公司的入口。

现有代码资产：
- 后端 `TenantOpsService.create_company`（`tenant_ops_service.py:116-237`）已可创建公司，但 INSERT 只写 7 个字段
- 后端 `_ensure_contact_from_payload`（`tenant_ops_service.py:990-1072`）已支持联系人写入（name, email, position）
- 前端 API 客户端 `tenantApi.companies.create(data)` 已就绪（`shared-api/src/tenant/companies.ts:88-89`），payload 类型为 `Record<string, unknown>`
- 页面已使用 `Sheet`（SheetContent）作为详情 Drawer，组件已导入
- `countryZh()` 国家翻译、`CompanyFilters` 中的国家列表已可复用

## Goals / Non-Goals

**Goals:**
- 公司列表页新增「新增公司」按钮，点击后右侧 Sheet 展开表单
- 表单字段对齐 admin 端可填写字段（12 个基本信息 + 联系人 + 备注）
- 后端 create_company INSERT 扩展 5 个字段（phone, employee_size, founded_year, full_address, description）

**Non-Goals:**
- 不做公司编辑功能
- 不改数据库 schema（5 个字段已存在于 `waimaotong_clean_companies`）
- 不做批量导入
- 不改 admin 端

## Decisions

### D1: Sheet 布局 — 分组表单

```
┌─ Sheet (w-[660px]) ──────────────────────────────────────┐
│  SheetTitle: 新增公司                                     │
│                                                           │
│  ┌─ 基本信息 ──────────────────────────────────────────┐  │
│  │  公司名称*          [________________]               │  │
│  │  英文名称           [________________]               │  │
│  │  国家              [▼ Select________]               │  │
│  │  域名              [________________]               │  │
│  │  网站              [________________]               │  │
│  │  电话              [________________]               │  │
│  │  行业              [________________]               │  │
│  │  员工规模           [▼ Select________]               │  │
│  │  成立年份           [________________]               │  │
│  │  地址              [________________]               │  │
│  │  公司简介           [textarea_________]               │  │
│  │  产品标签           [tag input________]               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─ 联系人（可选）────────────────────────────────────┐  │
│  │  ┌ #1 ─────────────────────────────────────────┐   │  │
│  │  │ 姓名 [______]  邮箱 [______]  职位 [______] │   │  │
│  │  │                                     [删除]  │   │  │
│  │  └─────────────────────────────────────────────┘   │  │
│  │                              [+ 添加联系人]         │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─ 备注 ──────────────────────────────────────────────┐  │
│  │  [textarea_________]                                 │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                           │
│  SheetFooter:               [ 取消 ]  [ 创建公司 ]        │
└───────────────────────────────────────────────────────────┘
```

复用页面已有的 `Sheet` / `SheetContent` 组件，宽度与公司详情 Sheet 一致（`w-[660px]`）。表单用 label+input 竖排布局，分三个视觉分组（基本信息 / 联系人 / 备注），用 `<section>` + 小标题分隔。

### D2: 表单字段明细

| 字段 | 组件 | 必填 | 后端 payload key | 写入表 |
|------|------|------|-----------------|--------|
| 公司名称 | Input | 是 | `name` | waimaotong_clean_companies.company_name |
| 英文名称 | Input | 否 | `english_name` | waimaotong_clean_companies.english_name |
| 国家 | Select | 否 | `country` | waimaotong_clean_companies.country_iso3 |
| 域名 | Input | 否 | `domain` | waimaotong_clean_companies.domain |
| 网站 | Input | 否 | `website` | waimaotong_clean_companies.website |
| 电话 | Input | 否 | `phone` | waimaotong_clean_companies.phone |
| 行业 | Input | 否 | `industry` | waimaotong_clean_companies.industry |
| 员工规模 | Select | 否 | `employee_size` | waimaotong_clean_companies.employee_size |
| 成立年份 | Input (number) | 否 | `founded_year` | waimaotong_clean_companies.founded_year |
| 地址 | Input | 否 | `full_address` | waimaotong_clean_companies.full_address |
| 公司简介 | Textarea | 否 | `description` | waimaotong_clean_companies.description |
| 产品标签 | TagInput | 否 | `product_tags` | waimaotong_clean_companies.product_tags |
| 备注 | Textarea | 否 | `note` | tenant_companies.note |

国家下拉列表复用 `CompanyFilters` 中已有的国家数据（从 `tenantApi.companies.filters()` 获取 `countries` 列表）。

员工规模下拉选项与 admin 端一致：`1-10`, `11-50`, `51-200`, `201-500`, `501-1000`, `1001-5000`, `5000+`。

### D3: 联系人子表单

联系人为可选区域，默认显示一行空行。每行三个字段：

| 字段 | payload key | 写入表 |
|------|------------|--------|
| 姓名 | `contacts[].name` | waimaotong_clean_contacts.name |
| 邮箱 | `contacts[].email` | waimaotong_clean_contacts.email |
| 职位 | `contacts[].title` | waimaotong_clean_contacts.position |

点「+ 添加联系人」追加一行。每行可单独删除（至少保留一行空行，但不强制填写）。提交时过滤掉全空的行。

后端 `_ensure_contact_from_payload` 已支持 `contacts[]` 数组格式，每条去重逻辑：按 `sys_company_id + email` 查重。

### D4: 提交流程

```
用户点击「创建公司」
  ↓
前端校验: name 非空
  ↓
构建 payload:
{
  name: "xxx",
  english_name: "xxx",
  country: "CHN",
  domain: "xxx.com",
  website: "https://xxx.com",
  phone: "+86-xxx",
  industry: "xxx",
  employee_size: "51-200",
  founded_year: 2010,
  full_address: "xxx",
  description: "xxx",
  product_tags: ["tag1", "tag2"],
  note: "xxx",
  contacts: [
    { name: "张三", email: "z@xxx.com", title: "CEO" }
  ]
}
  ↓
POST /api/v1/companies
  ↓
成功 → toast.success + 关闭 Sheet + invalidate 列表查询
失败 → toast.error(response.data.message)
```

### D5: 后端 INSERT 扩展

`tenant_ops_service.py:164-184` 的 INSERT 语句从：

```sql
INSERT INTO waimaotong_clean_companies
  (company_name, english_name, country_iso3, domain, website, industry, product_tags)
VALUES (...)
```

扩展为：

```sql
INSERT INTO waimaotong_clean_companies
  (company_name, english_name, country_iso3, domain, website, industry, product_tags,
   phone, employee_size, founded_year, full_address, description)
VALUES (...)
```

新增 5 个字段的参数从 `payload.get()` 取值，全部可选。`founded_year` 需要类型转换（`int` 或 `None`）。

### D6: 按钮位置

「新增公司」按钮放在 `PageHeader` 右侧（与 send-plans 列表页风格一致）：

```
┌─────────────────────────────────────────────────────────┐
│  公司列表                                   [+ 新增公司] │
│  筛选、查看和处理租户公司数据                              │
└─────────────────────────────────────────────────────────┘
```

### D7: 文件结构

```
companies/
  page.tsx                  # 列表页（加按钮 + 引入 Sheet）
  company-detail.tsx        # 详情 Sheet（不改）
  add-company-sheet.tsx     # 新增：新增公司 Sheet 表单
```

新增一个文件 `add-company-sheet.tsx`，由 `page.tsx` 控制 open 状态。
