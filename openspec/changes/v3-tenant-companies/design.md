# Design · v3-tenant-companies

## Context

`tenant-company-v3-contract-cleanup` 已归档，tenant company 对外契约已收口到 V3 字段。本 change 继续承载未完成的三块主体能力：

- C4 私有操作：备注、标签、群组管理的 tenant 前端编辑体验
- C5 10 项筛选：Companies 与 CuratedCustomers 共用筛选能力
- C6 默认评分模板：admin 配行业模板，tenant 只调权重，scoring worker 写入分数摘要

## Goals / Non-Goals

**Goals:**
- tenant/Companies Drawer 支持编辑私有备注、私有标签和群组关系。
- tenant/Companies 与 tenant/CuratedCustomers 共用 10 项筛选组件。
- admin/ScoringTemplates 支持按行业配置 PCB 默认模板。
- tenant/Settings/Scoring 改为只展示模板并调整租户权重。
- scoring worker 基于模板和租户权重写入 `model_score` / `score`，缺失或档位外数据按 0 分处理。

**Non-Goals:**
- 不重复实现已归档的 `tenant-company-v3-contract-cleanup`。
- 不恢复或兼容旧 tenant company 字段契约。
- 不实现 UC-21 人工调分。
- 不实现联系人分类、公司级中断、主联系人或完整 Tenant Dashboard。

## Decisions

### C4：Drawer 编辑态

Drawer 默认展示态，点击编辑后进入编辑态。编辑态只提交私有备注、私有标签和群组操作；保存成功后刷新当前公司详情和列表。

### C5：筛选组件复用

Companies 与 CuratedCustomers 共享同一个筛选组件和参数序列化逻辑。筛选分两类：

- 多选 OR：国家、行业细分、产品标签、数据来源
- 档位筛：成立时间、注册资金、公司规模、进出口额、进出口次数、联系人数量

分页和排序由列表页持有，筛选变化时重置分页游标。

### C6：两层评分模型

admin 管行业模板，tenant 只调权重。scoring worker 读取当前行业模板和租户权重覆盖，生成 `model_score` / `score`。缺失字段、未知档位或规则不匹配时，该维度得 0 分。

## Risks / Trade-offs

- 筛选维度多，前后端参数容易漂移 -> 通过共享参数构造和后端组合测试约束。
- Drawer 同时编辑备注、标签、群组，状态刷新容易漏 -> 保存后统一刷新详情、列表、群组成员查询。
- 评分模板改造涉及 admin、tenant、worker 三端 -> 分数据模型、admin UI、tenant UI、worker 四段实施并分别验收。

## Verification

- C4：备注、标签、群组操作持久化，并验证跨租户隔离。
- C5：后端组合筛选测试覆盖 10 项维度，前端 typecheck 通过。
- C6：admin 配模板、tenant 调权重、worker 重打分后 `model_score` / `score` 正确。
