---
title: "Neon 连接池端点拒绝 startup options 会话参数，只读会话改用 psycopg read_only 属性"
date: 2026-07-23
category: database-issues
module: db-connection
problem_type: database_issue
component: database
severity: medium
symptoms:
  - "psycopg.OperationalError: unsupported startup parameter in options: default_transaction_read_only"
  - "同一段代码连 Sealos 直连 PG 正常，连 Neon 开发库报错"
---

## 现象

用 `psycopg.connect(url, options="-c default_transaction_read_only=on")` 建立强制只读会话：连生产（Sealos，直连 PG）正常；连 Neon 开发库立即失败：

```
connection failed: ERROR: unsupported startup parameter in options: default_transaction_read_only.
Please use unpooled connection or remove this parameter from the startup package.
```

## 根因

Neon 默认连接串指向 **pooler 端点**（pgBouncer 类代理），代理不透传 startup packet 里的自定义 `options` 参数。任何经 `options` 下发的会话级 GUC 都会被拒；直连端点才支持。

## 解法

不用 startup options，改用 psycopg 3 的连接属性——效果等价（之后所有事务以 `BEGIN READ ONLY` 开启，写操作被 PostgreSQL 拒绝），且 pooled/直连两种端点通吃：

```python
conn = psycopg.connect(url, connect_timeout=15)
conn.read_only = True
# 双保险校验
cur.execute("SHOW transaction_read_only")  # 应为 'on'
```

现役实现参照 `backend/scripts/schema_snapshot.py`。

## 教训

- 写「双环境（Neon 开发 / Sealos 生产）都要跑」的数据库工具时，会话参数一律走连接属性或连接后 `SET`，不要依赖 startup options；
- 只读防护要带二次校验（`SHOW transaction_read_only`），不能只信连接侧声明。
