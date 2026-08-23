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

## 首轮抓取与验收

- 用户在 A 实例 API 容器配 `INDUSTRY_NEWS_FETCH_ENABLED=true`（08:00 循环跑在 FastAPI lifespan 里，worker 与 B 不配）并重启，管理端「立即抓取」首轮：14:04:21 UTC 完成，14/14 成功、错误计数 0，入库 148 条（抓到 176，差额为 RSS 源早于 90 天的旧稿）。
- 只读核对：`dedup_key` / `canonical_url` 零重复（三源同稿「PCB West Panel…」只留 Circuits Assembly 一条）；`canonical_url` 无 `utm_` / `#`；条目全部 `instance_id='default'`；114 条无发布时间（HTML / JSON-LD 源）。
- AC1 / AC2 / AC4 / AC5 由用户在生产手动验证通过；AC3 的去重与 90 天过滤已由首轮证实，「08:00 轮次整体置顶」待次日观察。

## 验收中发现的前端问题（#100，同日发布）

1. 折叠侧栏悬停展开层被页面盖住：`aside` 是 sticky（自成层叠上下文、z-index auto），主栏 z-50 页头与 DataTable 的 relative 容器 / 粘性表头画在其上——所有列表页通病。展开时给 `aside` 加 `z-[60]`。
2. 行业动态筛选区两行：改 FilterBar `layout="compact"` + `actionsPlacement="inline"`（与公司列表一致）。

发布：仅 4 个前端镜像（admin / tenant `2026.08.23-r2`，B `2026.08.23-b-r3`），backend 不动；用户更新后确认两处均已修复。

## 待办

观察 2026-08-24 08:00（北京）自动轮次：新增条目整体置顶、14 源 `last_success_at` 刷新、错误计数、去重 → 稳定后 PR B（遗留清理；发布 B 后不可回退到 B 之前的镜像）。

## 发布 B（同日，PR #101 合并后；用户选择不等次日 08:00 轮次）

- 发布前只读复核：四表 2/0/0/0 行、`intelligence_summary` 场景行两实例各 1、无外部 FK，与迁移 docstring 一致。
- 镜像：backend `2026.08.23-r2`；admin / tenant `2026.08.23-r3`（A）、`2026.08.23-b-r4`（B）。用户按「A backend → B backend → 四前端」串行更新。
- 部署后验证：两实例 `/health` 200；`/openapi.json` 156 → 146 条路由（10 条 `intelligence*` 消失，6 条行业动态路由仍在）；`schema_snapshot.py --prod` diff 恰好 = 四表删除 + `alembic_version → 20260824_0002`，既有 65 张表零变化；生产 `pg_tables` 无 `intelligence*` / `articles_p_*`，`ai_scene_defaults` 只剩 scoring / email_generation / data_analysis；行业动态 14 源 / 148 条未受影响。
- 自此不可回退到 `2026.08.23-r1` 及更早的 backend 镜像。
