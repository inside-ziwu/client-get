# Spec 审查报告 — 采集模块

**审查对象**: `docs/spec-collection-module.md` v1.1
**视角**: CEO（战略/范围）+ Eng（架构/边界）
**日期**: 2026-04-30

---

## 一、CEO 视角：战略与范围挑战

### 1.1 核心 premise 检查

#### 🔴 Premise 1: "管理员手动启动" 是最优模型吗？

**Spec 现状**：完全手动，运营每天点一次启动。

**6 个月后悔点**：
- 运营忘记点 → 数据停摆一天，租户投诉
- 运营离岗 → 整个平台采集停摆
- 平台规模化（10+ 租户、100+ 关键词）后，「每天点一次」已经不是工作量问题，是单点责任问题

**Eng 副作用**：手动模型必然引入 cron 兜底（运维一定会加），最后变成"既手动又定时"的尴尬状态。

**建议**：保留手动启动入口（运营可以加急），但**默认行为是定时调度**（每天凌晨自动启动一轮）。Spec 现在的 Q1 决策可能是误解了"手动控制"的真实需求——运营要的不是「每天点」，是「能控」。能停、能改配额、能跳过某关键词，比「每天必须点」更重要。

#### 🟡 Premise 2: "Phase 1 只做外贸通直采" 真的有商业价值吗？

**Spec 现状**：反推采集（精准客户）整体推 Phase 2。

**核心问题**：反推采集才是产品差异化（「精准客户」+ 同行竞争情报）。外贸通直采是市面上工具普遍能做的（任何外贸通账号都能搜）。Phase 1 上线一个「同质化」的功能，对租户的拉力可能不足。

**6 个月后悔点**：
- 租户上线后第一次用，看到的是「外贸通搜出来 1000 家公司」——和他们自己直接登外贸通搜没什么区别。差异化感知弱。
- 反推采集才是平台真正的卖点，但它要等 Phase 2、要等反向工程。

**反问**：腾道真的没有 API 吗？还是只是不想付费？

- 腾道开放平台 (`open-api.tendata.cn`) 在你之前的代码里是有的——是当时凭证拿不到，还是接口已下线？
- 如果开放 API 只是「太贵」，临时方案是不是付费跑通几个月，等爬虫成熟再切换？
- 反向工程 + 维护爬虫的总成本（人力 + 反爬封禁风险），可能比 API 调用费还高

**建议**：Spec 第 8 节加一项调研：**确认腾道开放 API 的可用性与成本**。如果 API 实际可用（只是贵），Phase 1 应该把「反推-腾道」一起带上，让 Phase 1 就是个完整闭环（外贸通直采 + 反推-腾道）。反推-外贸通才是 Phase 2 的延后项。

#### 🟡 Premise 3: "凭证集中托管" 真的合规吗？

**Spec 现状**：所有数据源凭证由平台运营录入，所有租户共享。

**风险**：
- 外贸通账号 ToS 通常禁止「为多租户提供数据服务」。一个外贸通账号给 100 个租户用，账号一封整个平台停摆。
- 数据采集的法律责任主体不清（是平台爬的还是租户爬的？）。
- 一个账号每天 15 RPM 全平台共享 = 实际每个租户分到的 RPM 极少（10 租户时每租户 1.5 RPM），扩展性差。

**6 个月后悔点**：
- 商业化时大客户问"我能不能用我自己的账号"，回答"不能"会丢单。
- 账号被封时全平台停服，对外故事难讲。

**建议**：Spec 至少**留扩展位**——`data_source_credentials` 表设计时不要硬编码 platform-only 模式，允许未来挂租户级凭证（即使 Phase 1 只用平台凭证）。`Non-goals` 里的「不做租户自带凭证」是产品决策，不是技术约束，要分清楚。

### 1.2 范围讨论

#### 🟢 Phase 1 范围合理（如果反推-腾道 API 可用，建议带上）

外贸通直采作为闭环本身合理：
- 现成代码（原始 repo）
- 全链路简单：1 种采集源 + 1 个 task_type + 直接公司列表
- 适合用来验证调度模型、进度管理、凭证管理这些**框架性**问题

但前提是：让租户看到价值。建议 Phase 1 启动后，前 1-2 个月就启动 R-1 腾道反向工程（或 API 调研），确保 Phase 2 不会拖。

#### 🔴 Non-goals 里有一项可能错了：「关键词重新采集」

**Spec 现状**：Q13 决策"本期不考虑重新采集"，done = 永久 done。

**问题**：
- 外贸通的搜索结果**会变**（新公司加入、老公司被标记），3 个月前 done 的数据 6 个月后可能严重过期
- 如果 done 永久，租户无法主动刷新一个关键词的数据，只能加新关键词。但「新关键词」语义上不同——他们想要的是「重新采 PCB 这个关键词」，不是「采 PCB-2026」
- 这跟 Q1（手动启动）有冲突：既然是手动启动，运营点一下重启某关键词应该是合理操作

**6 个月后悔点**：
- 租户问"为什么我看不到最近一周新加入外贸通的公司"，回答"那个关键词上次跑过了"——逻辑上很难解释
- 数据陈旧导致用户感知"平台数据老旧"

**建议**：Spec 改为「Phase 1 不做自动周期重采，但运营在 Admin 后台可以手动重置某关键词到 pending 状态」。这是一个最小成本的逃生通道，避免 done 一旦达成就永久卡死。

### 1.3 战略盲点

#### 🟡 同行公司"仅运营可见"——是不是浪费数据？

**Spec 现状**：Q11 决策"中国同行只展示给运营"。

**反思**：
- 同行公司是高价值数据：租户的产品如果是 PCB，知道哪些中国 PCB 厂商在出口、出口给谁，这是直接的市场情报
- 隐藏给租户后，租户感知"反推采集"只是一个产出海外买家的黑盒
- 运营自己消化这些数据的能力有限（运营是平台员工，不是 PCB 专家）

**反问**：为什么不展示给租户？理由是什么？
- 担心租户互相竞争？同租户群体反正都是 PCB 厂，竞争不可避免
- 担心数据敏感性？励销云本来就是公开企业信息聚合
- 担心 UI 复杂？这是产品设计问题，可解

**建议**：Spec 第 7 节"后续待确认"加一项明确：**「同行展示策略」需要在 Phase 2 重新评审**。Phase 1 不做反推所以暂时不冲突，但 Phase 2 上线前应当重新评估。

---

## 二、Eng 视角：架构与边界

### 2.1 数据写竞争

#### 🔴 多 worker 并发同时跑同一 task 的写竞争

**Spec 现状**：3.3 描述 lease 续期 + 心跳，但没说**多 worker 不会同时持有同一 task 的 lease**。

**场景**：
- Worker A claim 了 task X，跑了 100 分钟，连续多次心跳成功
- Worker A 网络抖动，5 分钟没心跳成功
- `recover_expired_tasks` 把 task X 回收，pending 状态
- Worker B claim 了 task X
- Worker A 网络恢复，继续跑（**它不知道 lease 已被回收**），开始往 DB 写公司数据

**问题**：Worker A 和 Worker B 同时写同一 task 关联的关键词进度（`current_page`、`today_pages`），最终状态不可预测。

**当前代码处置**：`_assert_task_lease()` 会检查 `lease_id` 匹配，Worker A 续期心跳时会失败。但是**写公司数据的 SQL 没有 lease 校验**——A 仍然可能往 `shared_companies` 写。

**建议**：
1. Spec 第 3.3 节加一条：**所有写入操作（heartbeat、submit_partial、write_company）都必须带 lease_id 校验**，DB 层 `WHERE lease_id = :lease_id` 守护
2. Worker A 在每次写入前检查 `cancellation_token`（lease 失效后置位），尽早退出
3. 或者更激进：放弃 task lease 模型，**关键词进度才是真源**——worker 只是「短租」拉一段 SEARCH 页码，写完就放回；下次另一个 worker 接着拉。这避免了长 lease 的所有问题。

#### 🟡 关键词进度的事务边界

**场景**：Worker 跑 Page 5 的 100 家公司，写完 50 家后崩了。

- 已写的 50 家在 DB 里
- `current_page` 没更新（还是 4）
- 下次 worker 续跑会重写 Page 5（因为 current_page=4，下一页是 5）

**结果**：50 家公司在 `shared_companies` 通过 `(source_type, source_id)` UNIQUE 自然去重（OK）；但**联系人有可能重复插入**（`shared_contacts` 的去重是 `(company_id, email)`，OK 也能去重）。

**结论**：现有去重键能兜住，但需要 Spec 显式说明：**page 级别的写入不需要事务，靠 UNIQUE 去重保证幂等**。

### 2.2 多租户共享时序

#### 🔴 关键词在采集中被租户删除/修改怎么办？

**Spec 未覆盖场景**：
- 租户 A 配置关键词「PCB」→ 调度器建 task → Worker 跑到一半
- 租户 A 在 tenant 端删除关键词「PCB」
- 此时 `collection_task_keywords` 中 (task_id, A_keyword_id) 关联还在吗？
- Worker 跑完 submit_result 时，要把结果给 A 吗？

**建议**：Spec 第 2.3 节加一条**关键词软删除规则**：
- 关键词只软删除（status=archived），不物理删
- archived 关键词的进度字段保留，但下次启动不会再被选中
- 跑了一半的 task 不会因为关键词 archived 而中断（已花的 API 调用不能浪费）

#### 🟡 租户被禁用时的关联

**场景**：租户 A 禁用，`collection_task_keywords(A_id, ...)` 还在。Worker 跑完写 `tenant_companies` 时，能写给 A 吗？

**建议**：`submit_result` 时跳过 inactive tenant，不写 `tenant_companies`，但 `shared_companies` 仍然写（数据复用）。

### 2.3 跨数据源数据合并

#### 🟡 同一家海外买家被两条路径采到

**场景**（Phase 2）：
- 外贸通直采路径：关键词「PCB」搜出 ABC GmbH（source_type=waimao_tong, source_id=abc123）
- 反推-腾道路径：同行 X 的海外买家也是 ABC GmbH（source_type=tengdao, source_id=t-456）
- domain 都是 `abc.de`

**当前代码逻辑**（`_upsert_company`）：先按 `(source_type, source_id)` 找，找不到再按 `lower(domain)` 找——会成功合并到同一个 `shared_company`，加一条 `company_sources` 记录。✅

**Spec 待补**：Spec 第 5.3 节"数据正确性"应当显式包含「跨数据源 domain 合并」用例的验收。

#### 🔴 `is_precise_customer` 的合并语义不一致

**Spec 第 2.6**：反推路径产物 = 精准客户（marker='precise'），直采路径 = normal。

**场景**：同一家公司，先被外贸通直采采到（normal），后被反推-腾道采到（precise）。`tenant_companies` 该是什么状态？

**当前代码**（`submit_result`）的处理：
```sql
is_precise_customer = tenant_companies.is_precise_customer OR excluded.is_precise_customer
```
单调上升（一旦 precise 永远 precise），✅ 但 `source_marker` 没有相应的合并逻辑（看代码会被覆盖）。

**建议**：Spec 第 2.6 节明确**升级单调性**：normal → precise 单向，precise 不会被 normal 覆盖。`source_marker` 字段加 CHECK 或专门的 update 逻辑。

### 2.4 长任务（200 分钟）的分片可能性

#### 🟡 Spec 选了"单 task 跑 200 分钟" vs "拆成多 task"

**Spec 现状**：3.3 节描述 single task ~200 分钟，靠心跳维持 lease。

**潜在问题**：
- 单 worker 实例必须 200 分钟内不重启 / 不部署（否则 task 中断）
- task lease 续期失败 1 次 → recover_expired_tasks 回收 → 写竞争风险（见 2.1）

**替代方案**：把单关键词的工作切成「页级 task」：
- task X1: page 1 of keyword PCB
- task X2: page 2 of keyword PCB（依赖 X1 完成）
- 或者无依赖，多 page 并发拉

**取舍**：
- 单 task：实现简单，恢复语义清晰（崩了就回收重跑）
- 页级 task：worker 部署友好，但 RPM 全局限流的协调更复杂（多 task 同时跑要协调一个共享令牌桶）

**建议**：Spec 加一段「设计选择记录」：明确选「单 task 长跑」+ 解释依据（实现简单 + 当前 worker 单实例够用）。如果未来 worker 横向扩展会改成页级。

### 2.5 测试可行性

#### 🔴 端到端测试需要真实凭证 + 真实 API + 跨 2 天

**Spec 5.2**: "真实凭证跑一个真实关键词，至少跨 2 天验证跨天恢复"。

**问题**：
- 不能在 CI 跑（外贸通 ToS、凭证敏感）
- 跨 2 天周期太长，无法快速 iterate
- 真实 API 不稳定（限流、ban、改版）会污染测试结果

**建议**：Spec 5.2 拆为两层：
1. **核心逻辑用 mock**：跨天恢复、limit 切换、限流 paused、凭证失效，全部用 mock 时间和 mock HTTP 测
2. **真实 API 烟雾测**：单独的 staging 任务（手动触发），不在标准 CI 里。每次部署前跑一次，文档化结果

写到 Spec 里，避免误把"必须真实 API"作为验收阻塞。

### 2.6 缺失的 Schema 决策

#### 🔴 Spec 3.5 列了"预期 migration"但没给字段最终形态

当前 Spec 只是列了「需要改」，但没定 schema：
- `collection_keywords.source_types` 移除 vs 保留
- `current_page` `today_pages` `last_run_date` `status` 等字段类型
- Phase 2 的 `stage1_today_count` 等字段

**建议**：Spec 第 8.1 节（Phase 1 范围）加一个「Schema 增量」子节，把 Phase 1 必须的字段列清楚（即使没到表设计深度，也要说"哪些字段要加，哪些字段要弃用"）。Phase 2 的字段可以不出现，避免污染 Phase 1 实施。

---

## 三、修订建议清单

| 优先级 | 章节 | 修订 |
|---|---|---|
| 🔴 P0 | 第 1 节 / Q1 | 重新审视"完全手动"决策。建议改为"定时为主 + 手动加急" |
| 🔴 P0 | 第 8 节 | 加调研项「确认腾道开放 API 可用性与成本」，决定是否能让 Phase 1 包含反推-腾道 |
| 🔴 P0 | 第 4 节 / Q13 | 「关键词重新采集」改为「Phase 1 支持运营手动重置 keyword 到 pending」 |
| 🔴 P0 | 第 3.3 节 | 加「写入操作必须 lease_id 守护」原则；明确 worker crash 恢复语义 |
| 🟡 P1 | 第 2.3 节 | 加「关键词软删除规则」+ 跑中删除处理 |
| 🟡 P1 | 第 2.6 节 | 加「is_precise_customer 升级单调性」+ source_marker 合并语义 |
| 🟡 P1 | 第 5.2 节 | 拆「mock 测试」 vs 「真实 API 烟雾测」两层 |
| 🟡 P1 | 第 8.1 节 | 加「Phase 1 Schema 增量」子节，列明字段 |
| 🟢 P2 | 第 7 节 | 加「同行展示策略」Phase 2 评审项 |
| 🟢 P2 | 第 4 节 / Non-goals | 加注：「不做租户自带凭证」是产品决策，schema 设计要留扩展位 |

---

## 四、CEO 视角总结

> Spec 在产品定义层面**结构完整**（5 个标准章节齐备）+ **决策有据**（17 项决策回溯清晰）。但有 3 个 6-月后悔点要在落实施前重审：
>
> 1. **手动启动是不是真需求**——运营要的是"能控"不是"必须点"
> 2. **Phase 1 商业价值薄**——只跑外贸通直采，差异化弱；建议争取把反推-腾道带进 Phase 1
> 3. **凭证集中托管的天花板**——schema 留扩展位，避免后期商业化阻塞
>
> 这三点不阻塞 Spec 落地，但应在进入 Phase 1 实施前给出明确答复（修订或确认）。

## 五、Eng 视角总结

> 架构主线合理（沿用 CollectionService + Worker + Internal API）。但有 4 个边界场景在 Spec 里被忽略，会在实施时反扑：
>
> 1. **写竞争**：长 lease + 多 worker 模型下，需要在 Spec 显式约束「lease_id 守护」
> 2. **关键词软删除**：跑中删除/禁用的处理路径要在 Spec 里写清
> 3. **跨数据源合并**：is_precise_customer 单调性、source_marker 合并语义要明确
> 4. **测试可行性**：真实 API 测试不能进 CI，要在 Spec 里区分 mock 测和烟雾测
>
> 这 4 点在 Phase 1 之前必须修。否则 Phase 2 上线时会成为 P0 故障。
