# Tasks · v3-contact-classification

> Wave 2 附属 — v3-email-delivery 的 T-ED-41 引用 classify 函数
> 任务编号：`T-CC-XX`

## 0. 前置

- [x] T-CC-00 v3-data-foundation 完成并已归档（alembic 升级 + worker base 就绪）
- [ ] T-CC-01 起草 design.md（3 表 + 1 视图 schema + classify 算法 + 切词规则）
- [ ] T-CC-02 用户审 design.md
- [ ] T-CC-03 业务方提供初始关键词清单（A/B/X 级）

## 1. 数据模型（C3-G1，方案 A：3 表 + 1 视图）

> **codex B-03 修订**：用户 2026-05-06 拍板方案 A。删 compiled 表，加视图 `v_tenant_contact_classified`。字段对齐决策池 M.1。

- [ ] T-CC-10 alembic 迁移：`position_classification_levels`（id / name / **display_name** / sort_order / is_sendable / **created_at** / **updated_at**）
- [ ] T-CC-11 alembic 迁移：`position_classification_categories`（id / level_id / name / **display_name** / **sort_order** / **created_at** / **updated_at**）
- [ ] T-CC-12 alembic 迁移：`position_classification_keywords`（id / category_id / keyword 小写 / created_at）
- [ ] T-CC-13 alembic 迁移：`v_tenant_contact_classified` 视图（sys_contact_id / level_id / category_id / is_sendable）— 实时计算
- [ ] T-CC-14 业务方初始关键词清单导入（A/B/X 级）
- [ ] T-CC-15 alembic 回滚预案

## 2. admin/contact-classification 页面（C3-G2）

- [ ] T-CC-20 admin 路由 + 侧边栏菜单注册
- [ ] T-CC-21 等级管理 UI（增删改 + is_sendable 开关 + sort_order 拖拽）
- [ ] T-CC-22 类别管理 UI（归属等级 + 增删改 + sort_order）
- [ ] T-CC-23 关键词管理 UI（归属类别 + 增删改）
- [ ] T-CC-24 整体预览（层级树形展示）
- [ ] T-CC-25 后端 CRUD API（admin 权限）
- [ ] T-CC-26 admin 改规则后视图实时反映（无需重建逻辑——视图本身就是实时计算）

## 3. classify(position) 函数（C3-G3）

- [ ] T-CC-30 切词规则：中英文混合 + 标点处理（空格/标点切词 + 全部小写）
- [ ] T-CC-31 集合交集查 keywords 表（与小写 keyword 做集合交集判断）
- [ ] T-CC-32 取最高等级（level.sort_order 最大）
- [ ] T-CC-33 未命中 → 归"未分类"虚拟等级，不投递
- [ ] T-CC-34 单测覆盖 A/B/X 级核心样本
- [ ] T-CC-35 性能验证：V3 数据量（5 租户 × 几千联系人）视图查询毫秒级完成

## 4. tenant/Settings/contact-rules 整段删除（C3-G4，codex H-03 扩大范围）

> codex H-03 验证：tenant 老模块涉及 5 处代码引用，仅删页面会留死代码 / 编译错误。

- [ ] T-CC-40 删除 `frontend/apps/tenant/src/router.tsx:56` 的 contact-rules 路由
- [ ] T-CC-41 删除 `frontend/apps/tenant/src/pages/Settings/ContactRules/` 整个目录
- [ ] T-CC-42 删除 `frontend/apps/tenant/src/pages/Onboarding/index.tsx` 中 `StepContactRules` 步骤（含 289 / 291 / 363 行引用）
- [ ] T-CC-43 删除 shared-api 包：`tenant/contact-rules` 客户端 + `queryKeys.contactRules`
- [ ] T-CC-44 删除后端：`backend/app/api/tenant/settings.py:86-104` contact-rules CRUD 端点
- [ ] T-CC-45 全仓搜索 `contactRules` / `contact-rules` / `ContactRules` 残留并清理
- [ ] T-CC-46 验证租户端编译通过 + 首登流程不再出现联系人规则配置
- [ ] T-CC-47 验证 admin 端 `admin/contact-classification` 页面正常（D-024 单端原则）

## 5. UC-08 / UC-25 集成（C3-G6）

- [ ] T-CC-50 邮件计划新建时调 classify(position) 取联系人
- [ ] T-CC-51 取所有 is_sendable=true 的联系人（不限每公司数量）
- [ ] T-CC-52 多步骤序列：第 N 轮发未发过的其他联系人
- [ ] T-CC-53 与 v3-email-delivery T-ED-41 联调

## 6. Review

- [ ] T-CC-90 CE review → `_control/reviews/ce-review-v3-contact-classification.md`
- [ ] T-CC-91 gstack eng review → `_control/reviews/gstack-eng-review-v3-contact-classification.md`
- [ ] T-CC-92 Codex code review → `_control/reviews/codex-code-review-v3-contact-classification.md`
- [ ] T-CC-93 修复 Blocker / High Risk

## 7. 验收

- [ ] T-CC-99-A admin 配置 3 表数据正确落库 + `v_tenant_contact_classified` 视图查询返回正确分类
- [ ] T-CC-99-B classify 函数命中 A/B 级正确返回 is_sendable=true
- [ ] T-CC-99-C classify 函数命中 X 级返回 is_sendable=false
- [ ] T-CC-99-D 未命中职位返回不投递
- [ ] T-CC-99-E tenant 端无任何配置入口（D-024）
- [ ] T-CC-99-F UC-08 邮件计划新建时调 classify 联调通过
