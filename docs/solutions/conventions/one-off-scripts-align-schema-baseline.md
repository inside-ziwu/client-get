---
title: 一次性脚本的 SQL 必须对照 schema.sql 基线写,禁止凭记忆
date: 2026-07-03
category: conventions
module: backend_scripts
problem_type: convention
component: database
severity: medium
applies_when:
  - "编写 backend/scripts/ 下的初始化、修复、回填类脚本"
  - "脚本中手写 INSERT/UPDATE 列清单"
tags: [schema-baseline, init-script, undefined-column, dry-run]
---

# 一次性脚本的 SQL 必须对照 schema.sql 基线写,禁止凭记忆

## Context

`init_instance.py` 在生产执行到第 6 步报 `UndefinedColumn: column "model_type" of relation "ai_models" does not exist`。脚本按记忆中的旧表结构写了 `model_type`/`input_price`/`output_price`/`fallback_model_ids` 四个列——而 `backend/03_database/schema.sql` 基线里**明确注释着**这些列"已由 0011/0013 迁移删除"。答案一直躺在基线文件里,只是写脚本时没看。

## Guidance

- 写任何手写列清单的脚本 SQL 前,先打开 `backend/03_database/schema.sql` 对照目标表的**当前**定义(该文件与迁移同步维护,且保留"列 X 已由迁移 NNNN 删除"的历史注释,是单一真源);
- 发布前用**开发库做全流程预演**:开发库与生产同在迁移链头,结构完全一致——本次修复后用临时 instance_id 在 dev 完整跑通 7/7 步并清理,生产一次通过;
- 幂等设计(ON CONFLICT DO NOTHING / 可重跑)+ 单事务,让"生产首跑失败"的代价降为零残留重来。

## Why This Matters

"记忆中的表结构"是所有手写 SQL 的头号事故源:表结构随迁移演进,而记忆停留在写下它的那天。schema.sql 基线 + dev 预演两道闸,把这类错误拦在生产之前;本次事故虽然靠单事务回滚做到了零残留,但多付了一轮"修脚本→出镜像→重部署"的周期。

## When to Apply

所有 `backend/scripts/` 新脚本;修改既有脚本涉及列清单时同样适用。评分/邮件等核心表尤其注意——它们的列变更最频繁。

## Examples

事故版(凭记忆):`INSERT INTO ai_models (id, provider, model_id, display_name, model_type, input_price, output_price, ...)`
修复版(对照基线):`INSERT INTO ai_models (id, provider, model_id, display_name, is_active, config, instance_id)`
基线里的提示原文:`-- model_type 已由 0013 删除;input_price / output_price 已由 0011 删除`
