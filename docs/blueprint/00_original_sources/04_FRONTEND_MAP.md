# 前端页面地图

> 技术栈: React 19 + TypeScript + Ant Design 6 + Vite 7
> 路由: react-router-dom 7
> HTTP: Axios (Bearer Token from localStorage)
> 状态管理: 纯 React Hooks（无 Redux/Zustand）

---

## 1. 路由结构

```
/login                → Login (公开)
/                     → Home (Dashboard)
/plans                → Plans
/plans/:id            → PlanDetail / PlanFollowUpDetail
/keywords             → Keywords
/company-assets       → CompanyAssets
/companies            → Companies
/contacts             → Contacts
/templates            → Templates
/drafts               → Drafts
/cleaning-rules       → CleaningRules
/tasks                → Tasks
*                     → Redirect to /
```

**路由守卫**: `RequireAuth` 组件检查 localStorage 中的 JWT Token，无 Token 重定向到 `/login`。

**布局**: `AdminLayout` — 固定深色侧边栏(240px，可折叠) + 顶部面包屑 + 用户头像 + 登出。

---

## 2. 页面详情

### 2.1 Login (`/login`)
**功能**: 用户名密码登录
**API**: `POST /api/auth/login`
**行为**: 登录成功后 Token 存入 localStorage，跳转 `/`

---

### 2.2 Dashboard / Home (`/`)
**功能**: 系统运营全貌

| 模块 | API | 展示内容 |
|------|-----|----------|
| EngageLab 邮件统计 | `GET /api/dashboard/engagelab-stats` | 发送/送达/打开/点击趋势图 |
| LLM 余额 | `GET /api/dashboard/llm-balance` | OpenRouter 剩余额度 |
| 每日邮件配额 | `GET /api/dashboard/daily-quota` | 限额/已用/剩余 |
| 计划概览 | `GET /api/plans` + `GET /api/dashboard/plan-overview` | 按计划查看进度 |

---

### 2.3 Plans (`/plans`)
**功能**: 计划列表 + 创建/编辑

| 操作 | API |
|------|-----|
| 列表 | `GET /api/plans` |
| 进度 | `GET /api/plans/{id}/progress` |
| 创建 | `POST /api/plans` |
| 编辑 | `PUT /api/plans/{id}` |
| 删除 | `DELETE /api/plans/{id}` |
| 行业选项 | `GET /api/product-config` |

**UI特点**: 卡片式列表，每个计划显示状态标签 + 进度条 + 优先级。

---

### 2.4 PlanDetail (`/plans/:id`)
**功能**: 计划详情 — 系统中最复杂的页面

| 功能区 | API | 说明 |
|--------|-----|------|
| 基本信息 | `GET /api/plans/{id}` | 计划元数据 |
| 流水线进度 | `GET /api/plans/{id}/progress` | collect→clean→draft→send 四阶段进度 |
| 关键词列表 | `GET /api/keywords?plan_id={id}` | 计划关联的关键词 |
| 公司列表 | `GET /api/companies?plan_id={id}` | A/B/X 公司 |
| 草稿列表 | `GET /api/drafts?plan_id={id}` | 邮件草稿 |
| 发送预览 | `GET /api/plans/{id}/sending-preview` | 时区感知排期 |
| 触发Flow | `POST /api/plans/{id}/trigger/{flow}` | 手动触发 |
| 选择公司 | `POST /api/plans/{id}/select-companies` | A/B 选择/跳过 |
| 审批草稿 | `POST /api/plans/{id}/approve-drafts` | 批量审批 |
| 状态流转 | `POST /api/plans/{id}/transition` | 手动推进状态 |

**UI特点**:
- 管道可视化: collect → clean → draft → send 进度条
- 10秒自动刷新（活跃状态时）
- 分标签页展示不同维度数据

---

### 2.5 Keywords (`/keywords`)
**功能**: 关键词 CRUD

| 操作 | API |
|------|-----|
| 列表 | `GET /api/keywords` |
| 计划下拉 | `GET /api/plans` |
| 创建 | `POST /api/keywords` |
| 编辑 | `PUT /api/keywords/{id}` |
| 删除 | `DELETE /api/keywords/{id}` |

---

### 2.6 CompanyAssets (`/company-assets`)
**功能**: 原始采集公司数据总览

| 操作 | API |
|------|-----|
| 列表 | `GET /api/company-assets` |
| 统计 | `GET /api/company-assets/stats` |
| 筛选选项 | `GET /api/company-assets/filters` |

---

### 2.7 Companies (`/companies`)
**功能**: 已分析公司列表（含评级）

| 操作 | API |
|------|-----|
| 列表 | `GET /api/companies` |
| 行业选项 | `GET /api/product-config` |
| 计划选项 | `GET /api/plans` |

**UI特点**: Drawer 抽屉查看公司详情，含 ScoreDimensionIndicator 雷达图展示三维评分。

---

### 2.8 Contacts (`/contacts`)
**功能**: 联系人管理（两个视图）

| 操作 | API |
|------|-----|
| 全部联系人 | `GET /api/contacts` |
| 买家联系人 | `GET /api/contacts/buyer` |
| 筛选选项 | `GET /api/contacts/buyer/filters` |

---

### 2.9 Templates (`/templates`)
**功能**: 邮件模板管理

| 操作 | API |
|------|-----|
| 列表 | `GET /api/templates` |
| 行业选项 | `GET /api/product-config` |
| 创建 | `POST /api/templates` |
| 编辑 | `PUT /api/templates/{id}` |
| 删除 | `DELETE /api/templates/{id}` |
| 预览 | `GET /api/templates/{id}/preview` |

---

### 2.10 Drafts (`/drafts`)
**功能**: 邮件草稿审核

| 操作 | API |
|------|-----|
| 列表 | `GET /api/drafts` |
| 计划筛选 | `GET /api/plans` |
| 审批 | `POST /api/drafts/{id}/approve` |
| AI重写 | `POST /api/drafts/{id}/rewrite` |
| 重写历史 | `GET /api/drafts/{id}/rewrite-history` |

**UI特点**: Drawer 展示草稿详情，支持中英文对照查看。

---

### 2.11 CleaningRules (`/cleaning-rules`)
**功能**: 产品行业配置（清洗规则）

| 操作 | API |
|------|-----|
| 列表 | `GET /api/product-config` |
| 创建 | `POST /api/product-config` |
| 编辑 | `PUT /api/product-config/{id}` |
| 删除 | `DELETE /api/product-config/{id}` |

---

### 2.12 Tasks (`/tasks`)
**功能**: Flow 运行监控

| 操作 | API |
|------|-----|
| 列表 | `GET /api/task-runs` |
| 停止 | `POST /api/task-runs/{id}/stop` |

**UI特点**: 10秒自动刷新，状态标签颜色区分。

---

## 3. 共享组件

| 组件 | 用途 |
|------|------|
| `RequireAuth` | 路由守卫 |
| `AdminLayout` | 侧边栏+顶栏布局 |
| `ScoreDimensionIndicator` | 三维评分雷达/指标展示 |

---

## 4. API 层封装

`web/src/api/` 使用 Axios 实例:
- 基础URL: 从环境变量读取
- 请求拦截器: 自动附加 `Authorization: Bearer <token>`
- 响应拦截器: 401 自动跳转登录页

---

## 5. 产品化标注

| 现状 | 产品化需求 |
|------|-----------|
| 12个管理页面，偏开发者视角 | 面向业务人员的简化视图 |
| 无引导流程 | 新用户 Onboarding 向导 |
| 无国际化 | i18n 支持（至少中英文） |
| 纯 React Hooks 状态 | 考虑全局状态管理（多页面数据共享） |
| 无移动端适配 | 响应式设计 |
| 无实时通知 | WebSocket 推送状态变更 |
| Ant Design 默认主题 | 品牌化定制主题 |
