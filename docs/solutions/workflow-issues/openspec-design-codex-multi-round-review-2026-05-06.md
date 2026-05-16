---
title: 用 codex 多轮独立审查兜底 OpenSpec design.md 起草中的 LLM 偏差
module: openspec/changes/v3-data-foundation
date: 2026-05-06
problem_type: workflow_issue
category: workflow-issues
component: development_workflow
severity: high
related_components:
  - documentation
  - database
tags:
  - openspec
  - design-review
  - codex
  - multi-round-review
  - schema-source-of-truth
  - llm-drift
applies_when:
  - 从空白起草 500+ 行 OpenSpec design.md 并需签字
  - 设计强依赖 schema.sql / Alembic 真源
  - 业务规则有"付费模型 / 数据生命周期"等隐性边界
  - 单一 LLM 一次产出可能层层叠加偏差
---

# 用 codex 多轮独立审查兜底 OpenSpec design.md 起草中的 LLM 偏差

## Context

在 OpenSpec 工作流中（`openspec/changes/<change-id>/design.md`），单次 LLM 起草设计文档时，常见以下偏差：

- **Schema 假设与真源不符**：未 grep `schema.sql` 即假设字段存在
- **业务规则被 SQL 错误约束**：JOIN 类型选错破坏业务语义
- **命名混淆**：业务实体（同行 / raw / 客户 / 视图）多次合并
- **Alembic 链处理错误**：跳过 revision 导致 down_revision 断链
- **旧表述残留**：用户已反馈修订但文档未同步

直接基于这种 design 进入实施 → 大量返工。主 Claude 自审有偏见，无法替代。

## Guidance

### 工作流（每轮闭环）

```
LLM 起草 design.md
   ↓
codex Round N（独立 AI 系统）审查
   ↓ 输出 finding 列表（含文件:行号证据）
主 Claude 按 finding 修复
   ↓
codex Round N+1 验证（限定范围只看修了的项）
   ↓ 0 残留 → 用户签字
```

### 关键操作要点

1. **使用 codex CLI 包装**：通过 `codex exec --json` 流式跑独立审查
2. **每轮限定 prompt 范围**：明确告知 codex 本轮审查边界，避免自动扩展浪费 token
3. **修复后必复审**：不靠主 Claude 自验证（同一上下文有偏见）
4. **turn.failed 容量满**：手动 grep 修复 + 重启 codex 验证特定项
5. **Finding 分级**：Blocker（必修）/ High / Medium / Low，按优先级处理

### 推荐 codex prompt 骨架（Round N+1 验证轮）

```
## 任务：design.md Round N+1 验证（仅 X 项 finding 复核）

Round N 报告 `<path>` 列了 X 项。主 Claude 已逐条修复。

**本轮只验证这 X 项是否真的修好。报告 100-300 行。**

## 验证清单
1. <Round N finding ID>: <修复点描述>
2. ...

## 输出
写到 `_control/reviews/<change-id>-design-roundN+1.md`：
- §0 总体结论（是否签字）
- §1 验证表（| ID | 状态 ✅/⚠️/🔴 | 证据(行号) |）
- §2 新引入问题（如有）

## 约束
- 不修改任何被审文件
- 不重审 Round 1..N 已 ✅ finding
- token <60k
- 完成后回复 `DESIGN ROUND N+1 DONE: <path>`
```

## Why This Matters

8 轮审查实况（来自本仓库 `_control/reviews/codex-code-review-v3-data-foundation-design-roundN.md`）：

| Round | 行数 | finding | 主要问题 |
|---|---|---|---|
| 1 | 1100 | 18（5 Blocker + 6 High + 7 M/L）| schema 假设与真源不符 |
| 2 | 300 | 12 完美 + 6 部分 | 修复后旧表述残留 |
| 3 | 300 | 14 完美 + 2 残留 | 清场（CONCURRENTLY 注释 vs SQL 冲突等）|
| 4 | 300 | 3 Blocker + 2 Medium | 用户业务决策修订（同行重构）|
| 5 | 150 | 5 全过 + 1 typo | — |
| 6 | turn.failed | 抓到关键 finding | OpenAI 容量满中断 |
| 7 | 180 | 5 finding | INNER JOIN 错配付费模型 |
| 8 | 110 | 5 全过 | ✅ 签字 |

**不跑多轮独立审查的代价**：

- 实施阶段才发现 schema 错误 → 已写代码 + 测试全部返工
- 业务规则被 SQL 错配 → 上线后破坏付费模型 / 租户隔离
- Alembic 断链 → 数据库迁移失败，需紧急回滚
- 命名混淆遗留进 schema → 后续所有关联模块继承错误模型

单次起草不可能"一次到位"，靠主 Claude 自审等于不审。

## When to Apply

**适用条件（满足任一即跑）**：

- design.md > 200 行 / 涉及 > 3 张表
- 涉及 schema 真源（数据库 / API contract / migration）
- 涉及业务规则与 SQL 转译（JOIN / 计费 / 权限）
- 跨多个模块（前端 / 后端 / worker）
- 用户已签字前必须 0 残留

**不适用**：

- 纯前端组件局部样式
- 文档表述微调（typo 级）
- 已有充分单元测试覆盖的小改动

## Examples

### 例 1：INNER JOIN 破坏首采付费模型（codex Round 7 V7-1 抓到）

业务规则："首采者付 AI 费 → 后续租户复用免费"

**Before（错）**：

```sql
SELECT op.api_key_encrypted
FROM collection_task_keywords ctk
JOIN openrouter_providers op ON op.tenant_id = ctk.tenant_id
WHERE ctk.task_id = $1
ORDER BY ctk.created_at ASC
LIMIT 1;
```

**问题**：A 最早加入 task 但未配 OpenRouter → INNER JOIN 过滤掉 A → SQL 取到 B 的 key → B 被错误计费 → 破坏首采付费模型。

**After（对）**：

```sql
SELECT ctk.tenant_id, op.api_key_encrypted
FROM collection_task_keywords ctk
LEFT JOIN openrouter_providers op ON op.tenant_id = ctk.tenant_id
WHERE ctk.task_id = $1
ORDER BY ctk.created_at ASC, ctk.id ASC
LIMIT 1;
```

代码层判 `api_key_encrypted IS NULL` 返回 `None`，**不 fallback 到后续租户**——首采租户未配则字段保持 NULL，AI 字段一次性回填，运维手动脚本兜底。

### 例 2：Schema 真源识别陷阱（codex Round 6 抓到）

**Before（错）**：design.md 假设 `collection_tasks.tenant_id` 字段存在。

**After（对）**：grep `schema.sql` 后发现：

```sql
-- collection_tasks 无 tenant_id 字段
CREATE TABLE collection_tasks (
  id uuid PRIMARY KEY,
  keyword text NOT NULL,
  -- ... 没有 tenant_id
);

-- 多租户关联通过 collection_task_keywords 多对多
CREATE TABLE collection_task_keywords (
  task_id uuid NOT NULL REFERENCES collection_tasks(id),
  keyword_id uuid NOT NULL REFERENCES collection_keywords(id),
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  ...
);
```

**教训**：不假设字段名 / 字段类型，必须 grep schema.sql 验证。design.md `_get_task_tenant_openrouter_key()` 函数实现要从 `collection_task_keywords` 反查首采租户。

### 例 3：Alembic revision 链不能跳中间（codex Round 1 B-04 抓到）

**Before（错）**：

```
"alembic 0012 不跑"  ← 但 0013.down_revision = '20260501_0012'
跳过 → 链断 → alembic upgrade head 失败
```

**After（对）**：

```python
# alembic/versions/20260501_0012_waimaotong_raw_contacts.py
revision = "20260501_0012"
down_revision = "20260501_0011"

def upgrade():
    # codex B-04 修订（2026-05-06）：D-035 外贸通推迟 V3.1+，本 migration 改为空
    # 保留 revision id 维持 Alembic 链路完整（0013 的 down_revision 仍指向 0012）
    pass

def downgrade():
    pass
```

保留 revision id，链不断。**绝不"跳过"中间 revision**。

### 例 4：业务上 4 类数据不能合并 3 类（codex Round 4 抓到）

**Before（错）**：把 `tendata_raw_*` 与 `shared_companies` 混为"客户库"。

**After（对）**：明确 4 类生命周期：

| 类别 | 表 | 用途 | 租户可见 |
|---|---|---|:-:|
| 同行 | `competitor_companies` | 中国同行清单（励销云）| ❌ |
| 腾道 raw | `tendata_raw_*` | 原始未清洗 | ❌ |
| 客户 | `shared_companies + company_sources` | 清洗后干净库 | ✅ 通过 view |
| 视图 | `tenant_companies` | 租户私有视图 | ✅ RLS |

每类必须有明确的生命周期对照表，禁止合并简化。

## 相关案例参考（本仓库）

### 现有"多轮审查"实践

- [`docs/spec-collection-module-review.md`](../../spec-collection-module-review.md) — 单轮 CEO + Eng 双视角审查报告（3 P0 + 4 P1 修订项）
- [`docs/spec-phase1.5-collection-pipeline-refactor.md`](../../spec-phase1.5-collection-pipeline-refactor.md) — plan-eng-review + Codex outside voice 两轮审查产出（11 问题 → 范围重定义）
- [`docs/plan-phase1-contacts-pipeline.md`](../../plan-phase1-contacts-pipeline.md) — v1/v2/v3 三版迭代（2 轮审查驱动）

### 本会话产出（8 轮 data-foundation-design 完整链）

位于 `_control/reviews/codex-code-review-v3-data-foundation-design-roundN.md`：

| 文件 | 大小 | 备注 |
|---|---|---|
| `...-design.md` (Round 1) | 31 KB | 18 finding 起点 |
| `...-design-round2.md` | 19 KB | 部分修 + 9 项新引入残留 |
| `...-design-round3.md` | 9 KB | 16 项清场 14 完美 |
| `...-design-round4.md` | 14 KB | 同行重构（用户业务决策）|
| `...-design-round5.md` | 9 KB | 5 项全过 |
| `...-design-round7.md` | 9 KB | INNER JOIN 错配 |
| `...-design-round8.md` | 8 KB | 全过签字 |

设计文档最终签字版：[`openspec/changes/v3-data-foundation/design.md`](../../../openspec/changes/v3-data-foundation/design.md)（约 1500 行）。

## 关键操作工具

```bash
# 启动 codex 独立审查（本仓库 codex CLI 路径 /Users/lay/.bun/bin/codex）
codex exec \
  --cd /path/to/repo \
  --sandbox workspace-write \
  --skip-git-repo-check \
  --json \
  -c 'model_reasoning_effort="medium"' \
  "$PROMPT" < /dev/null > /tmp/codex-stream.log 2>&1
```

注意：

- `< /dev/null` 必加，避免 codex 卡 stdin 等待
- `timeout 600` 包装防止挂死
- ChatGPT 账户下仅支持默认 model（GPT-5 系列），其他 model 名会被拒绝
- 容量满（OpenAI 服务侧拥堵）时返回 `Selected model is at capacity`，30-60 分钟后重试
