# V3 · 06 · Release Manifest

> **状态**：✅ 已签字，Gate 8 解除，可执行上线  
> **责任**：AI 起草 → 用户审 → 用户授权发布  
> **Gate**：[Gate 8](../../AGENTS.md#6-门禁规则v3-工作流-10-gates) 阻止上线直到本文件签字  
> **创建日期**：2026-05-07

---

## 0. 元数据

- **版本**：V3 Wave 2
- **计划发布日期**：2026-05-07
- **用户签字**：__待签字__

---

## 1. 应用清单

> 镜像 tag 在执行 push 脚本后自动生成（格式 `YYYY.MM.DD-rN`），请在 push 完成后回填。

| 应用 | 服务类型 | 镜像仓库 | V3 镜像 tag（push 后填） | 端口 | 健康检查路径 |
|------|----------|----------|--------------------------|------|--------------|
| clientget-backend | backend API | `lay_inside/clientget-backend` | _待填_ | 8000 | `/health` |
| collection-worker | worker | `lay_inside/clientget-backend`（同镜像） | _待填_ | — | — |
| collection-scheduler | worker | `lay_inside/clientget-backend`（同镜像） | _待填_ | — | — |
| scoring-worker | worker | `lay_inside/clientget-backend`（同镜像） | _待填_ | — | — |
| sending-worker | worker | `lay_inside/clientget-backend`（同镜像） | _待填_ | — | — |
| clientget-admin | admin 前端 | `lay_inside/clientget-admin` | _待填_ | 80 | `/healthz` |
| clientget-tenant | tenant 前端 | `lay_inside/clientget-tenant` | _待填_ | 80 | `/healthz` |

---

## 2. 数据库迁移

| 项 | 内容 |
|---|---|
| V3 之前 head | `20260507_0015`（contacts migration）|
| V3 Wave 2 目标 head | `20260507_0021`（email_events_index，mergepoint） |
| 迁移数量 | 8 个版本（含 merge point 0021）：主链 0016→0017→0025→0026→0027；分支 0016→0029→0020；merge point 0021(0027,0020) |
| 危险操作 | 0017 含数据回填（keyword_master UPSERT + collection_keywords FK UPDATE），正向幂等；无 DROP COLUMN/TABLE |
| 迁移前备份 | `pg_dump -Fc $DATABASE_URL > clientget-pre-wave2-$(date +%Y%m%d).dump` |
| 执行命令 | `alembic upgrade head` |
| 验证命令 | `alembic current` → 期望 `20260507_0021 (head) (mergepoint)` |
| Rollback | `alembic downgrade 20260507_0015`（8 个版本全部有 downgrade 路径） |

---

## 3. 环境变量变更

> 只列 key，**绝不**粘贴 value。

| 应用 | 新增 key | 修改 key | 移除 key | 备注 |
|------|----------|----------|----------|------|
| backend / sending-worker | `ENGAGELAB_API_USER` | — | `ENGAGELAB_SENDER` | EngageLab HTTP Basic 鉴权用户名 |
| backend / sending-worker | `ENGAGELAB_CREDENTIAL` | — | — | EngageLab HTTP Basic 鉴权密码 |

> **注**：`ENGAGELAB_SENDER` 已从代码中移除（from_email 来自 send_plans.sender_email），Sealos 若有此 key 可保留（config extra="ignore"）或删除，不影响运行。  
> **可选 key（有内置默认值，无需强制配置）**：`ENGAGELAB_API_KEY`（旧 Bearer 兜底，默认 null）、`ENGAGELAB_AUTH_HEADER`（默认 `Authorization`）、`ENGAGELAB_AUTH_SCHEME`（默认 `Bearer`）、`ENGAGELAB_TIMEOUT_SECONDS`（默认 10.0）。

---

## 4. 配置变更

- **Nginx**：无变更，沿用 `deploy/nginx-spa.conf`
- **Worker 启动命令**：无变更
- **新增部署脚本**：
  - `backend/scripts/push-backend.sh`（本次新增）
  - `frontend/deploy/push-admin.sh`（本次新增）
  - `frontend/deploy/push-tenant.sh`（已存在，Step 2 引用）

---

## 5. 依赖与基础设施

| 项 | V3 | 备注 |
|---|---|---|
| PostgreSQL | 现有版本（兼容） | 迁移使用标准 DDL，无版本要求变化 |
| EngageLab | HTTP Basic Auth | 新增 ENGAGELAB_API_USER / ENGAGELAB_CREDENTIAL |
| OpenRouter | 现有配置 | 无变更 |
| 阿里云镜像仓库 | `crpi-q6fqloatvalw3jr2.cn-beijing.personal.cr.aliyuncs.com` | 新增 clientget-backend / clientget-admin repo |

---

## 6. 发布步骤（按顺序）

```
Step 1. 备份生产数据库
  pg_dump -Fc $PROD_DATABASE_URL > clientget-pre-wave2-$(date +%Y%m%d).dump

Step 2. 构建并推送 3 个镜像
  cd backend && bash scripts/push-backend.sh
  cd frontend && bash deploy/push-admin.sh
  cd frontend && bash deploy/push-tenant.sh

Step 3. Sealos 新增环境变量（backend + sending-worker）
  ENGAGELAB_API_USER = <值>
  ENGAGELAB_CREDENTIAL = <值>
  （注：这两个 key 在 Step 5 重启 Pod 后生效，旧镜像运行期间忽略这两个字段不影响现有功能）

Step 4. 在 Sealos backend Pod 终端执行数据库迁移
  alembic upgrade head
  alembic current  # 验证：20260507_0021 (head) (mergepoint)

Step 5. Sealos 滚动更新（顺序：backend → workers → admin/tenant）
  backend      → 步骤 2 输出的 clientget-backend tag
  4 个 worker  → 同一 clientget-backend tag
  admin 前端   → clientget-admin tag
  tenant 前端  → clientget-tenant tag

Step 6. 健康检查
  curl https://api.xinanpcb.com/health

Step 7. 上线后验证（参照 deploy-wave2-checklist.md §五）
  - D-035 渠道白名单
  - Admin 职位分类新页面
  - 租户 EmailMonitor 6 张统计卡
```

---

## 7. 回滚预案

| 触发条件 | 回滚步骤 | 影响范围 |
|----------|----------|----------|
| backend 启动失败 | Sealos 切回上一 tag；若已迁移则 `alembic downgrade 20260507_0015` | 仅 backend |
| 数据正确性问题 | 停应用 → 从 pg_dump 备份恢复 → 切回上版本镜像 | 全部 |
| 邮件投递错误 | 关闭 sending-worker → 调查 → 视情况回滚或热修 | 仅邮件链路 |

---

## 8. Gate 8 Codex 技术核查结论

由 Codex 对本 Manifest 做独立技术核查（2026-05-07）：

| 核查项 | 结论 |
|--------|------|
| 迁移链路与实际文件一致性 | PASS（WARN：描述歧义已修正） |
| 环境变量变更准确性 | PASS（WARN：可选 key 已补充） |
| 回滚路径可行性（8 个 downgrade 实质内容） | PASS |
| Gate 6 两项修复落地验证 | PASS |
| 发布步骤完整性 | PASS（WARN：3 处描述缺口已修正） |

**Codex 核查结论：无 FAIL 项，Manifest 内容技术上准确，可以上线。**

## 9. Gate 6 代码审查结论

已完成，详见 [`_control/reviews/codex-code-review-wave2.md`](../reviews/codex-code-review-wave2.md)。

- 发现 2 个 major 问题，均已修复 commit（`e0cd255`）：
  - M-1：`fan_out.py` EXISTS 子查询未关联关键词与公司 → 已修复
  - M-2：`mark_email_failed` 未写 error_code/error_message → 已修复
- 安全性 PASS，并发安全 PASS，无 critical 问题

---

## 10. 用户签字

> 确认以上内容无误后，请在此行签字，Gate 8 解除：

- [x] **用户签字**（lay，日期：2026-05-07）：**本 Manifest 已审，授权上线 V3 Wave 2**
