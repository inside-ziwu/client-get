# Phase 3+4: 功能页面 + 设置页面

> 前置：Phase 2 已完成（数据密集页面可用）
> 完整规划见 `../../openspec/changes/tenant-nextjs-rewrite/design.md`

## Phase 3: 功能页面

### 3.1 Templates 页

`src/app/(dashboard)/templates/page.tsx`

参照现有 `apps/tenant/src/pages/Templates/index.tsx`（约 250 行）。

核心功能：
- 模板列表（卡片或表格展示）
- 新建模板（Dialog 弹窗 + 表单）
- 编辑模板
- 预览模板（HTML 内容渲染）
- 删除模板（AlertDialog 确认）

### 3.2 EmailMonitor 页

`src/app/(dashboard)/email-monitor/page.tsx`

参照现有 `apps/tenant/src/pages/EmailMonitor/index.tsx`（约 300 行）。

核心功能：
- 邮件发送统计（发送数、送达率、打开率、回复率）
- 趋势图（用简单的 div CSS 条形图或折线近似）
- AI 分析结果展示

### 3.3 Intelligence 页

`src/app/(dashboard)/intelligence/page.tsx`

参照现有 `apps/tenant/src/pages/Intelligence/index.tsx`（约 200 行）。

核心功能：
- 情报文章列表
- 订阅管理

## Phase 4: 设置页面

### 4.1 Settings/Keywords

`src/app/(dashboard)/settings/keywords/page.tsx`

参照现有 `apps/tenant/src/pages/Settings/Keywords/index.tsx`（约 150 行）。

核心功能：
- 关键词列表（表格）
- 新增关键词（Input + Button）
- 删除关键词（AlertDialog 确认）

### 4.2 Settings/Scoring

`src/app/(dashboard)/settings/scoring/page.tsx`

参照现有 `apps/tenant/src/pages/Settings/Scoring/index.tsx`（约 250 行）。

核心功能：
- 评分模板展示（只读）
- 租户权重调整（滑块或数字输入）
- 保存权重

### 4.3 Settings/AIProvider

`src/app/(dashboard)/settings/ai-provider/page.tsx`

参照现有 `apps/tenant/src/pages/Settings/AIProvider/index.tsx`（约 200 行）。

核心功能：
- OpenRouter API Key 配置
- 用量统计展示
- 模型选择

### 4.4 Settings/Team

`src/app/(dashboard)/settings/team/page.tsx`

参照现有 `apps/tenant/src/pages/Settings/Team/index.tsx`（约 200 行）。

核心功能：
- 团队成员列表（表格）
- 邀请成员（Dialog + 邮箱输入）
- 成员角色管理
- 移除成员

## 约束

- 所有页面 `'use client'`
- 表单用 useState
- 图表不引入 recharts 等重库
- 用 @shared/ui 的组件
