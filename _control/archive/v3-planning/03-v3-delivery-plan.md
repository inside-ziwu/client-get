# V3 · 03 · Delivery Plan（6-Slice 骨架 × 5 OpenSpec change）

> **状态**：v1.0 起草（2026-05-06）—— 保留 ChatGPT §10 的 6-Slice 骨架，编织 5 个 OpenSpec change 与 9 能力域
> **责任**：Claude Code 起草 → 用户审节奏 → 用户签字
> **Gate**：本文件未签字前，[Gate 5](../../AGENTS.md#6-门禁规则v3-工作流-10-gates) 阻止 `/ce:work` 启动开发
> **关联**：[`02-current-implementation-gap-audit.md`](02-current-implementation-gap-audit.md)（9 能力域 × 缺口编号）+ [`01-v3-acceptance-matrix.md`](01-v3-acceptance-matrix.md)（18 V3-* 验收 ID）

## 0. 元数据

- 版本：v1.0（首版编织 5 OpenSpec change）
- 起草日期：2026-05-06
- 用户签字：__未签字__
- 节奏方案：**C — 基座先行 + 业务并行**（用户 2026-05-06 决策）

---

## 1. 总体原则

- **只补 P0 Gap**：不重做已满足的能力，不预先优化 P1/P2
- **每任务对应**：① V3-* 验收 ID（[01-acceptance-matrix](01-v3-acceptance-matrix.md)）+ ② Cn-Gx 缺口编号（[02-gap-audit](02-current-implementation-gap-audit.md)）+ ③ D-XXX 决策号
- **Wave 1 主导**：v3-data-foundation 是 C5 / C6 / C7（依赖 clean_companies +11 字段 + cleanup_service + sending worker 部署）的硬依赖；**C3 联系人分类是软依赖**——alembic 升级 + worker base 模板就绪后即可并行设计/编码（codex H-01 修订）
- **Wave 2 并行**：4 个 change 在 Wave 1 主体完成后并行；C3 可在 Wave 1.A alembic 升级后提前启动
- **每 Slice 可独立验收**：单 Slice 完成就能给用户看效果
- **DB 改动**：必须 migration + rollback + staging 验证
- **Worker 改动**：必须状态机 / 幂等 / 重试 / 错误日志
- **邮件发送**：必须防重复（email_send_locks 或幂等键）
- **Tenant 改动**：必须 A/B 隔离验证

---

## 1.5 Wave 节奏（5 OpenSpec change 编排）

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Wave 1 — 数据基座（独占，1 周）                                         │
│  ───────────────────────────────                                        │
│  v3-data-foundation                                                     │
│    ├─ Slice 0: 开发基线 + 容器化基线（C8-G1, G2）                        │
│    ├─ Slice 1.A: alembic 0006 → 0013 升级（C8-G3）                      │
│    └─ Slice 1.B: D-008 重构 6 raw + 2 clean + cleanup_service（C1-G1~5） │
│                                                                          │
│  ▼ Wave 1 完成 = 数据基座 + cleanup_service 部署 + alembic 升级到位      │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│  Wave 2 — 业务并行（4 change 并发，2-3 周）                              │
│  ──────────────────────────────────────────                             │
│  ┌──────────────────────┐  ┌──────────────────────┐                     │
│  │ v3-collection-       │  │ v3-email-delivery    │                     │
│  │   pushback           │  │                      │                     │
│  │ Slice 1.C UC-10      │  │ Slice 3 真发 + 域名  │                     │
│  │ Slice 1.D KeywordMast│  │ Slice 5 E2E 验收     │                     │
│  │ Slice 2 去重+隔离    │  │ (R-3 + C7 + C9)      │                     │
│  │ (C2)                 │  │                      │                     │
│  └──────────────────────┘  └──────────────────────┘                     │
│  ┌──────────────────────┐  ┌──────────────────────┐                     │
│  │ v3-tenant-companies  │  │ v3-contact-          │                     │
│  │                      │  │   classification     │                     │
│  │ C4 私有操作 4 件套   │  │ C3 admin 中央配      │                     │
│  │ C5 10 项筛选         │  │ 4 张新表             │                     │
│  │ C6 评分模板          │  │ classify 函数        │                     │
│  │ (附属，不阻塞主链)   │  │ (附属，C7 引用)      │                     │
│  └──────────────────────┘  └──────────────────────┘                     │
│                                                                          │
│  Slice 4 Worker 可靠性 = 横切基础设施，每 change 自补                    │
│                                                                          │
│  ▼ Wave 2 完成 = 9 能力域全交付 → Slice 5 Sealos E2E 验收               │
└─────────────────────────────────────────────────────────────────────────┘

依赖图：
                    Wave 1
                   ┌─────┐
                   │data-│
                   │found│
                   └──┬──┘
                      │ alembic + cleanup_service ready
        ┌──────┬──────┼──────┬──────┐
        ▼      ▼      ▼      ▼      ▼
    [collec] [email] [comp] [contact-cls]
        │      │      │      │
        └──────┴──────┴──────┘
                      ▼
                  Slice 5 E2E
```

**Slice ↔ change 矩阵：**

| Slice | 对应能力域 | 主 change | 附属 change |
|---|---|---|---|
| **Slice 0** 开发基线 | C8 | v3-data-foundation | — |
| **Slice 1.A** alembic 升级 | C8 | v3-data-foundation | — |
| **Slice 1.B** D-008 重构 | C1 | v3-data-foundation | — |
| **Slice 1.C** UC-10 admin 启动 | C2 | v3-collection-pushback | — |
| **Slice 1.D** KeywordMaster | C2 | v3-collection-pushback | — |
| **Slice 2** 去重 + 租户隔离 | C1+C2 | v3-data-foundation + v3-collection-pushback | — |
| **Slice 3** 邮件投递 | C7 | v3-email-delivery | v3-contact-classification（C7-G7 依赖 classify）|
| **Slice 4** Worker 可靠性 | C8 横切 | 所有 change 自补 | — |
| **Slice 5** Sealos E2E | C9 | v3-email-delivery | v3-tenant-companies / v3-contact-classification 都需先完工 |

**附属能力域**（不在 Slice 主链，但 Wave 2 必须并行完成）：

| 能力 | OpenSpec change | 与主链关系 |
|---|---|---|
| C3 联系人分类 | v3-contact-classification | C7 Slice 3 的 C7-G7 依赖 classify(position) 函数 |
| C4 私有操作 | v3-tenant-companies | 独立，不阻塞主链；Slice 5 E2E 时验收 |
| C5 10 项筛选 | v3-tenant-companies | 独立，依赖 C1-G4 的 9 字段（Wave 1） |
| C6 评分模板 | v3-tenant-companies | 独立，scoring worker 部署随 Wave 1 |

---

## 2. Slice 0 — 开发基线与运行基线

> **目标**：确认当前代码能运行、能测试、能构建、能部署。这一步失败 → 立刻停。

| 项 | 内容 |
| --- | --- |
| **能力域** | C8 |
| **OpenSpec change** | v3-data-foundation |
| **Wave** | 1 |
| **针对缺口** | C8-G1（容器构建）、C8-G2（Sealos 部署清单） |
| **针对验收 ID** | V3-DEPLOY-001（前置部分）|
| **AI 任务** | 1) 读 `package.json` / `pyproject.toml` 把实测命令记录到 `_control/v3/slices/slice-0-dev-runtime-baseline.md`（**不直接改 AGENTS.md / CLAUDE.md**，按 AGENTS.md 工作区规则；如需更新两份文件，列为"人类维护者待补"建议）；2) 验证 admin / backend / 4 worker 本地可启动；3) 起草 Dockerfile（4 worker + cleanup_service）+ Sealos 部署清单（k8s yaml + 调度 + 健康检查）；4) 输出基线报告 |
| **用户任务** | 1) 确认基线代码版本；2) 提供本地 `.env`（不发给 AI，由用户自填）；3) 确认 Sealos 部署入口与权限 |
| **交付物** | `_control/v3/slices/slice-0-dev-runtime-baseline.md` |
| **验收标准** | 本地 admin ✅ / backend ✅ / 4 worker ✅ / DB 连接 ✅ / Docker build 命令明确 ✅ / Sealos 部署 yaml 通过 staging 验证 ✅ |

## 3. Slice 1 — 真实采集闭环（拆 4 子片）

> **目标**：创建采集任务 → worker 反推（励销云 stage1 + 腾道 stage2）→ 结果入 raw → cleanup → clean → 分发到租户 → 前端展示。

### 3.1 Slice 1.A — alembic 升级（C8）

| 项 | 内容 |
| --- | --- |
| **OpenSpec change** | v3-data-foundation |
| **针对缺口** | C8-G3（alembic 0006 → 0013）+ F1 / F2 已知缺口 |
| **AI 任务** | 1) 跑 0007~0013 升级；2) staging 验证 schema = schema.sql；3) 回滚预案 |
| **验收标准** | 真实 DB schema 与 schema.sql 完全对齐；prod / staging 升级脚本可用 |

### 3.2 Slice 1.B — D-008 重构（C1）

| 项 | 内容 |
| --- | --- |
| **OpenSpec change** | v3-data-foundation |
| **针对缺口** | C1-G1~G5 |
| **AI 任务** | 1) 拆 raw 表（去外贸通）；2) 建 shared_companies / shared_contacts；3) 建 cleanup_queue + cleanup_service worker（lease + 重试 + 跨源合并 + 励销云不入 clean）；4) clean_companies +11 字段（D-038 9 个 + D-039 2 个）；5) D-008 数据迁移 + 回滚 |
| **针对验收 ID** | V3-COL-005、V3-COL-006 |
| **验收标准** | 干净库 0 行 → 跑首采后 ≥1 行 PCB 公司；同公司重复采集 → UNIQUE 1 行 |

### 3.3 Slice 1.C — UC-10 admin 启动按钮（C2）

| 项 | 内容 |
| --- | --- |
| **OpenSpec change** | v3-collection-pushback |
| **Wave** | 2 |
| **针对缺口** | **UC-10 启动按钮已实现**（codex B-01 验证：admin/CollectionTasks/index.tsx:230-302），需按 D-035 限制 channel |
| **AI 任务** | 1) **复核**现有 admin/CollectionTasks `triggerMutation` + 触发按钮交互；2) 按 D-035 限制：UI 隐藏 / 禁用 direct channel（外贸通推迟 V3.1+），仅保留 reverse 入口；3) 后端 `POST collection-keywords/trigger` 防御性拒绝 channel=direct |
| **针对验收 ID** | V3-COL-002、V3-COL-003 |
| **验收标准** | admin 点按钮 → channel=reverse 任务入库 → worker pickup → 反推完成；direct channel 入口已禁用 |

### 3.4 Slice 1.D — KeywordMaster + UC-11（C2）

| 项 | 内容 |
| --- | --- |
| **OpenSpec change** | v3-collection-pushback |
| **针对缺口** | C2-G1~G5 |
| **AI 任务** | 1) 建 keyword_master 表；2) 拆 collection_keywords；3) UC-06 命中分支；4) UC-11 fan-out worker；5) UC-12/14 改写 |
| **针对验收 ID** | V3-COL-001、V3-COL-002 |
| **验收标准** | A 租户采过的关键词，B 租户配同关键词后立即看到 A 当年客户（0 等待）|

## 4. Slice 2 — 采集结果去重 + 租户隔离

| 项 | 内容 |
| --- | --- |
| **能力域** | C1（cleanup_service）+ C2（fan-out） |
| **OpenSpec change** | v3-data-foundation + v3-collection-pushback |
| **Wave** | 1 + 2（因 cleanup_service 在 Wave 1 完成，fan-out 在 Wave 2）|
| **针对缺口** | C1-G3（cleanup_service）、C2-G4（fan-out）|
| **针对验收 ID** | V3-COL-006、V3-COL-007、V3-AUTH-001 |
| **AI 任务** | 1) cleanup_service 多源合并去重；2) tenant_companies fan-out 复制规则；3) 跨租户 UNIQUE 约束；4) A/B 双租户 RLS 验证；5) 励销云不入 clean 规则单测 |
| **用户任务** | 1) 准备测试租户 A/B；2) 确认重复客户合并策略 |
| **交付物** | `_control/v3/slices/slice-2-dedupe-tenant.md` + 单测 + A/B 隔离日志 |
| **验收标准** | 租户 A 看不到 B 的私有状态字段；同公司重复采集 → 跨源合并到 1 行；励销云原始数据租户永不可见 |

## 5. Slice 3 — 真实邮件投递闭环

| 项 | 内容 |
| --- | --- |
| **能力域** | C7 |
| **OpenSpec change** | v3-email-delivery（主）+ v3-contact-classification（依赖：classify 函数）|
| **Wave** | 2 |
| **针对缺口** | C7-G1~G9（域名 + sending + 监控 + 预热档位 + EngageLab 接入） |
| **针对验收 ID** | V3-MAIL-001~006、V3-WORKER-002（防重复）|
| **AI 任务** | 1) admin 创建租户 Modal +"发件域名 + 起始预热档位"；2) admin 域名 Tab 调 EngageLab Domain API；3) 触发验证 + DNS 一键复制；4) sending worker 部署；5) UC-25 邮件计划新建调 classify(position) 取联系人；6) emails 表写入 + 状态回写；7) 预热档位限速 |
| **用户任务** | 1) 提供 EngageLab API_USER；2) 提供 1 个测试域名；3) 配 DNS 记录线下；4) 提供测试收件邮箱；5) 验收真实邮件 |
| **交付物** | PR + 单测 + `_control/v3/slices/slice-3-email-e2e.md` |
| **验收标准** | 域名验证 verified ✅ → 创建邮件计划 → sending worker 真发 → 测试收件箱真实收到 ✅ → emails.status = delivered |

## 6. Slice 4 — Worker 可靠性与可观测性

> **横切基础设施**：每个 change 内 worker 都遵循同一标准。Wave 1 v3-data-foundation 提供基线；其他 change 自补。

| 项 | 内容 |
| --- | --- |
| **能力域** | C8 横切 |
| **OpenSpec change** | 所有 change 自补；v3-data-foundation 提供模板 |
| **Wave** | 1 模板 + 2 各 change 跟进 |
| **针对缺口** | C8-G5（监控/日志/重试/幂等）|
| **针对验收 ID** | V3-WORKER-001（重试）、V3-WORKER-002（防重复）|
| **AI 任务** | 1) 建 worker base class（retry + heartbeat + idempotency）；2) error_code / error_message 标准化；3) 任务超时；4) 幂等键（email_send_locks 等）；5) 结构化日志；6) worker health 端点 |
| **用户任务** | 1) 确认重试策略（次数 / 退避）；2) 确认是否需要人工重试入口 |
| **交付物** | `_control/v3/slices/slice-4-worker-reliability.md` + base class + 各 worker 接入 |
| **验收标准** | Worker 重启不丢任务；重复点击不重复发送；失败有 error_code；状态机 pending/running/success/failed/retrying 完整 |

## 7. Slice 5 — Sealos E2E 发布验收

| 项 | 内容 |
| --- | --- |
| **能力域** | C9 |
| **OpenSpec change** | v3-email-delivery（验收用例归此 change）|
| **Wave** | 2 收尾 |
| **针对缺口** | C9-G1~G5 |
| **前置依赖** | Wave 1 完成 + Wave 2 全 4 change 完成 |
| **针对验收 ID** | V3-DEPLOY-001 + 全部 V3-* |
| **AI 任务** | 1) release checklist；2) 部署 manifest；3) E2E 测试脚本；4) 汇总日志 + 验收报告 |
| **用户任务** | 1) Sealos 部署；2) 验证 admin/tenant 全模块；3) 用 t-019dc236 / t-019dc238 跑全链路；4) 真实发件验收；5) 签字 |
| **交付物** | [`05-v3-pm-acceptance-report.md`](05-v3-pm-acceptance-report.md) + [`06-v3-release-manifest.md`](06-v3-release-manifest.md) + `docs/releases/2026-XX-XX-v3-sealos-release.md` |
| **验收标准** | Sealos 全链路：登录 → 配置 → 关键词 → admin 启动首采 → worker 反推 → 干净库入库 → tenant 浏览 + 私有操作 → 创建邮件计划 → worker 真发 → 收件箱收到 ✅ |

---

## 8. 切片之间的强制 Review

> 每个 Slice 完成后，**Wave 1 必须串行 Review，Wave 2 各 change 各自独立 Review 后汇合到 Slice 5**。

```
单 Slice 完成
    ↓
CE review (/ce:review)
    ↓
gstack eng review (/plan-eng-review + /review)
    ↓
Codex review (codex /review)
    ↓
修复（仅 Blocker / High Risk；Medium / Low 排期）
    ↓
PM 验收
    ↓
进下一 Slice / 下一 change（Wave 2 内并行）
```

| Slice 完成后必跑 | 输出文件 |
| --- | --- |
| CE review | `_control/reviews/ce-review-slice-X.md` |
| gstack eng review | `_control/reviews/gstack-eng-review-slice-X.md` |
| Codex code review | `_control/reviews/codex-code-review-slice-X.md` |

---

## 9. 5 OpenSpec change 索引

> 每 change 在 `openspec/changes/` 下独立目录，含 proposal.md / design.md / tasks.md / specs/。

| # | change 目录 | Wave | 覆盖能力 | 主要 Slice | 状态 |
|---|---|:-:|---|---|---|
| 1 | `v3-data-foundation` | 1 | C1 + C8 | Slice 0, 1.A, 1.B, 4(模板) | ✅ 已创建（待签字）|
| 2 | `v3-collection-pushback` | 2 | C2 | Slice 1.C, 1.D, 2 | ✅ 已创建（待签字）|
| 3 | `v3-email-delivery` | 2 | C7 + C9 | Slice 3, 5 | ✅ 已创建（待签字）|
| 4 | `v3-tenant-companies` | 2 | C4 + C5 + C6 | 附属（Slice 5 阻塞）| ✅ 已创建（待签字）|
| 5 | `v3-contact-classification` | 2 | C3 | 附属（C7 引用）| ✅ 已创建（待签字）|

旧占位 `v3-complete-collection-email/` → archive（已完成）。

---

## 10. PM Review Checklist（签字前）

- [ ] Wave 1 / Wave 2 节奏合理（基座先行 + 业务并行）
- [ ] 5 个 change 拆分覆盖 9 能力域无遗漏
- [ ] 每 Slice 都有：能力域 + change + 缺口编号 + V3-* 验收 ID
- [ ] DB 改动都有 migration + rollback
- [ ] Worker 改动都符合 Slice 4 标准
- [ ] 邮件发送有防重复
- [ ] Tenant 改动有 A/B 隔离验证
- [ ] 附属能力（C3/C4/C5/C6）有明确 Wave 2 时间窗口
- [ ] Slice 5 E2E 前置依赖明确（Wave 2 全完工）

签字行：

```
__________________________ (用户)   日期：__________
```

---

> **本文件不含**：每 change 内部 task 拆分（→ openspec/changes/*/tasks.md）、E2E 用例细节（→ 04-v3-e2e-test-plan）、决策追溯（→ 00-v3-target-spec.md）。
