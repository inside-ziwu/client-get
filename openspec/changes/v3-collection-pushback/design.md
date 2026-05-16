# Design · v3-collection-pushback

> **2026-05-08 迁移说明**：本文件中的 `keyword_master / tenant_keyword / collection_run / collection_task` 基础数据模型已迁入归档 change [`../archive/2026-05-09-v3-data-foundation/design.md`](../archive/2026-05-09-v3-data-foundation/design.md) §2.0，那里是 schema 真源。本文件保留运行语义、状态机、worker 行为和前端展示规则，供 collection-pushback 实施引用。

## 1. 核心结论

admin 关键词页管理的是**全平台关键词采集任务**，不是 tenant 私有关键词任务。

tenant 是订阅者。tenant 新增一个别人已经添加过的关键词时，只增加订阅关系，不创建、不重启、不停止、不改变该关键词的采集状态。

```
keyword_master
  = 全平台唯一关键词，例如 "PCB" / "线路板"

tenant_keyword
  = tenant 订阅关系

collection_run
  = 这个关键词的一轮持续采集，跨天存在

collection_task
  = 某一天某一批实际执行任务
```

关系：

```text
keyword_master
      │
      ├── tenant_keyword × N
      │
      └── collection_run × N
              │
              └── collection_task × N
```

## 2. 为什么必须有 collection_run

`collection_task` 只能表达一次执行：pending、running、completed、failed、cancelled。

但业务里存在一轮跨天持续采集：

- 今天采到励销云每日 1000 上限
- 今天停止执行
- 明天北京时间 08:00 继续
- 继续昨天的 cursor / page / skip_source_ids
- 直到励销云无更多数据，才算整轮采完

如果没有 `collection_run`，就会被迫让 `collection_task` 同时承担两种职责：

```text
错误混合：
collection_task
  ├── 单次 worker lease / retry
  ├── 跨天业务状态
  ├── admin 页面状态
  ├── cursor 续采位置
  └── 手动停止语义
```

这会导致状态显示、worker 重试、次日续采、停止取消互相污染。

正确分层：

```text
collection_run
  ├── admin 页面状态
  ├── 跨天 cursor / progress
  ├── 每日上限状态
  ├── 手动停止状态
  └── 是否采完

collection_task
  ├── 单次执行状态
  ├── lease / retry
  ├── scheduled_at
  ├── page_size
  └── 单批 result_summary
```

## 3. 数据模型引用

`keyword_master / tenant_keyword / collection_runs / collection_tasks` 的 schema 真源已迁入归档 change [`../archive/2026-05-09-v3-data-foundation/design.md`](../archive/2026-05-09-v3-data-foundation/design.md) §2.0。本 change 不再定义字段表，避免和 data-foundation 出现双真源。

本 change 只保留以下运行语义：

- `keyword_master`：全平台唯一关键词，归一规则由 data-foundation 定义
- `tenant_keyword`：tenant 与平台关键词的订阅关系
- `collection_runs`：关键词的一轮持续采集，承载跨天 cursor、每日上限、停止/完成状态
- `collection_tasks`：一次实际 worker 执行，归属某个 run

run 状态：

| 状态 | admin 显示 | 含义 |
| --- | --- | --- |
| not_started | 未开始 | 尚未启动 |
| running | 采集中 | 有当前或即将执行的 task |
| daily_limit_reached | 今日已达上限 | 今天已到 1000，等待次日 08:00 |
| completed | 已采完 | 励销云无更多数据 |
| stopped | 未开始 | admin 手动停止，次日不自动继续 |
| failed | 未开始/失败待定 | 非重试错误，前台可后续细化 |

本轮设计中，`stopped` 和 `not_started` 前台都显示"未开始"。

task 状态只描述单次执行，不直接等于 admin 页面状态。字段以 data-foundation §2.0.4 为准。

## 4. 状态机

### 4.1 run 状态机

```text
not_started
    │ admin 点采集
    ▼
running
    ├── 励销云无更多数据 ───────────────▶ completed
    ├── 今日达到 1000 ────────────────▶ daily_limit_reached
    ├── admin 点停止 ─────────────────▶ stopped
    └── 不可恢复错误 ─────────────────▶ failed

daily_limit_reached
    ├── 次日北京时间 08:00 scheduler 执行 continuation ─▶ running
    └── admin 点停止 ────────────────────────────────▶ stopped

stopped
    └── admin 再点采集 ───────────────────────────────▶ running
```

### 4.2 task 状态机

```text
pending
   │ worker claim
   ▼
running
   ├── 本批成功 ───────▶ completed
   ├── 可重试失败 ─────▶ pending
   ├── 不可重试失败 ───▶ failed
   └── admin 停止 ─────▶ cancelled
```

## 5. 达到每日上限

约束：

- 北京时间自然日
- 每个 keyword_master 每天最多采集励销云 1000 条
- 励销云单次请求最大 100
- 系统默认请求条数保持 10

达到 1000 后：

```text
1. 当前 collection_task.status = completed
2. collection_task.result_summary.reason = daily_limit_reached
3. collection_run.status = daily_limit_reached
4. collection_run.next_run_at = 次日北京时间 08:00
5. 创建下一条 collection_task:
     run_id = 当前 run
     status = pending
     scheduled_at = next_run_at
     cursor_snapshot = 当前 run.cursor
```

次日 scheduler：

```text
1. 找到 scheduled_at <= now 且 status=pending 的 continuation task
2. claim task
3. 用 task.cursor_snapshot / run.cursor 继续请求
4. 不从第一页重新采
5. 仍然最多补到当天 1000
```

## 6. 停止语义

admin 点"停止"表示停止整轮 run，而不是只停止当前 task。

必须一并取消：

- 当前 running task
- 未来 pending continuation task
- 已 scheduled 但未执行的同 run task

结果：

```text
collection_run.status = stopped
collection_run.manual_stopped_at = now()
collection_tasks where run_id = ? and status in ('pending', 'running')
  → cancelled
```

停止后：

- admin 显示"未开始"
- 次日不自动继续
- 必须 admin 再点"采集"才会重新启动

## 7. 采完语义

当励销云返回无更多数据：

```text
collection_task.status = completed
collection_task.result_summary.reason = no_more_data
collection_run.status = completed
collection_run.completed_at = now()
```

admin 显示"已采完"。

## 8. stage2 腾道暂时忽略

当前腾道 Cookie 会话会过期，并且用户已明确本轮先暂时忽略。

因此本 change 的闭环是：

```text
admin 启动关键词
  → collection_run
  → lixiaoyun collection_task(s)
  → lixiaoyun_raw_companies
  → 同行数据正确显示
```

不应因为腾道 stage2 失败，把 stage1 run 标成失败。

后续恢复腾道时，可以在同一个 run 模型下增加 provider/stage 维度，或独立 stage2 run。当前不展开。

## 9. Admin 页面状态与操作

| run 状态 | 前台显示 | 操作 |
| --- | --- | --- |
| not_started | 未开始 | 采集、历史 |
| stopped | 未开始 | 采集、历史 |
| running | 采集中 | 停止、历史 |
| daily_limit_reached | 今日已达上限 | 停止、历史 |
| completed | 已采完 | 历史 |

`failed` 的显示可后续单独定。本轮最小可行处理是显示"未开始"并在历史里展示错误。

## 10. Scheduler 职责

scheduler 不应该"重新发现关键词然后从头采"。

它只做两件事：

```text
1. claim 到点的 pending collection_task
2. 对 daily_limit_reached 且 next_run_at <= now 的 run，确保已有 pending continuation task
```

正常情况下，达到上限时已经生成了次日 pending task；scheduler 次日只负责执行。

## 11. 历史与审计

admin 点"历史"应围绕 run 展开：

```text
keyword_master
  └── collection_runs
        └── collection_tasks
```

这样能回答：

- 这轮什么时候开始？
- 哪天达到上限？
- 次日是否续采？
- 哪一批失败？
- 是手动停止还是采完？

## 12. 待实施时确认的轻量细节

- `today_fetched` 是写入 run，还是单独建 `collection_run_daily_usage` 表。
- `cursor` 具体字段由励销云 adapter 输出决定，最低要能表达 page/offset/last_seen/skip_source_ids。
- `failed` 前台是否单独显示"失败"，还是按当前约定先显示"未开始"并依赖历史。
