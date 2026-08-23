# 生产上线记录（PR A，2026-08-23）

## 发布

- 基线 `359a89b`（main：#97 + #99 + CI 修复）。首轮 5 个构建全部在推送阶段失败：runner 升级 buildkit 后 `build-push-action` 默认附带 provenance 认证清单（config `application/vnd.oci.empty.v1+json`），阿里云个人版 ACR 拒收。workflow 显式 `provenance: false` / `sbom: false` 后重跑成功。
- 镜像：backend / admin / tenant `2026.08.23-r1`（A）；admin / tenant `2026.08.23-b-r2`（B，`b-r1` 被失败推送占用）。B 的 `NEXT_PUBLIC_*` 参数从构建日志逐字核对。
- 部署后验证：两实例 `/health` 200；`/openapi.json` 150 → 156 条路由，6 条 `industry-news` 路由出现；`schema_snapshot.py --prod` diff 恰好 = 迁移 `20260824_0001`（`f2ac2f9`）；生产 `alembic_version = 20260824_0001`，三表 0 行。

## 种子（生产写入，用户逐次确认）

- 本机无 Sealos kubectl 上下文，种子脚本从本机直连生产库执行（`DATABASE_URL` 指向生产，仅该进程）。
- `--dry-run`：created 14 → 用户确认 → 执行：`created 14 / updated 0 / unchanged 0` → 只读回读 `instance=default` 14 行全部启用、`instance_b` 0 行 → 幂等 dry-run `unchanged 14`。

## 出口核验（A 实例 backend 容器内，用户执行）

`python scripts/run_industry_news_fetch.py --from-file app/data/industry_news_sources_pcb.json`，14/14 `ok`，合计 176 条：

| 源 | 条数 | 源 | 条数 |
|---|---|---|---|
| PCB Update | 26 | PCB East | 8 |
| PCEA | 10 | TPCA | 8 |
| I-Connect007 | 46 | NEPCON JAPAN | 5 |
| PCD&F | 12 | Productronica | 9 |
| Circuits Assembly | 12 | electronica | 8 |
| IPC | 10 | CPCA 协会动态 | 6 |
| PCB West | 10 | CPCA 每周资讯 | 6 |

- 设计里预留的「国内云出口 IPC / I-Connect007 / 慕尼黑两站可能 403 或 0 条」没有发生。
- PCB Update 样本含 `pcdandf.com/…/19444-pcea-announces-…`（CR1 修复前会被裸 `pcea` 误杀）；「PCB West Panel to Take On What's Next for PCB Design」同稿出现在 PCEA / PCB West / Circuits Assembly 三源，入库按 dedup_key 只留一条。
- HTML / JSON-LD 源多数 `published_at = null`，按设计以 `fetched_at` 参与窗口与排序。

## 待办

开关 `INDUSTRY_NEWS_FETCH_ENABLED=true` 只配在 **A 实例 API 容器**（`clientget-backend`，08:00 循环跑在 FastAPI lifespan 里；B 不配）→ 重启 → 管理端「立即抓取」首轮（不依赖开关）→ AC1–AC5 → 观察一轮 08:00 → PR B。
