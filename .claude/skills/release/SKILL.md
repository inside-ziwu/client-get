---
name: release
description: ClientGet 发布构建：两实例 5 镜像矩阵，触发 Actions 构建推送阿里云 ACR 并产出 Sealos 更新对照表。当用户要求发布、构建镜像、部署新版本、走发布流程、构建 ACR 时使用。仅在用户明确要求发布时调用，不得作为其他任务的附带动作。
---

# ClientGet 发布构建（两实例 5 镜像）

## 红线

- 构建并推送镜像是**外部副作用**，仅在用户明确要求发布时执行（AGENTS.md §1）。
- 本技能的边界到「镜像推送完成 + 产出 Sealos 对照表」为止；**Sealos 控制台更新镜像 tag 由用户手动完成**，不要代办、不要催促。
- 生产数据库迁移随 backend 容器启动自动执行——发布前必须向用户列出将执行的迁移。

## 背景事实（2026-07-23 确立；与 README §7 发布矩阵互为镜像，改动须两处同步）

两实例（A=默认 `xinanpcb.com` 域、B=sealos 临时域）**共用数据库与 backend 镜像**；前端因 API 地址在**构建时**经 `--build-arg` 写死，必须按实例各构建一套。镜像名不区分实例，**靠 tag 区分**。2026-07-23 曾漏发 B 实例前端，本技能因此而生。

## 发布前检查（必做）

1. `git fetch origin main` 确认发布基线：本地与 origin/main 一致、用户没有想带上却未合并的 PR。
2. 列出**上次部署以来新增的 alembic 迁移**（对比生产库 `alembic_version` 与仓库迁移链，或查 `backend/alembic/versions/` 近期新增），明确告知用户"部署 backend 时将自动执行这些迁移"。若有迁移，建议先在开发库做全链模拟：`downgrade <生产当前版本>` → 一口气 `upgrade head`（历史先例见 docs/solutions/）。
3. **变更范围判断**：
   - 仅动 backend（含迁移）→ 只需构建 backend ×1；
   - 涉及 frontend → **A/B 四个前端镜像全部构建**（漏发某实例 = 该实例前端停留旧版）。

## 5 镜像构建矩阵

| # | service | 实例 | workflow inputs | tag |
|---|---|---|---|---|
| 1 | backend | A+B 共用 | 无实例参数 | 自动 `YYYY.MM.DD-rN` |
| 2 | admin | A | 全部留空（api_url 默认 `https://api.xinanpcb.com`；portal 空值由前端 fallback 到 `https://tenant.xinanpcb.com`，见 `frontend/apps/admin/src/app/(dashboard)/tenants/client-page.tsx`） | 自动 |
| 3 | tenant | A | 留空 | 自动 |
| 4 | admin | B | `api_url=https://sfxteoewmcow.sealosbja.site` `tenant_portal_url=https://ihvjdybutzgy.sealosbja.site` | 显式 `YYYY.MM.DD-b-rN` |
| 5 | tenant | B | `api_url=https://sfxteoewmcow.sealosbja.site` | 显式 `YYYY.MM.DD-b-rN` |

B 实例 tag 的 rN：查当日历史（`gh run list` 或 ACR）取已有 `b-rN` 最大值 +1，首次为 `b-r1`。

## 构建命令

```bash
# A 实例（含共用 backend）——全默认参数
gh workflow run build-and-push.yml -f service=backend
gh workflow run build-and-push.yml -f service=admin
gh workflow run build-and-push.yml -f service=tenant

# B 实例——显式参数 + 显式 tag（rN 按当日递增）
gh workflow run build-and-push.yml -f service=admin -f tag=$(date +%Y.%m.%d)-b-r1 \
  -f api_url=https://sfxteoewmcow.sealosbja.site \
  -f tenant_portal_url=https://ihvjdybutzgy.sealosbja.site
gh workflow run build-and-push.yml -f service=tenant -f tag=$(date +%Y.%m.%d)-b-r1 \
  -f api_url=https://sfxteoewmcow.sealosbja.site
```

## 构建监控与验证（必做）

1. `gh run list --workflow=build-and-push.yml` 拿 run id，`gh run watch <id> --exit-status` 等完成（可后台并行）。
2. 从构建日志验证两件事：实际 tag（`grep -oE "clientget-\w+:[0-9b.r-]+"`）与 **B 实例的 `NEXT_PUBLIC_*` 参数逐字等于矩阵值**（`grep -oE "NEXT_PUBLIC_[A-Z_]*=[^\" ]*"`）。参数不符 = 立即报告用户，不得进入交付。

## 交付报告（模板）

向用户输出：
1. 镜像 → 容器对照表（**8 个容器**）：A API / A worker / B API / B worker ← 同一个 backend 镜像；A admin、A tenant、B admin、B tenant ← 各自实例的镜像；
2. **串行更新提醒**：先换 A 的 backend（API+worker），确认新容器启动成功（= 迁移已执行完），再换 B 的 backend——A、B 共库，避免两容器并发执行迁移的竞态；四个前端随后任意顺序；
3. 部署后验证约定：用户确认 Sealos 更新完成后执行下节四步。

## 部署后验证（用户确认 Sealos 更新完成后，四步按序）

1. **探活**：curl 两实例 `/health`（`https://api.xinanpcb.com` 与 `https://sfxteoewmcow.sealosbja.site`）。
2. **版本指纹**：探活 OK ≠ 新代码在跑（2026-07-23 教训）。从本次 diff 挑一个 OpenAPI 可见变更（新增/删除的路由或参数），curl 两实例公开的 `/openapi.json` 判定；本次变更全部不可见于 OpenAPI 时，如实标注「版本未指纹验证」，不拿探活冒充。
3. **契约探测**：`cd backend && uv run python scripts/schema_snapshot.py --prod`，`git diff backend/03_database/schema_snapshot.json` 应恰好等于本次迁移内容（零迁移则零 diff）；仅统计行数波动时按「发布后快照同步」惯例直推提交。
4. **数据侧业务证据**：视本次变更设计生产只读对照查询（psycopg `read_only`；对照组思路：期望消失的模式归零 + 正常模式仍出现，排除假阴性）。发送窗口未产出时如实标 pending，用定时唤醒复查，不硬凑证据。
