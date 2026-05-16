---
title: "SQLAlchemy asyncpg: 命名参数后紧跟 ::type 导致参数替换失败"
date: 2026-05-07
category: runtime-errors
module: cleanup-service
problem_type: runtime_error
component: background_job
severity: high
symptoms:
  - "asyncpg.exceptions.PostgresSyntaxError: syntax error at or near \":\" 在 INSERT 执行时"
  - "命名参数 :param::uuid 未被替换，原样保留在最终 SQL 中"
  - "同一语句中其他命名参数（:tenant_id、:keyword_json）正常替换为 $1/$2，唯独带 ::type 的参数被跳过"
root_cause: wrong_api
resolution_type: code_fix
related_components:
  - database
tags:
  - asyncpg
  - sqlalchemy
  - named-parameter
  - postgresql-cast
  - text-sql
  - upsert
  - cleanup-service
---

# SQLAlchemy asyncpg: 命名参数后紧跟 `::type` 导致参数替换失败

## Problem

在 `app/services/cleanup_service.py` 的 `_upsert_tenant_companies` 方法中，`sqlalchemy.text()` 内对 UUID 参数使用了 PostgreSQL 原生类型转换语法 `:clean_id::uuid`。SQLAlchemy 的 asyncpg dialect 在做命名参数替换时无法正确识别该参数边界，导致 `:clean_id` 未被替换为位置参数（`$n`），asyncpg 在执行阶段遭遇非法 `:` 字符并报错，整批 cleanup_queue 条目写入失败。

## Symptoms

**精确报错信息：**

```
asyncpg.exceptions.PostgresSyntaxError: syntax error at or near ":"
[SQL:
    INSERT INTO tenant_companies
      (id, tenant_id, clean_company_id, matched_keywords, ...)
    VALUES
      (gen_random_uuid(), $1, :clean_id::uuid,
       CAST($2 AS jsonb), 'pending_score', 'incomplete', false)
    ...
]
[parameters: ('019de1a0-c3a9-7585-81e7-4162d8f2b8bb', '["multilayer pcb"]')]
```

**可观察行为：**

- `:tenant_id` → `$1` ✓，`:keyword_json` → `$2` ✓，但 `:clean_id::uuid` 原样保留在 SQL 中。
- 错误只在运行时（asyncpg 执行阶段）触发，静态分析和 `--sql` dry-run 均不报警。
- cleanup worker smoke test 报 `WARNING: CleanupService: failed to process queue row 1`，`tenant_companies` 零写入。

## What Didn't Work

- **`--sql` dry-run**：在运行 `alembic upgrade head --sql` 时校验了迁移 SQL，但 dry-run 走的是 `MockConnection`，完全不经过 asyncpg 参数替换流程，无法暴露此问题。等到真实 worker 运行才报错。
- 此类错误不会在 SQLAlchemy ORM 层或同步 `psycopg2` driver 下复现（两者参数替换逻辑不同），在非 asyncpg 环境下测试不能发现它。

## Solution

**Before（Broken）：**

```python
await conn.execute(
    text("""
        INSERT INTO tenant_companies
          (id, tenant_id, clean_company_id, matched_keywords,
           business_status, data_status, is_precise_customer)
        VALUES
          (gen_random_uuid(), :tenant_id, :clean_id::uuid,   -- ❌
           CAST(:keyword_json AS jsonb),
           'pending_score', 'incomplete', false)
        ON CONFLICT (tenant_id, clean_company_id) DO UPDATE
        SET matched_keywords = (...),
            updated_at = now()
    """),
    {"tenant_id": tenant_id, "clean_id": clean_id, "keyword_json": ...},
)
```

**After（Fixed）：**

```python
await conn.execute(
    text("""
        INSERT INTO tenant_companies
          (id, tenant_id, clean_company_id, matched_keywords,
           business_status, data_status, is_precise_customer)
        VALUES
          (gen_random_uuid(), :tenant_id, CAST(:clean_id AS uuid),  -- ✅
           CAST(:keyword_json AS jsonb),
           'pending_score', 'incomplete', false)
        ON CONFLICT (tenant_id, clean_company_id) DO UPDATE
        SET matched_keywords = (...),
            updated_at = now()
    """),
    {"tenant_id": tenant_id, "clean_id": clean_id, "keyword_json": ...},
)
```

**同场附带修复：** 同文件存在重复的 `_process_batch` 方法定义——第一份签名缺少 `batch_size` 参数，第二份才是正确实现。Python 中后定义静默覆盖前者，删除了第一份不完整定义以消除混淆。

## Why This Works

SQLAlchemy 的 asyncpg dialect 在将 `text()` SQL 中的命名参数（`:param_name`）替换为 asyncpg 位置占位符（`$1`、`$2`…）时，会识别 `::` 为 PostgreSQL 类型转换操作符并做特殊处理。当 `:param_name` 紧跟 `::type` 时，dialect 跳过（或错误处理）该参数，导致其不进入替换队列。其余参数正常获得位置编号后，SQL 中仍残留字面量 `:clean_id::uuid`，asyncpg 发送给 PostgreSQL 时遭遇非法语法。

> 注：asyncpg dialect 内部的确切匹配机制有多种可能路径；以上为从错误行为逆推的观察描述，而非源码层的精确机制，保险起见以实测行为为准。

`CAST(:clean_id AS uuid)` 让命名参数 `:clean_id` 后面紧跟空格和字母 `A`，不含任何冒号序列，dialect 可以干净识别边界并正常替换为 `$n`。`CAST(expr AS type)` 是标准 SQL，与 `expr::type` 语义等价，PostgreSQL 完全支持。

## Prevention

1. **编码规则**：在 `sqlalchemy.text()` 内使用 asyncpg dialect 时，**禁止**对命名参数使用 `::type` 转换语法；有两种等价替代方式：

   - **SQL 侧**：`CAST(:param AS uuid)` — 最直接，对已有 `text()` SQL 改动最小。
   - **Python 侧（更惯用）**：将参数在 Python 层包装为正确类型再传入，SQLAlchemy 自动做类型映射，无需 SQL 内显式 CAST，且类型错误在 Python 层提前暴露：

     ```python
     import uuid
     # 传 uuid.UUID 对象而非字符串，asyncpg 直接识别无需 CAST
     {"clean_id": uuid.UUID(clean_id), ...}
     # SQL 中直接写 :clean_id，不需要任何 CAST
     ```

2. **静态扫描（可加入 pre-commit）：**

   ```bash
   # 检测所有 Python 文件中 :param::type 形式（ERE 语法，兼容 macOS BSD grep）
   grep -rEn ':\w+::' --include='*.py' .
   ```

   任意匹配结果均应人工核查。

3. **集成测试**：为每个使用 `text()` + 命名参数的 service 方法编写集成测试，实际连接 asyncpg（pytest-asyncio + 测试 PG 容器），覆盖含 UUID / JSONB 参数的 upsert 路径。`--sql` dry-run 走 `MockConnection`，不经过 asyncpg 参数替换，不能替代真实执行测试。

4. **重复方法检查**：每次在文件中新增方法前，先 grep 确认同名方法不存在，避免 Python 静默覆盖（后者覆盖前者，无任何警告）。

## Related Issues

- 同项目另一 asyncpg 错误（schema 类型不匹配）：`docs/solutions/database-issues/tenant-companies-bigint-uuid-type-mismatch-2026-05-07.md` — 不同根因（JOIN 类型错配），但同为 asyncpg 运行时错误，可对照参考。
