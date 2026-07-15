---
title: "PostgreSQL 归档恢复必须同主版本并补齐扩展与外部依赖"
date: 2026-07-14
category: database-issues
module: backup-restore
problem_type: database_issue
component: database
severity: high
symptoms:
  - "PG16 pg_restore 报 unsupported version (1.16)"
  - "按表恢复时报 type public.citext does not exist"
  - "分段 pg_restore 成功但上游 age 返回 SIGPIPE 141"
root_cause: environment_mismatch
resolution_type: workflow
tags: [postgresql, pg-dump, pg-restore, age, citext, backup, migration]
---

# PostgreSQL 归档恢复必须同主版本并补齐扩展与外部依赖

## Problem

T-21 Phase B 对生产 PG16 的退役表做 custom archive 备份时，本机默认 `pg_dump` 为18.4。归档可以由 PG18 `pg_restore --list` 读取，但 PG16.14 报 `unsupported version (1.16)`，无法作为生产同版本恢复依据。

改用 PG16 `pg_dump` 后，按表恢复的 pre-data 又因空白库没有 `citext` 而失败；即使目标表都在归档中，表外引用的父表与 `trigger_set_updated_at()` 也不会由 `--table` 自动带入。

## Solution

1. **备份和恢复工具与生产保持同一 PostgreSQL 主版本。** 可使用 `postgres:16` 容器内的 `pg_dump/pg_restore`，不要依赖本机最新客户端。
2. custom archive 直接通过 stdout 流式送入 age，加密文件落盘，禁止先生成明文 dump。
3. 恢复前先安装目标表使用的扩展；本次为：

   ```sql
   CREATE EXTENSION citext;
   ```

4. 分三段恢复：pre-data → data → post-data。data 与 post-data 之间，根据真实 FK 图建立最小父表桩并补齐被引用主键，同时创建触发器依赖函数。
5. 分段 `pg_restore` 可能读取完目标 section 后提前关闭 stdin，使 age 收到 SIGPIPE 141。只有 `age=141` 且 `pg_restore=0` 才可判定该段成功；任何其他组合均失败。
6. 恢复后必须对账：逐表行数、约束 `convalidated`、外键孤儿、序列水位、用户触发器，并记录归档 SHA-256。

## Why This Works

- custom archive 格式会随新版本演进，较老 `pg_restore` 不保证读取较新 `pg_dump` 的归档。
- `pg_dump --table` 只保证匹配对象本身，不会递归包含扩展、函数或被引用父表。
- 先恢复数据、再补父键、最后建立 FK，可以在不复制全部生产父表数据的前提下验证目标表可完整恢复。
- 数字对账同时证明“密文可解”“结构可建”“数据可载入”“依赖可重建”，比只跑 `pg_restore --list` 更接近真实恢复能力。

## Prevention

- 备份脚本启动时同时输出 server、pg_dump、pg_restore 主版本，主版本不一致直接失败。
- 恢复脚本使用 `set -euo pipefail`，并单独处理分段解密的 SIGPIPE 状态。
- 在删除生产表前，把加密归档、校验值、恢复对账和销毁日期作为审批门禁。
