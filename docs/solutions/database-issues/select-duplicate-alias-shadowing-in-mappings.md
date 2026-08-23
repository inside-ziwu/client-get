---
title: JOIN SELECT 同名别名遮蔽——.mappings() 静默取后者，字段错值可潜伏数月
date: 2026-07-23
category: database-issues
module: backend_services
problem_type: silent_bug
component: sqlalchemy
severity: high
applies_when:
  - "JOIN 查询中给列起别名，且别名可能与另一张表的输出列同名"
  - "序列化层通过 row[\"...\"] 按键名取值"
tags: [sqlalchemy, mappings, alias, join, silent-failure]
---

# JOIN SELECT 同名别名遮蔽——.mappings() 静默取后者，字段错值可潜伏数月

## Context

情报文章查询里 `SELECT p.created_at AS published_at, ..., a.published_at`——发布记录时间的别名与文章表自有列同名。PostgreSQL 允许结果集含重复列名（不报错），SQLAlchemy `.mappings()` 转 dict 时**后出现的列静默覆盖先出现的**。结果 `published_to_tenant_at`（推送给租户时间，序列化取 `row["published_at"]`）自 2026-05-16 monorepo 合并起恒等于文章原始发布时间，从未正确过——两字段恒同值，前端无消费方，潜伏两个多月（PR #89 修复）。

## Guidance

1. **别名直接用最终序列化字段名**：`p.created_at AS published_to_tenant_at`，序列化 `row["published_to_tenant_at"]`——别名即语义，消除中间映射层，撞名概率归零。
2. **写 JOIN SELECT 时逐列自查别名与所有参与表的输出列是否撞名**；尤其 `created_at/updated_at/status/id` 这类几乎每表都有的列，起别名时必须带前缀语义（如 `article_created_at`、`publication_status`——同一条 SQL 里这两个就是做对了的先例）。
3. **防回归测试两件套**：序列化单测给两个键不同值、断言各取各的；`inspect.getsource` 断言 SQL 不再含撞名别名（见 `backend/tests/test_intelligence_article_serialization.py`）。

## Why This Matters

这类 bug 无异常、无报错、返回结构完整，仅值错；当错值恰与另一字段相同时，肉眼与常规测试都难发现。mock 测试断言的是「SQL 文本 + 映射逻辑」，而遮蔽发生在真实驱动的结果集层——恰是 mock 盲区。

## When to Apply

- 见 frontmatter `applies_when`；单表 SELECT 无此风险。

## Related

- PR #89（修复与防回归测试）
- `.trellis/spec/backend/quality-guidelines.md（真库验证纪律）`（mock 盲区约定）
