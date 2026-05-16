# Tasks · v3-tenant-companies

> Wave 2 附属 — 不阻塞主链，但 Slice 5 E2E 验收需完成
> 任务编号：`T-TC-XX`

## 0. 前置

- [x] T-TC-00 v3-data-foundation 完成并已归档（clean_companies +11 字段（D-038 9 + D-039 2） + product_tags 回填）
- [x] T-TC-01 起草 design.md（筛选组件复用方案 + scoring 两层模型）
- [x] T-TC-02 用户审 design.md

## 0.5 已归档依赖

> tenant company V3 contract cleanup 已归档为 `2026-05-10-tenant-company-v3-contract-cleanup`。本 change 不再重复承载旧字段收口任务。

- [x] T-TC-03 tenant company V3 contract cleanup 已归档，不在本 change 继续跟踪

## 1. C4 — 私有操作（UC-22 备注 + UC-23 标签 + D-020 群组）

> **2026-05-10 裁决**：UC-21 调分彻底移出本 change。本 change 只实现私有备注、私有标签与群组管理。

### 1.1 Drawer 编辑态切换

- [ ] T-TC-10 tenant/Companies Drawer 加 enterEditMode / exitEditMode 切换（按 mockup `tenant-companies.html`）
- [ ] T-TC-11 顶部按钮组：显示态（加入群组 / 编辑 / 关闭） vs 编辑态（加入群组 / 保存 / 取消）

### 1.3 私有备注（UC-22）

- [ ] T-TC-30 备注 textarea `noteEdit`
- [ ] T-TC-31 后端通过 jsonb payload 已支持，前端补编辑

### 1.4 私有标签（UC-23）

- [ ] T-TC-40 标签 add / remove `tagsEdit`
- [ ] T-TC-41 同上 jsonb payload

### 1.5 群组管理（UC-19 / D-020）

- [ ] T-TC-50 单条加入群组（行内按钮 `showAddGroup`）
- [ ] T-TC-51 批量加入群组（顶部 batch bar `showBatchAddGroup`）
- [ ] T-TC-52 加入群组 Modal（单条 + 批量共用）
- [ ] T-TC-53 与现有 groups + group_members 模型对齐
- [ ] T-TC-54 拉黑/取消拉黑入口样式对齐 mockup（UC-20 已 PASS）

## 2. C5 — 10 项筛选（D-038）

### 2.1 后端 filter API

- [ ] T-TC-60 多选 OR：国家 / 行业细分 / 产品标签 / 数据来源
- [ ] T-TC-61 档位筛：成立时间 / 注册资金 / 公司规模 / 进出口额 / 进出口次数 / 联系人数量
- [ ] T-TC-62 联系人数量档位：`0 / 1-3 / 4-10 / 11-30 / >30`
- [ ] T-TC-63 后端单测覆盖各组合
- [ ] T-TC-64 RLS 验证（A/B 隔离不破坏）
- [x] T-TC-65 修正 tenant 公司列表游标分页：列表超过 `limit` 时返回 `has_more=true` 与下一页 `cursor`，避免前端只显示第一页。

### 2.2 前端筛选组件

- [ ] T-TC-70 复用组件：tenant/Companies + tenant/CuratedCustomers 共用
- [ ] T-TC-71 多选 OR UI（按 mockup `tenant-companies.html` 顶部筛选栏）
- [ ] T-TC-72 档位筛 UI
- [ ] T-TC-73 已选筛选 chip 展示 + 一键清空
- [ ] T-TC-74 筛选与分页 / 排序联动
- [x] T-TC-75 将 tenant 公司列表从“加载更多”改为页码分页组件，并展示总数统计；筛选变化时回到第一页。

## 3. C6 — 默认评分模板（D-039 + D-039-X.1）

### 3.1 数据模型

- [ ] T-TC-80 scoring_templates 表加 industry 字段（PCB 默认模板）
- [ ] T-TC-81 建 tenant_scoring_weights 表（租户级权重覆盖）
- [ ] T-TC-82 数据迁移：现有 scoring_templates 迁到按行业模型

### 3.2 admin/ScoringTemplates 按行业 UI

- [ ] T-TC-90 admin/ScoringTemplates 按行业列表（按 mockup `admin-scoring-templates.html`）
- [ ] T-TC-91 PCB 7 维模板配置（工厂性质 / 规模 / 进出口额 / 次数 / 联系人 / 数据来源 / PCB 供应商）
- [ ] T-TC-92 维度 / 档位 / 分值映射 / 默认权重表单
- [ ] T-TC-93 模板预览效果（用真实数据预览评分）

### 3.3 tenant/Settings/Scoring 改造

- [ ] T-TC-100 tenant/Settings/Scoring 移除规则配置（按 mockup `tenant-settings-scoring.html` 改造）
- [ ] T-TC-101 仅展示模板 + 调权重表单
- [ ] T-TC-102 实时预览权重变化对评分的影响

### 3.4 scoring worker 分数摘要

- [ ] T-TC-110 scoring worker 写入 `model_score` / `score`
- [ ] T-TC-111 兜底：档位外 / 缺失 = 0 分
- [ ] T-TC-112 scoring worker 跑全量重打分（首次模板生效后）

## 4. Review

- [ ] T-TC-190 CE review → `_control/reviews/ce-review-v3-tenant-companies.md`
- [ ] T-TC-191 gstack eng review → `_control/reviews/gstack-eng-review-v3-tenant-companies.md`
- [ ] T-TC-192 Codex code review → `_control/reviews/codex-code-review-v3-tenant-companies.md`
- [ ] T-TC-193 修复 Blocker / High Risk

## 5. 验收（贡献 Slice 5 E2E）

- [ ] T-TC-199-A C4 验收：Drawer 私有备注、私有标签、群组操作可编辑 + 持久化
- [ ] T-TC-199-B C5 验收：10 项筛选组合查询返回正确数据
- [ ] T-TC-199-C C6 验收：admin 配按行业模板 + 租户调权重 → scoring worker 重打分 → `model_score` / `score` 正确
- [ ] T-TC-199-D 跨租户 RLS 验证（A 改私有状态 B 看不到）
