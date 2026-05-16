# 采集独立运行单元改造设计

Created: 2026-04-22
Status: approved-in-chat

## 1. 问题定义

当前系统里的采集链路已经具备独立领域边界，但还没有成为正式部署单元。

现状包括：

- 任务调度脚本已存在：`backend/scripts/run_collection_scheduler.py`
- internal collection 合同已存在：`backend/app/api/internal/collection.py`
- 任务执行与结果入库逻辑已存在：`backend/app/services/collection_service.py`
- 测试已按服务身份 `collection-service` 模拟调用：`backend/tests/test_collection_internal_api.py`

但正式部署与运维口径中，采集没有像评分和发送那样成为独立常驻单元。当前发布单元仅包括：

- `postgres`
- `backend`
- `scoring-worker`
- `sending-worker`

这导致以下问题：

- 采集调度仍停留在“一次性脚本”层面，不属于正式守护进程
- 采集执行缺少标准 worker 入口，不便于 Sealos / Docker Compose 独立发布
- 部署文档、回滚文档、健康检查口径都没有把采集纳入正式运行面
- 架构上存在“半独立”状态，边界有了，运维单元没有拉直

## 2. 设计目标

本次改造的目标是把采集升级为独立运行单元，但不把它升级为独立微服务。

必须达成：

- 采集成为正式部署单元
- 调度与执行职责分离
- 采集执行仍通过现有 internal collection 合同回写结果
- 不改变 Admin / Tenant 前端合同
- 不改变现有 internal collection API 基本路径与语义
- 与 `scoring-worker`、`sending-worker` 保持一致的运维模型

明确不做：

- 不拆独立仓库
- 不拆独立数据库
- 不迁出 backend 持有的 internal API
- 不重写 provider 业务逻辑
- 不改前端页面或租户业务合同
- 不把这次改造扩展成采集系统重构

## 3. 目标拓扑

改造后，后端正式运行单元固定为 5 个：

1. `backend`
2. `collection-scheduler`
3. `collection-worker`
4. `scoring-worker`
5. `sending-worker`

其中：

- `backend` 继续提供外部 API、internal API、鉴权、统一入库规则
- `collection-scheduler` 周期性把 `collection_keywords` 聚合为 `collection_tasks`
- `collection-worker` 负责 claim 任务、调用采集 provider、heartbeat、submit-result
- `scoring-worker` 与 `sending-worker` 保持现状

部署层面，`collection-scheduler` 和 `collection-worker` 都是不对外暴露端口的后台守护进程。

## 4. 核心边界与职责

### 4.1 backend

职责：

- 保持 `backend/app/api/internal/collection.py` 作为采集任务合同入口
- 保持 `backend/app/services/collection_service.py` 作为统一结果回写与业务规则承载层
- 继续处理黑名单、幂等、租户映射、联系人入库、竞品入库等业务规则

约束：

- 不把结果入库逻辑下放到 `collection-worker`
- 不让 worker 直接绕过 internal API 写主业务表

### 4.2 collection-scheduler

职责：

- 周期性扫描 `collection_keywords`
- 合并相同 `keyword_normalized + countries_hash` 的租户关键词
- 生成或复用 `collection_tasks`
- 建立 `collection_task_keywords` 映射

依赖：

- `backend/app/services/collection_scheduler_service.py`

约束：

- 只负责生成任务
- 不负责真正执行采集
- 支持 `--once` 和守护模式

### 4.3 collection-worker

职责：

- 调用 `/internal/api/v1/collection/tasks/claim`
- 对已 claim 的任务发起采集
- 维持 lease heartbeat
- 调用 `/internal/api/v1/collection/tasks/{task_id}/submit-result`

依赖：

- 现有 internal collection 合同
- 新的 provider adapter 层

约束：

- 只做任务编排与 provider 调用
- 不承载业务写库规则
- 支持 `--once` 和守护模式

## 5. 接口与数据合同

本次改造不调整以下合同的路径和核心语义：

- `POST /internal/api/v1/collection/tasks/claim`
- `POST /internal/api/v1/collection/tasks/{task_id}/heartbeat`
- `POST /internal/api/v1/collection/tasks/{task_id}/submit-result`

为保证独立 worker 的可恢复性，本次允许新增一个失败回写合同：

- `POST /internal/api/v1/collection/tasks/{task_id}/mark-failed`

允许的增强只有：

- 更完整的结构化日志
- 更清晰的错误码映射
- 更详细的结果统计字段

不允许的变化：

- 不新增前端调用路径
- 不改变 payload 基本结构
- 不把 internal collection API 改成对外公开 API

服务身份继续沿用：

- `service_name = collection-service`
- scopes:
  - `collection:claim`
  - `collection:write`

## 6. 实现设计

### 6.1 新增调度守护脚本

新增：

- `backend/scripts/run_collection_scheduler_worker.py`

设计要求：

- 结构对齐 `backend/scripts/run_scoring_worker.py`
- 提供参数：
  - `--once`
  - `--sleep-seconds`
  - `--service-instance`
- 每轮调用 `CollectionSchedulerService.schedule_due_tasks`
- 打印结构化 JSON 结果
- 单轮失败不导致进程永久退出

保留：

- `backend/scripts/run_collection_scheduler.py`

用途：

- 作为一次性调试脚本继续保留
- 文档里明确标注它不是生产守护入口

### 6.2 新增采集 worker

新增：

- `backend/app/workers/collection.py`
- `backend/scripts/run_collection_worker.py`

`CollectionWorker` 主循环包含：

1. claim 任务
2. 根据任务的 `source_types` 选择 provider
3. 执行采集
4. 长任务期间发送 heartbeat
5. 汇总标准化 `companies / contacts / competitors`
6. submit-result

错误处理原则：

- provider 失败时不伪造成功结果
- lease 失效时立即中止本轮
- submit-result 失败时记录完整上下文，进入失败回写或等待 lease 回收

任务状态策略固定为：

- 成功提交结果：`completed`
- provider 显式失败：优先调用 `mark-failed`
- `attempt_count < max_attempts` 时，`mark-failed` 将任务回退为 `pending`
- `attempt_count >= max_attempts` 时，`mark-failed` 将任务置为 `failed`
- worker 异常退出或网络中断导致未显式回写时，依靠 lease 过期回收机制重新进入可调度状态或失败状态

### 6.3 新增 provider adapter 层

新增目录：

- `backend/app/integrations/collection/`

建议文件：

- `base.py`
- `router.py`
- `waimaotong.py`

统一接口由 adapter 层定义，worker 只消费标准化结果，不感知 provider 内部细节。

标准输出模型至少包括：

- `companies`
- `contacts`
- `competitors`

每个 provider adapter 的职责：

- 拉取外部凭证
- 调用第三方数据源
- 清洗并映射成内部标准结构
- 抛出统一异常类型

### 6.4 internal ops 复用策略

现有 `backend/app/services/internal_ops_service.py` 里已有部分 collection 相关批量写入辅助逻辑。

本次不新增第二套写库模型。

约束：

- 采集主链路仍以 `CollectionService.submit_result` 为主
- 如需抽公共能力，应提炼为共享方法，而不是让 worker 同时走两套不同的回写路径
- `mark-failed` 与 lease 回收逻辑也应收敛在 collection service 层，不放到 worker 自己直接写表

## 7. 配置设计

新增配置项建议：

- `COLLECTION_SCHEDULER_SLEEP_SECONDS`
- `COLLECTION_WORKER_SLEEP_SECONDS`
- `COLLECTION_TASK_LEASE_SECONDS`
- `COLLECTION_WORKER_LIMIT`
- `COLLECTION_HEARTBEAT_INTERVAL_SECONDS`

现有 provider 凭证体系继续复用：

- `data_source_credentials`

不新增新的 provider 凭证表，避免双轨配置。

## 8. 失败恢复设计

### 8.1 失败回写

新增 internal 失败回写能力：

- `POST /internal/api/v1/collection/tasks/{task_id}/mark-failed`

最小 payload 建议包含：

- `lease_id`
- `error_code`
- `error_message`
- `retryable`

行为规则：

- 仅允许持有有效 lease 的 worker 回写失败
- `retryable = true` 且 `attempt_count < max_attempts`：
  - 状态改回 `pending`
  - 清空 lease 字段
  - 保留 `error_message`
- 否则：
  - 状态改为 `failed`
  - 写入 `error_message`
  - 清空 lease 字段

### 8.2 lease 过期回收

必须新增“过期 running 任务回收”逻辑，否则 worker 崩溃会留下永远不可 claim 的任务。

回收逻辑建议收敛在 `CollectionService` 或专用 maintenance 方法中，由 `collection-scheduler` 每轮先执行：

- 找到 `status = 'running' AND lease_expires_at <= now()` 的任务
- 若 `attempt_count < max_attempts`：
  - 回退为 `pending`
  - 清空 lease 字段
- 若 `attempt_count >= max_attempts`：
  - 置为 `failed`
  - 写入超时错误信息

这样可保证：

- worker 显式失败时有同步回写路径
- worker 非正常退出时有异步兜底回收路径

## 9. 部署设计

### 9.1 Docker Compose

`backend/docker-compose.prod.yml` 新增：

- `collection-scheduler`
- `collection-worker`

两个服务都：

- 复用 backend 镜像
- 复用运行时环境变量
- 不暴露公网端口
- `restart: unless-stopped`

推荐启动命令：

- `collection-scheduler`
  - `python scripts/run_collection_scheduler_worker.py --sleep-seconds 30`
- `collection-worker`
  - `python scripts/run_collection_worker.py --sleep-seconds 10`

### 9.2 Sealos

新增应用：

- `clientget-collection-scheduler`
- `clientget-collection-worker`

两者都：

- 复用 `clientget-backend` 镜像
- 不开公网访问
- 使用与 backend 相同的数据库和密钥环境变量

### 9.3 文档更新范围

必须同步更新：

- `backend/README.md`
- `backend/docs/DEPLOYMENT.md`
- `backend/docs/LAUNCH_CHECKLIST.md`
- `backend/docs/ROLLBACK.md`
- `backend/docs/SEALOS_DEPLOYMENT.md`

## 10. 可观测性设计

本次以结构化日志为主，不引入新的监控系统。

每轮调度日志建议包含：

- `service`
- `service_instance`
- `scheduled_count`
- `items_count`
- `duration_ms`

每轮采集日志建议包含：

- `task_id`
- `lease_id`
- `service_instance`
- `source_types`
- `companies_count`
- `contacts_count`
- `competitors_count`
- `duration_ms`
- `provider_error_code`

错误日志必须能定位：

- claim 失败
- heartbeat 失败
- provider 调用失败
- submit-result 失败
- mark-failed 失败
- lease 超时回收

## 11. 测试设计

新增自动化测试应覆盖：

### 11.1 调度守护脚本

- `--once` 正常执行
- 无任务时返回空结果
- 已存在 `pending/running` 任务时不重复创建

### 11.2 collection-worker

- claim 成功后正常执行 submit-result
- 长任务期间 heartbeat 正常续租
- provider 抛错时结果不伪造成功
- lease 失效时中止提交
- provider 失败时正确调用 `mark-failed`
- 达到 `max_attempts` 后任务进入 `failed`

### 11.3 provider adapter

- provider 输出能映射为标准结构
- provider 异常能映射为统一错误

### 11.4 部署 smoke

- compose 启动后可见：
  - `backend`
  - `collection-scheduler`
  - `collection-worker`
  - `scoring-worker`
  - `sending-worker`
- Sealos 中可独立拉起两个采集应用

### 11.5 失败恢复与回收

- `running + lease 过期` 任务能在下一轮被回收
- 回收后任务要么重新变成 `pending`，要么进入 `failed`
- 不允许出现长期滞留在 `running` 但无人持有 lease 的任务

## 12. 发布与回滚

发布顺序：

1. 先发布 backend
2. 再发布 `collection-scheduler`
3. 再发布 `collection-worker`
4. 最后做联调 smoke

回滚原则：

- 优先回滚 `collection-scheduler` / `collection-worker` 版本
- backend 仅在 internal collection 合同或 `CollectionService` 回归时回滚
- 不涉及数据库 schema 破坏性变更时，不做数据库回滚

## 13. 风险与约束

主要风险：

- provider 调用链路仍然是当前最大不确定项
- heartbeat 策略不合理会导致长任务 lease 失效
- submit-result 若失败，需要明确重试与告警策略

已接受的约束：

- 本次不是独立微服务拆分
- backend 仍然是唯一真写入入口
- provider 质量问题不在本次改造范围内解决

## 14. 方案审查结论

本方案自审结论为：通过。

通过理由：

- 目标聚焦，只解决“采集成为独立运行单元”这一件事
- 运行形态与评分、发送保持一致，运维模型统一
- 现有 internal collection 合同与业务写入规则被复用，回归风险可控
- 不引入新的前端合同与跨服务数据一致性问题

本方案被拒绝的备选方向包括：

- 继续保持采集只靠手动脚本运行
- 让 collection-worker 直接写业务表
- 现在就拆成独立仓、独立数据库、独立微服务

以上备选方向在当前阶段都不符合收益/风险比。
