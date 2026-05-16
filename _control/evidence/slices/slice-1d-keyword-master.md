# Slice 1.D — keyword_master 主表 + fan-out 骨架

状态：**✅ 本地 alembic upgrade 验证通过，已签字**

创建日期：2026-05-07

---

## 目标

建立跨租户关键词去重主表（keyword_master），支持 UC-11 fan-out 语义：
当租户新增关键词订阅时，通过 fan-out worker 将其他租户已采集的 clean_companies 推送给该租户。

| 任务编号 | 说明 |
|----------|------|
| T-CP-20 | 建 `keyword_master` 表（migration 0016） |
| T-CP-21 | 建 `tenant_keyword` 关联表（migration 0016） |
| T-CP-22 | `collection_keywords` 添加 `keyword_master_id` 外键（migration 0017） |
| T-CP-23 | 数据迁移：现有 collection_keywords → keyword_master + tenant_keyword（migration 0017） |
| T-CP-30 | `GET /api/admin/collection-keywords/{kn}/master-check` API |
| T-CP-31 | `keyword_service.py`：normalize_keyword + lookup_keyword_master |
| T-CP-40 | `fan_out.py` worker 骨架 |
| T-CP-62 | 完善 migration downgrade，更新 schema.sql |

---

## 变更范围

### 数据库

- [x] `backend/alembic/versions/20260507_0016_keyword_master_tables.py`
  - 建 `keyword_master`（id, keyword, keyword_normalized UNIQUE, created_at）
  - 建 `tenant_keyword`（id, tenant_id FK→tenants, keyword_master_id FK→keyword_master, UNIQUE(tenant_id, keyword_master_id)）
  - downgrade：DROP TABLE tenant_keyword → DROP TABLE keyword_master

- [x] `backend/alembic/versions/20260507_0017_collection_keywords_master_fk.py`
  - collection_keywords 新增 `keyword_master_id uuid REFERENCES keyword_master(id) ON DELETE SET NULL`
  - 数据迁移：INSERT INTO keyword_master（去重）→ UPDATE collection_keywords.keyword_master_id → INSERT INTO tenant_keyword
  - downgrade：DROP COLUMN keyword_master_id

- [x] `backend/03_database/schema.sql`
  - 新增 keyword_master 表定义（Collection 段之前）
  - 新增 tenant_keyword 表定义
  - collection_keywords 表新增 keyword_master_id 列注释

### 后端服务

- [x] `backend/app/services/keyword_service.py`（新建）
  - `normalize_keyword(raw: str) -> str`：小写 + strip + 去标点 + 合并空白
  - `lookup_keyword_master(conn, keyword_normalized) -> dict | None`：查主表统计
  - `get_or_create_keyword_master(conn, *, keyword, keyword_normalized) -> str`：幂等写入
  - `bind_tenant_keyword(conn, *, tenant_id, keyword_master_id) -> bool`：幂等关联

- [x] `backend/app/api/admin/collection.py`（扩展）
  - 新增路由：`GET /collection-keywords/{keyword_normalized}/master-check`
  - 返回：`{matched: bool, company_count: int, tenant_count: int}`

### Worker

- [x] `backend/app/workers/fan_out.py`（新建）
  - `FanOutWorker.run_for_tenant_keyword(engine, tenant_id, keyword_master_id)`
  - `run_fan_out_for_tenant_keyword(conn, tenant_id, keyword_master_id)`：核心逻辑
  - 批量 INSERT INTO tenant_companies ON CONFLICT DO UPDATE（追加 matched_keywords）
  - 幂等：UNIQUE(tenant_id, clean_company_id) 约束保证

---

## 设计决策

### 为何不直接用 keyword_normalized 作为 keyword_master PK？
UUID PK 保持与其他表一致的外键引用风格，且允许未来关键词重命名而不破坏 FK。

### fan-out 写入 tenant_companies 时如何处理 matched_keywords？
ON CONFLICT DO UPDATE 追加关键词到 jsonb 数组，避免覆盖已有关键词。幂等：已存在则跳过追加。

### downgrade 顺序？
0017 先 DROP COLUMN，再 0016 DROP TABLE（Alembic 按 down_revision 链自动反向执行）。

---

## 验收标准

```bash
# 数据库迁移
cd backend && uv run alembic upgrade head
# 期望：INFO Running upgrade 20260507_0015 -> 20260507_0016, ...
#       INFO Running upgrade 20260507_0016 -> 20260507_0017, ...

# API smoke test（需启动 dev server）
GET /api/admin/collection-keywords/solar-panel/master-check
# 期望：{"matched": false, ...}（生产环境未迁移时）
# 或：{"matched": true, "company_count": N, "tenant_count": M}
```

---

## 签字

- [x] 本地 alembic upgrade 全链通过（lay 2026-05-07）
  - migration 0016：keyword_master + tenant_keyword 建表 ✅
  - migration 0017：collection_keywords.keyword_master_id 列 + 数据迁移 ✅
  - 两个 head（0027 + 0021）全部升级成功 ✅
  - psql 验证：keyword_master(4列)、tenant_keyword(4列) 已建 ✅
  - collection_keywords.keyword_master_id uuid 列已建 ✅
  - 顺手修复 migration 0029 的 LIKE '%%' psycopg 占位符 bug ✅
- [ ] Sealos 生产部署（lay）
