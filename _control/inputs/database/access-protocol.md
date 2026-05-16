# 数据库访问协议（Database Access Protocol）

> **目的**：定义 AI（Claude Code / Codex 等）与人类协作者访问生产 PostgreSQL 数据库时的硬性安全规则与操作流程。
> **生效时间**：2026-05-05（用户决策）
> **关联**：[Gate 10](../../../AGENTS.md#6-单一真源原则最高优先级)、[`_control/03-runtime-inputs.md`](../../03-runtime-inputs.md)
> **当前选定方案**：**方案 1（schema-only 拷贝）+ 方案 2（偶发数据查询：用户跑、粘贴脱敏结果）**

---

## 1. 硬性边界（不可违反）

| 规则 | 说明 |
| --- | --- |
| **R1** | **AI 不得看到完整 connection string with password**——任何包含 `postgresql://user:password@host` 形式的字符串都不得出现在 AI 对话或工作区文件 |
| **R2** | **AI 不得主动**让用户粘贴 `.env`、连接串、密码、密钥 |
| **R3** | **AI 输出的 SQL / 命令模板不得含真实密码**——用占位符 `<PASSWORD>` 或 `$PGPASSWORD` 环境变量引用 |
| **R4** | **AI 不得把任何 secret 写入** `_control/`、`docs/`、commit message、git tracked 文件 |
| **R5** | 用户不慎在对话中粘贴了密码，AI 必须**立即提醒并不复述**该值，建议用户立即轮换 |
| **R6** | 数据查询结果由用户**手动脱敏**后粘贴给 AI（脱敏规则见 §4） |
| **R7** | AI 探查到的 schema 信息（表名 / 字段名 / 索引名）属于设计资料，可入仓 |
| **R8** | AI 对生产数据库执行 DDL / DML 时只生成 SQL 文本，**由用户在自己工具里执行**——AI 不直接连数据库 |

## 2. 角色与责任

### 2.1 用户

- 持有真实凭证（生产 PG 密码、kubectl context、Sealos 控制台访问权）
- 负责创建 readonly 用户、跑 port-forward、执行 AI 生成的 SQL、脱敏粘贴结果
- 决定哪些数据可以让 AI 看到（按业务敏感度自己判断）
- 凭证存放：本地 `~/.pgpass` / 1Password / `.env`（在 `.gitignore` 内）/ Sealos 控制台 secret——**绝不**进 `_control/`

### 2.2 AI

- 永远只看 schema 与脱敏数据
- 写 SQL 给用户执行，看用户脱敏后粘贴的结果
- 不主动要求看 secret
- 看到密码立即提醒并停止复述

### 2.3 Sealos

- 持有真实数据库（命名空间 `ns-3umexz0o` 内 svc `clientgetdb-postgresql:5432`）
- 通过 `kubectl port-forward` 提供本地访问
- 内置 PG Web Console 可作备选执行界面

## 3. 方案 1：schema-only 拷贝（高频）

### 3.1 何时用

- AI 需要做 §D ER 图 vs 真实 schema 偏差对照
- AI 需要写迁移 / 字段命名 / 关系图分析
- 任何不需要看具体行的工作

### 3.2 命令模板

> 在**用户自己的 shell** 跑。AI 不参与执行。

```bash
# 步骤 1：把密码放环境变量（不入 history、不提交、不发 AI）
read -rsp "PG password: " PGPASSWORD && export PGPASSWORD
# 或者用 ~/.pgpass 文件（chmod 600）

# 步骤 2：起 port-forward（开一个独立终端常驻）
kubectl port-forward -n ns-3umexz0o svc/clientgetdb-postgresql 5432:5432

# 步骤 3：在另一个终端 dump schema-only（不含数据）
pg_dump --schema-only --no-owner --no-privileges \
  -h localhost -p 5432 -U postgres -d <db_name> \
  > _control/inputs/database/schema-current-$(date +%Y-%m-%d).sql

# 步骤 4：清理环境变量（防止误粘贴）
unset PGPASSWORD
```

> 替换 `<db_name>` 为实际数据库名（不要写到本文件里）。

### 3.3 命名约定

| 路径 | 内容 |
| --- | --- |
| `schema-current-YYYY-MM-DD.sql` | 某次 dump 的真实 schema 快照 |
| `schema.sql`（已存在） | blueprint 设计真源（人维护） |

**保留多份历史快照**（每次 schema 变化时新拷一份），不要覆盖。

### 3.4 AI 用 schema 快照做什么

- 与 [`_control/inputs/database/schema.sql`](schema.sql)（设计稿）对照 → 找出所有偏差（V3 §D 任务）
- 与业务流 §9 ER 图对照 → 找出"业务概念 vs 实际表名"的对应关系
- 分析索引 / 外键 / 触发器在生产是否齐全
- 不读任何行数据

## 4. 方案 2：偶发数据查询（低频）

### 4.1 何时用

- 用户问"现在 tenant_companies 里实际有几行？"
- 验收时核对某条记录的实际状态
- 调试某个具体业务流问题

### 4.2 流程

```
1. 用户在对话里描述要看什么
2. AI 写 SELECT 给用户（带 LIMIT / 聚合查询，避免拉海量行）
3. 用户在自己工具里执行（Sealos PG Web Console / 本地 psql / pgAdmin）
4. 用户按 §4.3 脱敏后粘贴结果
5. AI 基于脱敏结果分析
```

### 4.3 脱敏规则

| 字段类型 | 脱敏处理 |
| --- | --- |
| 邮箱 | `a***@example.com` 或仅给 row count |
| 联系人姓名 | 首字符 + `***` 或 row count |
| 电话 | 仅 row count，不给值 |
| 公司名 | 一般可保留（业务公司名非高度敏感） |
| 国家 / 行业 / 时间戳 / 状态字段 | 可保留 |
| token / api_key / password / secret 字段 | **绝不粘贴**，仅说"X 行非空" |
| `raw_payload` JSON | 仅给"X 行有/无该字段"，不给 JSON 内容 |
| 域名（DNS / DKIM 配置） | 一般可保留（公开 DNS 信息） |

### 4.4 AI 输出 SQL 的最佳实践

```sql
-- 优先：聚合查询，不拉行
SELECT count(*) FROM tenant_companies WHERE tenant_id = ...;

-- 次选：明确 LIMIT，仅看少量行
SELECT id, country, source_label FROM tenant_companies
WHERE tenant_id = ... LIMIT 5;

-- 避免：SELECT * FROM 大表
-- 避免：导出敏感字段（email / phone / contact_name）的明文行
```

## 5. 方案 3+4（升级路径，V3 实施期再启用）

> 当前**未启用**，仅作未来参考。

### 5.1 readonly 用户

```sql
-- 在生产 PG 一次性执行（用户自己跑）
CREATE USER clientget_readonly WITH PASSWORD '<新密码，不发 AI>';
GRANT CONNECT ON DATABASE <db> TO clientget_readonly;
GRANT USAGE ON SCHEMA public TO clientget_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO clientget_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO clientget_readonly;
```

### 5.2 本地匿名化副本

如果数据查询频率提高：

```bash
# 用户跑：dump 真实数据
pg_dump --data-only -h localhost -U postgres -d <db> | \
  sed 's/邮箱正则/REDACTED/g' | \    # 自定义脱敏规则
  psql -h localhost -p 5433 -U dev -d clientget_local
```

`docker run -p 5433:5432 postgres:16`（本地端口 5433 避免冲突）。

AI 用 `localhost:5433` 连接（本地密码可固定，不算 secret）。

## 6. 操作历史

> 每次执行方案 1 / 方案 2 时**留一行记录**，便于追溯。**绝不**记录密码、查询出的真实数据。

| 日期 | 操作 | 文件 | 备注 |
| --- | --- | --- | --- |
| 2026-05-05 | 协议成文化 | 本文件创建 | 用户决策 D-007 + DB 访问方案 1+2 |
| _未来_ | _示例：用户 dump schema-current_ | _schema-current-2026-05-05.sql_ | _用于 §D ER 偏差对照_ |

## 7. 应急流程

如果 secret 被误粘贴 / 误写入文件：

1. **立即停止**当前操作，不复述、不进一步处理
2. 用户**立即**在 Sealos / 数据源后台**轮换该密码 / 重生 token**
3. 检查 git history：`git log -p | grep -i "<泄露的部分值>"`
   - 如已 commit 但未 push → `git reset --hard HEAD~N` 或 `git filter-repo`
   - 如已 push → 联系 git 服务商按"凭证泄露"流程处理（GitHub 有 secret scanning + 紧急 invalidate API）
4. 在 [`04-open-questions.md`](../../04-open-questions.md) 登记安全事件
5. 更新本协议 §1 规则，补防御措施

## 8. 参考

- AGENTS.md §6 单一真源 + Gate 10 secrets 边界
- `_control/03-runtime-inputs.md` 已知敏感文件路径清单
- `_control/inputs/sealos/README.md` Sealos 应用清单（仅 env key，不含 value）
