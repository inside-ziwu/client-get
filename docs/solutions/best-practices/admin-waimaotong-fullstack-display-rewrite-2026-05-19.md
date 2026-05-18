---
title: "Admin 端外贸通数据展示页面全栈重写 — 踩坑与最佳实践"
date: 2026-05-19
category: best-practices
module: admin-collection
problem_type: best_practice
component: database
severity: low
applies_when:
  - 新增管理后台数据展示页面（列表+筛选+详情）
  - 数据库有线上手动添加的列需追平到 Alembic 迁移
  - 多 provider 共享 service 层查询逻辑
  - 框架迁移后需清理构建配置残留
  - CI/CD tag 依赖自动生成日期
tags:
  - waimaotong
  - admin
  - full-stack
  - alembic-migration
  - sql-query
  - nextjs-page
  - ci-cd
  - data-display
---

# Admin 端外贸通数据展示页面全栈重写 — 踩坑与最佳实践

## Context

在 Admin 管理后台新增外贸通 (waimaotong) 数据源展示页面并移除废弃的腾道 (tendata) 页面时，遇到了一系列跨层级的工程问题：数据库迁移与线上不同步、多 provider 共享 SQL 分支引用已删除列、Python `text[]` 类型被误当 JSON 渲染、Vite->Next.js 迁移后 Dockerfile 残留、以及 CI/CD 的 UTC 时区缓存陷阱。

变更范围覆盖全栈：Alembic 迁移补齐 waimaotong 表的 23 列 -> 后端 `admin_collection_service.py` 重写 SQL 查询（list/debug/contacts 三种模式）-> 前端 Next.js 页面（列表 11 列 + 筛选 8 项 + 详情 Sheet）-> Dockerfile 修复 -> CI/CD tag 策略调整。

(auto memory [claude]) ClientGet 是 B2B 外贸客户智能平台，Admin 端用 Next.js 15 App Router + Tailwind + shadcn/ui，后端 FastAPI + PostgreSQL，部署 Sealos。

## Guidance

### 1. 幂等迁移：用 `ADD COLUMN IF NOT EXISTS` 追平线上 schema

当线上数据库有通过脚本或手动 SQL 直接添加的列（绕过 Alembic），迁移文件与线上不同步时，使用 PostgreSQL 的 `ADD COLUMN IF NOT EXISTS` 实现幂等迁移。

```sql
-- upgrade: 线上已有这些列时不报错，本地/新环境则正常创建
ALTER TABLE waimaotong_raw_companies
    ADD COLUMN IF NOT EXISTS company_name text,
    ADD COLUMN IF NOT EXISTS country text,
    ADD COLUMN IF NOT EXISTS source_keyword text;

-- downgrade: 对称使用 DROP COLUMN IF EXISTS
ALTER TABLE waimaotong_raw_companies
    DROP COLUMN IF EXISTS company_name,
    DROP COLUMN IF EXISTS country,
    DROP COLUMN IF EXISTS source_keyword;
```

Alembic 的 `op.add_column()` 不支持 `IF NOT EXISTS`，必须用 `op.get_bind().exec_driver_sql()` 写原生 SQL。

### 2. 共享 WHERE 分支必须拆分，不能跨 provider 引用列

多个 provider 共享 `elif provider in {"tendata", "waimaotong"}` 分支时，如果一个 provider 的列被删除（如 tendata 的 `country_iso3`、`trade_amount_3y_usd`），另一个 provider 的查询也会报 SQL 错误。

每个 provider 独立 WHERE 分支，即使筛选逻辑相似也不共享：

```python
# WRONG: 共享分支，tendata 列删除后 waimaotong 也挂
elif provider in {"tendata", "waimaotong"}:
    industry_column = "c.industry_desc" if provider == "tendata" else "c.industry"

# RIGHT: 独立分支，各管各的
elif provider == "waimaotong":
    if country_iso3:
        where_parts.append("c.country = :country")
        params["country"] = country_iso3
    if source_keyword:
        where_parts.append("c.source_keyword = :source_keyword")
        params["source_keyword"] = source_keyword
```

### 3. PostgreSQL `text[]` 存储 Python repr 的数据陷阱

`text[]` 类型的列，如果存的是 Python `str(dict_obj)` 的输出（如 `{'name': None, 'imgUrl': '...'}`），既不是合法 JSON 也不是有意义的文本。前端无论当字符串渲染还是尝试 JSON.parse 都会出错。

排查路径：看列类型 -> 采样数据确认实际存储格式 -> 判断能否可靠解析。

如果数据没有可靠的解析方式且业务价值为零，后端 SQL 直接不查该列、前端不渲染。不要试图"兼容"脏数据。

此问题在本次变更中经历了三次迭代才定位根因：
1. 直接 `{products.map(p => <Badge>{p}</Badge>)}` -> 渲染出 Python dict 字符串
2. 尝试解析 `typeof p === 'string' ? p : p?.name` -> Python repr 不是 JSON，仍失败
3. 确认是数据源问题，后端 SQL 不查、前端不渲染（最终方案）

### 4. Vite 到 Next.js 迁移后清理 Dockerfile 残留

框架迁移后，Dockerfile 中的 COPY 指令可能引用已删除的文件。本地不跑 `docker build`（用 CI），直到推送 CI 才暴露。

```dockerfile
# 残留了不存在的文件，构建失败
COPY apps/admin/vite-env-shim.d.ts apps/admin/vite-env-shim.d.ts
```

框架迁移完成后，全局搜索旧框架的特征文件名（如 `vite-env`、`vite.config`），确认 Dockerfile、CI 配置、tsconfig 中无残留引用。

### 5. GitHub Actions UTC 时间 + Sealos 镜像缓存双重陷阱

`date -u` 在 GitHub Actions 中生成 UTC 时间。北京时间 2026-05-19 01:00 触发的构建，tag 生成为 `2026.05.18-r1`（UTC 仍是 18 日）。如果之前 18 日已推送过同名 tag，Sealos 拉取时命中缓存的旧镜像。

两个独立问题叠加：
1. UTC 日期跨天：`date -u +%Y.%m.%d` 和本地日期可能不同
2. 同名 tag 缓存：同一 tag 多次推送，容器运行时拉到的可能是旧版

缓解方案：手动触发 `workflow_dispatch` 时显式指定唯一 tag（如 `2026.05.19-r2`），不依赖自动生成。或者自动 tag 中加入 commit SHA 短码保证唯一性。

### 6. 不存在的 CSS class 不报错，只是静默失效

使用了不存在的 CSS class（如 `className="admin-table"`），Tailwind 不会报错，表格没有样式。需要参照已有页面（如 peers、customers 页面），使用显式 Tailwind class：

```tsx
// WRONG: admin-table 不存在，静默无样式
<table className="admin-table w-full text-sm">

// RIGHT: 显式 Tailwind class
<table className="w-full min-w-[1320px] text-sm">
  <thead className="border-b bg-muted/70 text-left text-xs text-muted-foreground">
    <tr><th className="whitespace-nowrap px-3 py-2">公司名</th></tr>
  </thead>
  <tbody>
    <tr className="cursor-pointer border-b hover:bg-muted/40">
      <td className="px-3 py-2">...</td>
    </tr>
  </tbody>
```

### 7. debug 端点用 `dict(row)` 替代硬编码 payload 键

不同 provider 返回的列集合差异很大时，硬编码 payload 键导致新字段遗漏或旧字段报 KeyError。改用 `dict(row)` 动态映射：

```python
# RIGHT: dict(row) 动态映射
if provider == "waimaotong":
    item = dict(row)
    item["id"] = str(raw_company_id)
    item["provider"] = provider
    item["created_at"] = self._datetime_iso(item.get("created_at"))
    if "source_tags" in item:
        item["source_tags"] = list(item["source_tags"] or [])
    return item
```

### 8. 分页 ORDER BY 必须包含唯一键

`ORDER BY created_at DESC` 在同一秒入库的多条记录之间顺序不稳定，翻页时出现重复或遗漏。加 `id DESC` 作为 tiebreaker：

```sql
ORDER BY c.created_at DESC, c.id DESC LIMIT :limit OFFSET :offset
```

## Why This Matters

- **幂等迁移**避免了"线上跑迁移报 column already exists"的部署事故，在有人手动改过线上 schema 的项目中极为常见
- **WHERE 分支拆分**消除了 provider 间的隐式耦合——删除一个 provider 的列不会导致其他 provider 的 SQL 报错，这是多数据源系统中最常见的回归 bug 来源
- **text[] Python repr 陷阱**说明了列类型和实际存储内容可能完全不匹配，仅看 schema 定义会误判，必须采样验证
- **UTC tag 缓存**是亚洲时区团队使用 UTC-based CI 时的经典组合问题
- **Dockerfile 残留**只在 CI 构建时暴露，本地开发完全无感知，属于典型的"最后一公里"部署失败

## When to Apply

- 数据库有线上直接修改的列需要追平到迁移系统时 -> 幂等迁移模式
- 多个数据源/provider 共用 service 层查询逻辑时 -> 独立 WHERE 分支
- 处理 PostgreSQL 数组类型列且数据来自 Python 爬虫/脚本时 -> 先采样验证实际格式
- 框架迁移（Vite/CRA -> Next.js 等）完成后 -> 全局搜索旧框架特征文件
- CI tag 依赖 `date` 命令自动生成时 -> 注意 UTC 偏移和镜像缓存
- 新建管理后台列表页时 -> 参照已有页面的 Tailwind class，不假设全局 CSS class 存在
- debug/详情 API 需要返回大量动态字段时 -> `dict(row)` 优于硬编码
- 分页查询时 -> ORDER BY 必须包含唯一键

## Examples

### 共享 WHERE 分支拆分

Before（provider 耦合，tendata 列删除后 waimaotong 也报错）:
```python
elif provider in {"tendata", "waimaotong"}:
    industry_column = "c.industry_desc" if provider == "tendata" else "c.industry"
    employee_column = "c.employee_num" if provider == "tendata" else "c.employee_size"
```

After（独立分支，各 provider 只引用自己的列）:
```python
elif provider == "waimaotong":
    if country_iso3:
        where_parts.append("c.country = :country")
        params["country"] = country_iso3
    if source_keyword:
        where_parts.append("c.source_keyword = :source_keyword")
        params["source_keyword"] = source_keyword

elif provider == "tendata":
    # ... 只引用 tendata 真实存在的列
```

### Dockerfile 残留清理

Before（构建失败）:
```dockerfile
COPY apps/admin/next-env.d.ts apps/admin/next-env.d.ts
COPY apps/admin/vite-env-shim.d.ts apps/admin/vite-env-shim.d.ts
```

After:
```dockerfile
COPY apps/admin/next-env.d.ts apps/admin/next-env.d.ts
```

## Related

- [FK 列迁移 NULL 置空模式](../best-practices/fk-column-migration-null-old-values-before-constraint-2026-05-07.md) — 同属 Alembic 迁移最佳实践，覆盖 FK rename + NULL 安全迁移
- [tenant_companies bigint/uuid 类型不匹配](../database-issues/tenant-companies-bigint-uuid-type-mismatch-2026-05-07.md) — 迁移引发类型不匹配的教训，与本文幂等迁移模式互补
- [asyncpg 命名参数类型转换语法错误](../runtime-errors/asyncpg-named-param-cast-syntax-error-20260507.md) — waimaotong SQL 查询使用 asyncpg 时需注意 `:param::type` 语法陷阱
- `docs/plans/2026-05-19-001-feat-admin-waimaotong-display-plan.md` — 本次变更的实施计划
- `openspec/changes/archive/2026-05-19-admin-waimaotong-display/` — 本次变更的 OpenSpec 归档（proposal/design/tasks）
