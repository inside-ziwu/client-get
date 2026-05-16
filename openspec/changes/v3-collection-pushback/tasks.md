# Tasks · v3-collection-pushback

> Wave 2 — 与 v3-email-delivery / v3-tenant-companies / v3-contact-classification 并行
> 任务编号：`T-CP-XX`

## 0. 前置

- [x] T-CP-00 v3-data-foundation 完成验收并已归档（cleanup_service 部署 + alembic 升级到位）
- [x] T-CP-01 起草 design.md（keyword_master + collection_run / collection_task + UC-11 fan-out 算法）
- [x] T-CP-02 用户审 design.md

## 1. Slice 1.C — Admin 关键词页全平台任务语义（M-01）

> **codex B-01 修订**：UC-10 admin 启动按钮已实现（`admin/CollectionTasks/index.tsx:230-302`），不再 from-scratch；本节改为复核 + 按 D-035 限制 channel。

- [x] T-CP-10 复核现有 admin/CollectionTasks `triggerMutation` + 触发按钮交互是否符合 V3 流程（与 mockup `admin-collection-tasks.html` 对比）
- [x] T-CP-11 明确 admin 关键词页聚合对象 = `keyword_master` / `collection_run`，不是 tenant 级 `collection_keywords.subscription_status`
- [x] T-CP-12 前端状态映射：`not_started` / `stopped` → 未开始；`running` → 采集中；`daily_limit_reached` → 今日已达上限；`completed` → 已采完
- [x] T-CP-13 操作映射：未开始显示"采集/历史"；采集中显示"停止/历史"；今日已达上限显示"停止/历史"；已采完显示"历史"
- [x] T-CP-14 D-035 限制：UI 隐藏 / 禁用 direct channel（外贸通推迟 V3.1+），仅保留 reverse（反推）入口
- [x] T-CP-15 后端 `POST collection-keywords/trigger` 校验：拒绝 channel=direct 的请求（防御性）
- [x] T-CP-16 admin 端权限校验复核（D-024 单端原则）
- [x] T-CP-17 任务状态轮询机制复核（run 状态 + 最新 task 状态），验证 V3-COL-002 + V3-COL-003

## 2. Slice 1.D — KeywordMaster + UC-11（C2-G1~G5）

### 2.1 数据模型

- [x] T-CP-20 数据模型职责迁出：`keyword_master / tenant_keyword` schema 迁入 `v3-data-foundation` T-DF-24 / T-DF-26
- [x] T-CP-21 数据模型职责迁出：`collection_runs / collection_tasks.run_id` schema 迁入 `v3-data-foundation` T-DF-25
- [x] T-CP-22 旧表职责迁出：`collection_keywords / collection_task_keywords` 真源废弃策略迁入 `v3-data-foundation` T-DF-27
- [x] T-CP-23 本 change 不再承担上述基础 migration；后续只基于 data-foundation 产物实现 fan-out / worker 行为
- [x] T-CP-24 keyword 归一化函数（英文大小写无关 + 去多余空格/标点；中文关键词如"线路板"允许）+ 单测
- [x] T-CP-25 collection_runs 基础 schema 已迁入 `v3-data-foundation`
- [x] T-CP-26 collection_tasks run 关联基础 schema 已迁入 `v3-data-foundation`

### 2.2 UC-06 命中分支

- [x] T-CP-30 tenant/Intelligence 配关键词时查 keyword_master
- [x] T-CP-31 命中老关键词 → UI 提示"已采过 N 家公司，立即可见"
- [x] T-CP-32 未命中 → UI 提示"待运营在 admin 启动首采"
- [x] T-CP-33 tenant 新增同词只写 tenant_keyword 订阅关系，不创建、不重启、不停止、不改变 collection_run 状态
- [x] T-CP-34 验证 V3-COL-001

### 2.3 UC-11 fan-out worker

- [ ] T-CP-40 新建 fan_out_service worker（worker base class 接入）
- [x] T-CP-41 fan-out 算法：tenant 配老关键词 → 查 shared_companies 命中 → 复制到 tenant_companies 视图
- [x] T-CP-42 幂等键（同 tenant + 同 keyword 不重复 fan-out）
- [x] T-CP-43 fan-out 单测覆盖
- [ ] T-CP-44 fan-out worker Sealos 部署

### 2.4 UC-12/14 改写

- [ ] T-CP-50 collection worker 加关键词归一化处理
- [x] T-CP-51 collection worker 按 `collection_task.run_id` 读取/更新 `collection_run` cursor，确保跨天续采不是从头开始
- [x] T-CP-52 UC-14 分发：通过 keyword_master 显式分发到所有命中租户的 tenant_companies

## 3. Slice 1.E — 励销云每日上限与跨天续采

- [x] T-CP-60 励销云请求策略：单次请求默认 page_size=10，最大允许 100
- [x] T-CP-61 每个 keyword_master 按北京时间自然日统计励销云 stage1 采集量，每日上限 1000
- [x] T-CP-62 达到 1000 后：当前 task completed，run 状态 `daily_limit_reached`，admin 显示"今日已达上限"
- [x] T-CP-63 达到 1000 后立即创建同一 run 下的 pending continuation task，scheduled_at=次日北京时间 08:00
- [x] T-CP-64 scheduler 到点后执行 continuation task，继承上一 task/run 的 cursor/page/skip_source_ids，不从头采集
- [x] T-CP-65 励销云无更多数据：task completed，run 状态 `completed`，admin 显示"已采完"
- [x] T-CP-66 admin 点停止：取消当前 running task 与未来 pending/scheduled continuation tasks，run 状态 `stopped`，次日不自动继续
- [x] T-CP-67 腾道 stage2 Cookie 失效时不阻塞 stage1 run/task 状态闭环；stage2 自动触发暂不作为本 change 验收前置

## 4. Slice 2 — 去重 + 租户隔离（C2-G4）

- [x] T-CP-70 跨租户 UNIQUE 约束验证（同公司不同租户 → shared_companies 1 行 + tenant_companies N 行）
- [ ] T-CP-71 A/B 双租户 RLS 验证：A 看不到 B 私有状态字段（评分调整 / 备注 / 标签 / 群组）
- [ ] T-CP-72 励销云原始数据租户永不可见（V3 N-* 业务规则）
- [ ] T-CP-73 V3-COL-006 / V3-COL-007 / V3-AUTH-001 验收

## 5. Review

- [ ] T-CP-90 CE review → `_control/reviews/ce-review-v3-collection-pushback.md`
- [ ] T-CP-91 gstack eng review → `_control/reviews/gstack-eng-review-v3-collection-pushback.md`
- [ ] T-CP-92 Codex code review → `_control/reviews/codex-code-review-v3-collection-pushback.md`
- [ ] T-CP-93 修复 Blocker / High Risk

## 6. 验收

- [ ] T-CP-99-A V3-COL-001 通过：tenant 配新关键词成功落库
- [ ] T-CP-99-B V3-COL-002 通过：admin 启动关键词采集 → collection_run + 首个 collection_task 入库
- [ ] T-CP-99-C V3-COL-003 通过：worker 励销云 stage1 采到至少 1 家同行公司
- [ ] T-CP-99-D V3-COL-007 通过：A 租户看不到 B 租户私有状态
- [ ] T-CP-99-E V3-AUTH-001 通过：A/B 隔离严格
- [ ] T-CP-99-F E2E：A 采过的关键词 → B 配同关键词 → B 立即看到 A 当年客户（0 等待）
- [ ] T-CP-99-G E2E：达到励销云每日 1000 → admin 显示"今日已达上限" → 次日北京时间 08:00 后从 cursor 继续
- [ ] T-CP-99-H E2E：admin 停止采集 → 当前 task 与未来 continuation task 一并取消 → 次日不自动继续
