---
title: 采集独立运行单元改造实施计划
date: 2026-04-22
status: active
origin: docs/superpowers/specs/2026-04-22-collection-independent-deployment-design.md
---

## 问题框定

当前采集链路已有任务调度、internal collection 合同与结果回写逻辑，但缺少正式常驻运行单元与失败恢复机制，导致采集无法像评分、发送一样作为独立部署单元进入 Compose 与 Sealos 发布面。

本计划只解决“采集成为独立运行单元”这一目标，不扩展为独立微服务拆分。

## 范围

包含：

- 补齐采集任务失败回写与 lease 过期回收
- 新增 `collection-scheduler` 守护入口
- 新增 `collection-worker` 守护入口
- 新增 provider adapter 骨架
- 更新 Compose / Sealos / README / 部署文档
- 补自动化测试与本地后端回归

不包含：

- 独立仓库或独立数据库
- 前端页面或对外 API 变化
- provider 业务质量优化
- 真实外部采集源的完整生产接入

## 实施决策

1. `collection-worker` 直接复用 `CollectionService`，而不是通过 HTTP 再调本仓 internal API。
原因：
   - 当前 `scoring-worker` 与 `sending-worker` 都是同镜像、同代码库、直接调用 service 层
   - 目标是独立运行单元，不是独立微服务
   - 直接走 service 层可以减少新的 internal auth、HTTP base URL、网络故障面

2. 保留并扩展 internal collection API。
原因：
   - 现有合同已经是稳定边界
   - 后续如果真拆独立服务，可以继续复用
   - 本次新增 `mark-failed`，但不破坏既有接口路径与语义

3. 失败恢复由 service 层统一承接。
原因：
   - 任务状态机必须单点收敛
   - 避免 worker 直接拼 SQL 导致规则漂移

## 实现单元

### 1. 采集状态机与接口扩展

目标文件：

- `backend/app/services/collection_service.py`
- `backend/app/api/internal/collection.py`
- `backend/app/schemas/internal_collection.py`

改动：

- 新增 `mark_failed(...)`
- 新增 `recover_expired_tasks(...)`
- 为 `claim_tasks(...)` 增加“先回收过期 running 任务”的能力
- 新增 `POST /internal/api/v1/collection/tasks/{task_id}/mark-failed`

测试：

- `backend/tests/test_collection_internal_api.py`

关键场景：

- 正确 lease 可标记失败
- 可重试任务回退为 `pending`
- 达到 `max_attempts` 的任务进入 `failed`
- 过期 lease 的 running 任务能回收

### 2. 调度守护入口

目标文件：

- `backend/scripts/run_collection_scheduler_worker.py`

复用文件：

- `backend/app/services/collection_scheduler_service.py`

改动：

- 新增 `--once`
- 新增守护循环
- 每轮先执行过期任务回收，再调度新任务

测试：

- 新增 `backend/tests/test_collection_scheduler_worker.py`

关键场景：

- `--once` 正常输出
- 无任务时返回空结果
- 有过期 running 任务时先回收再继续调度

### 3. 采集 worker 与 provider adapter 骨架

目标文件：

- `backend/app/workers/collection.py`
- `backend/scripts/run_collection_worker.py`
- `backend/app/integrations/collection/base.py`
- `backend/app/integrations/collection/router.py`
- `backend/app/integrations/collection/waimaotong.py`

改动：

- 新增 `CollectionWorker.run_once(...)`
- claim 后按 `source_types` 路由 provider
- provider 异常时走 `mark_failed(...)`
- 先落 provider adapter 骨架与一个占位实现

测试：

- 新增 `backend/tests/test_collection_worker.py`

关键场景：

- claim 成功并提交结果
- provider 抛错触发 `mark_failed`
- 无任务时返回空列表

### 4. 配置与部署文档

目标文件：

- `backend/app/core/config.py`
- `backend/.env.example`
- `backend/docker-compose.prod.yml`
- `backend/README.md`
- `backend/docs/DEPLOYMENT.md`
- `backend/docs/LAUNCH_CHECKLIST.md`
- `backend/docs/ROLLBACK.md`
- `backend/docs/SEALOS_DEPLOYMENT.md`

改动：

- 增加采集相关配置项
- 增加 `collection-scheduler` 与 `collection-worker` 两个部署单元
- 更新 Sealos 应用清单与启动命令

测试：

- 文档一致性人工检查

### 5. 回归

执行：

- `cd backend && uv run pytest -q`
- 必要时针对新增测试单跑

成功标准：

- 采集相关测试通过
- 现有 collection / scoring / sending 测试不回归
- worker 入口脚本可执行

## 顺序与依赖

1. 先实现 `collection_service` 状态机扩展
2. 再补 internal schema 与 API
3. 再写 scheduler worker
4. 再写 collection worker 与 adapter 骨架
5. 最后补 compose / 文档 / 测试

## 风险

- 现有 `collection_tasks` 状态机虽支持 `failed`，但此前没有成体系地使用，需要测试兜底
- provider adapter 这次只会做骨架，真实外呼依赖后续接入
- 根目录不是 git 仓库，本次无法在该目录做计划 commit

