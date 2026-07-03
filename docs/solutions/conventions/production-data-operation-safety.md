---
title: 生产数据操作安全模式:只读摸图 → 单事务 → 回读对账
date: 2026-07-03
category: conventions
module: database_operations
problem_type: convention
component: database
severity: critical
applies_when:
  - "对生产库做任何写操作(数据同步、批量修正、清理、重算)"
tags: [production, data-operations, transaction, reconciliation, foreign-keys]
---

# 生产数据操作安全模式:只读摸图 → 单事务 → 回读对账

## Context

多实例上线当天在生产库连续执行了四类数据操作(预热档位 A→B 同步、平台配置复制、3.4 万公司评分全量重算、测试数据全链清理),零事故。共性做法值得固化为约定。

## Guidance

三段式,一段都不能省:

**1. 只读摸图(动手前)**

- 自省列名而不是猜:`information_schema.columns`(本次踩过 `tenant_domains`/`role`/`clean_company_id` 三次"想当然"的列名);
- 查外键图定删除/替换顺序:`pg_constraint WHERE confrelid='<表>'::regclass AND contype='f'`(清理测试数据时靠它发现了 `email_send_locks` 这层隐藏引用);
- 查引用计数定共享风险:删全局池数据前确认"无其他租户引用"。

**2. 单事务执行**

- 整个操作包在一个事务里,任何一步失败整体回滚(init 脚本第 6 步失败但零残留,靠的就是这一条);
- 被引用的行**停用(is_active=false)而不是删除**;必须重建的用"删子表→删父表→按映射重插"并维护 id 映射;
- 大批量写用分批事务(如每 1000 行一批)+ 幂等设计,可安全重跑;
- 一次性脚本进仓库时:默认 dry-run + 环境变量二重确认(参照 `backend/scripts/rescore_system_scores.py`、`init_instance.py`)。

**3. 回读对账(动手后)**

- 不要只看 UPDATE/DELETE 返回行数,重新 SELECT 验证终态;
- 有分布的做分布对账:重算后的等级分布必须与迁移矩阵逐项相加吻合(A 36=21+15、B 8522=8227+295);
- 抽查一条真实记录的具体值(如"精准反推 A 级公司 76 分 ≥ 阈值 70")。

## Why This Matters

生产库没有"撤销"。摸图消灭"想当然"(列名、外键、共享引用是三大想当然重灾区);单事务把失败变成无事发生;对账把"我以为成功"变成"数字证明成功"。三段的成本合计几分钟,任何一段省掉的事故成本都以小时计。

## When to Apply

所有生产写操作,无论多小——今天最小的一次操作(勾一个字段)和最大的一次(重算 34,473 行)用的是同一套流程。

## Examples

对账实例(评分重算):dry-run 输出迁移矩阵 → 执行 → `GROUP BY system_grade` 回读 → 每个等级的新计数 = 矩阵对应行之和 → 抽查单条。四步都留在 openspec 归档记录里可复核。
