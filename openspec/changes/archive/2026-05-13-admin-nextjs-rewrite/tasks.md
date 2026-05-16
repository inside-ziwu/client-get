## Phase 1: 项目脚手架

- [x] 1.1 在 `frontend/apps/admin-next/` 初始化 Next.js 15 项目（App Router, TypeScript）
- [x] 1.2 配置 Tailwind CSS + shadcn/ui CLI (`components.json`, `globals.css`, `cn()` 工具)
- [x] 1.3 配置 `tsconfig.json` path alias 指向 `@shared/*` 包
- [x] 1.4 配置 `next.config.ts`：rewrites 代理 `/admin/api/*` 到后端、`output: 'standalone'`、`transpilePackages: ['@shared/api', '@shared/types', '@shared/hooks']`
- [x] 1.5 安装共享依赖：`@tanstack/react-query`, `zustand`, `axios`, `dayjs`
- [x] 1.6 创建 `src/providers.tsx`（QueryClientProvider，沿用现有配置：staleTime 30s, gcTime 5m, retry 1）
- [x] 1.7 修改 `@shared/api` 的 `createApiClient`，增加可选 `baseURL` 参数（默认值保持 `import.meta.env.VITE_API_BASE_URL`，Tenant 端不传参行为不变）
- [x] 1.8 创建 `src/lib/api.ts`（调用 `createApiClient('admin', { baseURL: '' })` + `createAdminApi`）
- [x] 1.9 创建 `src/lib/format.ts`（`formatDateTime` 工具函数）
- [x] 1.10 验证 `pnpm dev` 能启动且代理到本地后端正常
- [x] 1.11 验证 Tenant 端 `pnpm dev` 不受 `@shared/api` 修改影响（回归）

## Phase 2: 布局与认证

- [x] 2.1 安装 shadcn/ui 基础组件：Button, Input, Avatar, DropdownMenu, Sheet, ScrollArea
- [x] 2.2 创建根布局 `src/app/layout.tsx`（html/body + providers 包装）
- [x] 2.3 创建侧边栏组件 `src/components/layout/sidebar.tsx`，还原 6 组导航结构（客户/采集/营销）
- [x] 2.4 创建 `(dashboard)/layout.tsx`（侧边栏 + RequireAuth 守卫 + 用户信息加载）
- [x] 2.5 创建登录页 `src/app/login/page.tsx`（表单 + JWT 存储 + 跳转）
- [x] 2.6 端到端验证：登录 → 进入主布局 → 侧边栏导航 → 登出

## Phase 3: L 档页面（低复杂度，快速推进）

- [x] 3.1 安装 shadcn/ui 组件：Card, Table, Dialog, Form, Label, Separator, Badge, Tooltip
- [x] 3.2 `Login` — 已在 Phase 2 完成
- [x] 3.3 `WarmupRules` — 规则表单 + 动态行编辑
- [x] 3.4 `AIConfig` — 双表布局（AI 模型 CRUD + 场景默认值）

## Phase 4: M 档页面（中复杂度）

- [x] 4.1 安装 shadcn/ui 补充组件：Sheet (Drawer), AlertDialog (Popconfirm), Select, Textarea, Switch, Checkbox, Collapsible, Tabs
- [x] 4.2 `IntelligenceSources` — 列表 + 表单 + 批量 JSON 导入
- [x] 4.3 `PeersData` — 11 列数据表 + 筛选表单 + 详情 Sheet
- [x] 4.3.1 `PeersCleaned` — 接入已有 Next.js 同行数据（清洗）页面，查询 peer-companies API + 健康指标 + 详情 Sheet
- [x] 4.4 `CollectionTasks` — 可展开行 + 状态轮询 + 历史 Sheet
- [x] 4.5 `DataSources` — 数据源 CRUD + 凭证嵌套管理 + 动态表单
- [x] 4.6 `ContactClassification` — 三列层级 UI（Level → Category → Keywords）
- [x] 4.7 `EmailTemplates` — 模板 CRUD + GrapesJS 编辑器集成
  - [x] 4.7.1 迁移 `GrapesEmailEditor` 组件（forwardRef + useImperativeHandle）
  - [x] 4.7.2 安装 `grapesjs` + `grapesjs-preset-newsletter`
  - [x] 4.7.3 验证编辑器加载、保存、预览完整流程

## Phase 5: S 档页面（高复杂度）

- [x] 5.1 安装日期选择器依赖：`react-day-picker` + shadcn DatePicker
- [x] 5.2 `CollectionArchive` — 双 Tab（Tendata + Clean Archive）+ 多级筛选 + 嵌套联系人表
  - [x] 5.2.1 Tendata Tab：15+ 列表 + 10+ 筛选字段（贸易金额范围、供应商过滤、成立年份等）
  - [x] 5.2.2 Clean Archive Tab：规范化公司视图 + RangeField 组件
  - [x] 5.2.3 详情 Sheet：联系人子表
- [x] 5.3 `ScoringTemplates` — 评分模板 CRUD + DimensionEditor
  - [x] 5.3.1 DimensionEditor 子组件：7 维度 × 3-4 条件的内联分数编辑
  - [x] 5.3.2 等级阈值配置（S/A/B/C/D）
  - [x] 5.3.3 预览 Dialog + 旧格式向后兼容
- [x] 5.4 `Tenants` — 租户管理 + 4 Tab 详情
  - [x] 5.4.1 租户列表 + 创建/激活/暂停/删除
  - [x] 5.4.2 域名管理 Tab（添加 + 验证）
  - [x] 5.4.3 团队管理 Tab（成员 CRUD + 角色 + 密码重置）
  - [x] 5.4.4 OpenRouter 配置 Tab（API Key + 余额刷新）

## Phase 6: 部署

- [x] 6.1 编写 `frontend/Dockerfile.admin-next`（多阶段：pnpm install → next build → node:20-alpine standalone）
- [x] 6.2 编写 `frontend/deploy/push-admin-next.sh`（复用现有 tag 生成逻辑，镜像名 `clientget-admin-next`）
- [x] 6.3 本地 `docker build` 验证镜像构建成功
- [x] 6.4 推送镜像到阿里云 ACR
- [ ] 6.5 在 Sealos 创建/更新 admin-next 应用实例，使用已内置 `NEXT_PUBLIC_ADMIN_API_BASE_URL=https://api.xinanpcb.com` 的镜像；生产不依赖同域名 `/admin/api/*` Ingress path routing
- [ ] 6.6 验证生产环境访问：登录、导航、API 调用、GrapesJS 编辑器

## Phase 7: 收尾

- [ ] 7.1 全部 10 个页面逐一回归测试，对比旧版行为
- [x] 7.2 确认无遗漏后，旧 admin 应用下线
- [x] 7.3 镜像名从 `clientget-admin-next` 改回 `clientget-admin`
- [x] 7.4 删除 `frontend/apps/admin/` 和旧 Vite `frontend/Dockerfile.admin` 实现，`Dockerfile.admin` 由 Next standalone 接管
- [x] 7.5 更新 `frontend/deploy/push-admin.sh` 指向 Next standalone Dockerfile
- [ ] 7.6 更新 `frontend/apps/admin-next/` 目录名为 `frontend/apps/admin/`（可选，视 monorepo 约束决定；本轮选择保留目录名以降低切换风险）
- [ ] 7.7 Tenant 端全量回归：验证登录、核心页面、API 调用均正常（确认 `@shared/api` 修改无副作用）

## Phase 8: 上线后细节优化

- [x] 8.1 登录页标题改为「外贸获客SaaS」，移除「使用真实 API 登录后台管理系统」
- [x] 8.2 Admin 展示文案中「租户」统一改为「用户」（不改 API/类型命名）
- [x] 8.3 菜单「客户管理」改为「用户管理」，分组「客户」改为「用户」

## Phase 9: 用户管理体验与线上性能修复

- [x] 9.1 调查线上「数据加载慢」根因，区分前端首屏资源、后端 API 响应、网络/Ingress 与详情页串行加载问题，并记录结论：`https://admin.xinanpcb.com/login` 与 `/api/healthz` 多次出现 10s+ TTFB，静态 chunk 约 0.8s TTFB，初步指向前端 Node 实例/Ingress 首包抖动；用户详情加载保持并行请求
- [x] 9.2 修复用户列表字段展示：创建时间必须正常显示，状态等后端枚举必须中文化
- [x] 9.3 简化创建用户表单：移除 Slug、发件域名、预热档位，Slug 由系统自动生成或由前端按名称生成后提交
- [x] 9.4 用户详情基础信息支持编辑并保存，详情页展示用户后台管理地址且支持复制
- [x] 9.5 重做查询区、详情 Sheet、域名管理、团队管理的视觉与交互：查询不挤压；域名添加为「域名 + 预热档位」且预热档位来自配置；验证状态显示「已验证」等中文；团队成员支持编辑
- [x] 9.6 修复生产环境「同行公司」页面必现 client-side exception：`raw_payload` 兼容 `null` / 非对象 / 数组，列表与详情读取前统一收敛为安全对象，并新增契约断言防止回归
