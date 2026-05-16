# 04 · 待解决问题清单

> **目的**：所有"我不确定 / 需要决策 / 等用户确认"的问题汇总在这里。代理在动手前必须先扫一眼。
> **更新**：2026-05-05

## 状态图例

- 🔴 **阻塞**——不解决就没法继续
- 🟡 **待澄清**——影响方向但暂可绕行
- 🟢 **已决策**——保留作历史记录

## 单一真源原则（2026-05-05 用户决策）

> 详见 [`AGENTS.md`](../AGENTS.md#6-单一真源原则最高优先级)。
>
> **`_control/v3/00-v3-target-spec.md` 是 V3 唯一权威**。参考材料之间冲突 → 全部由用户拍板，AI 不得自决。AI 给的"建议答案"列仅供参考，签字前不生效。

---

## A. 范围与基线（最关键）

| # | 状态 | 提出 | 问题 | 影响 | AI 建议答案（待用户拍板） |
| --- | --- | --- | --- | --- | --- |
| A1 | 🟡 | 2026-05-04 | "v3" 具体指什么？范围、目标用户、关键能力 | `_control/v3/00-v3-target-spec.md` | **V3 = `docs/business-flow-DRAFT.md` 中标的"1.0 全部 33 UC" + Phase 1.5 D1-D4 必修结构债**（已写入 v0.1 草稿） |
| A2 | 🟡 | 2026-05-04 | `blueprint/` 中 00–09 蓝图是否仍是当前权威源？ | docs 索引 `[BASELINE?]` / `[HISTORY]` 取舍 | **部分过时**：blueprint 00-09 仍为蓝图设计参考，但 2026-04-30 后 docs/spec-* + business-flow-DRAFT 已修订 12_COLLECTION_SERVICE_REPAIRED 等部分内容 |
| A3 | 🟡 | 2026-05-04 | `docs/spec-*` 是否取代 blueprint 的 `12_COLLECTION_SERVICE_REPAIRED.md` / `05_services/COLLECTION_SERVICE_SPEC.md`？ | 写代码遵循谁 | **是**：docs/spec-* + business-flow-DRAFT 优先（2026-04-30 之后产物，含 Q1-Q24 业务方对齐成果与 Phase 1.5 D1-D4 修订） |
| A4 | 🟡 | 2026-05-04 | 是否需要把 blueprint 关键文档拷贝到 `_control/inputs/local-docs-raw/`？ | inputs 是否启用 | **不需要**：blueprint 已在 `02-docs-index.md` 索引；local-docs-raw 留给真正"散落本地、不在工作区"的文档 |
| A5 | 🟢 | 2026-05-10 | 原目录名 `clientget-backend-blueprint-v1` 中的 `-v1` 后缀含义已过期？ | 命名混乱风险 | **已解决**：目录已拆分为 `backend/`（活跃后端代码）与 `blueprint/`（历史蓝图资料） |

---

## B. 文件重复与命名疑点

| # | 状态 | 提出 | 问题 | 影响 |
| --- | --- | --- | --- | --- |
| B1 | 🟡 | 2026-05-04 | `backend/03_database/schema.sql` 与 `blueprint/03_database/schema.sql` **MD5 完全相同**——是否两份都需要保留？谁是真源？ | 后续维护 schema 时改哪一份 |
| B2 | 🟡 | 2026-05-04 | `backend/scripts/run_collection_scheduler.py` 与 `run_collection_scheduler_worker.py` 命名相近，未读代码无法判断职责差异 | worker 启动入口选哪个 |
| B3 | 🟡 | 2026-05-04 | `blueprint/docs/OPEN_QUESTIONS.md` 与 `08_references/OWNER_OPEN_QUESTIONS.md` 是否内容重复或概念区分？ | 谁是权威 |
| B4 | 🟡 | 2026-05-04 | 前端缺 `Dockerfile` 直接的构建脚本对照——`deploy/push-tenant.sh` 存在但没有 `push-admin.sh`，是否使用同一脚本？ | 部署流程理解 |

---

## C. 敏感文件与版本控制

| # | 状态 | 提出 | 问题 | 影响 |
| --- | --- | --- | --- | --- |
| C1 | 🔴 | 2026-05-04 | `backend/.env` 真实存在，**本次未读**——是否在 backend 子仓库 `.gitignore` 内？是否曾被误提交进 git 历史？ | 凭证泄露风险 |
| C2 | 🟡 | 2026-05-04 | `frontend/apps/{tenant,admin}/.env.development` 是否含敏感开发密钥？是否被前端 `.gitignore` 排除？ | 同上，但风险等级较低 |
| C3 | 🟡 | 2026-05-04 | `backend/docs/legacy_migration_report.json`（1.2KB）**未读**——是否含数据库样本数据？是否应当从子仓库排除？ | 数据合规 |
| C4 | 🟡 | 2026-05-04 | 工作区根 `.gitignore` 已排除两个独立子仓库与噪音目录，但**没有**显式规则排除根目录可能新增的 `.env`、`.env.local`——目前根目录无 .env 文件，但作为防御性补全建议加上 | 防误提交 |

---

## F. 数据库结构与代码层（2026-05-04 整理 schema 时新增）

| # | 状态 | 提出 | 问题 | 影响 |
| --- | --- | --- | --- | --- |
| F1 | 🔴 | 2026-05-04 | `backend/app/models/` **是空目录**（仅 `__pycache__`）——后端是否未使用 SQLAlchemy ORM？所有数据访问通过 `repositories/` 裸 SQL？还是模型在别处？ | ORM 层是否需要补；写代码风格选型 |
| F2 | 🟡 | 2026-05-04 | `scoring_jobs`（0003）与 `waimaotong_raw_contacts`（0012）由迁移单独创建，未回写到 `schema.sql`——schema.sql 与真实库结构存在偏差。是否定期"同步刷新"？ | 设计真源准确性 |
| F3 | 🟡 | 2026-05-04 | 月度分区由"启动钩子"创建，0010 加 DEFAULT 分区兜底。启动钩子在何处？（推测在 `backend/app/main.py` 的 FastAPI lifespan，未读确认） | 部署运行模型 |
| F4 | 🟡 | 2026-05-04 | `backend/03_database/schema.sql` 与 `blueprint/03_database/schema.sql` **MD5 相同但角色不同**——前者被 alembic 0001 加载，后者是设计真源副本。修改时如何保证同步？是否应当将其中一份变成软链接？ | 维护纪律（B1 的进一步澄清） |

> ⚠️ B1 已被 F4 取代（更准确的描述）。

## D. 启动与运行

| # | 状态 | 提出 | 问题 | 影响 |
| --- | --- | --- | --- | --- |
| D1 | 🟡 | 2026-05-04 | 前端 `pnpm dev` / `pnpm build` 实际命令名是否与推测一致？需读 `frontend/package.json` 与各 app `package.json` 的 `scripts` 段 | `01-code-roots.md` §1.4 准确性 |
| D2 | 🟡 | 2026-05-04 | 后端启动命令？`uv run uvicorn app.main:app` 还是有自定义入口（`pyproject.toml` `[project.scripts]`）？ | `01-code-roots.md` §2.3 准确性 |
| D3 | 🟡 | 2026-05-04 | 数据库类型？PG 版本？连接是本地 docker-compose、还是 Sealos 远端？ | `03-runtime-inputs.md` §2 |
| D4 | 🟡 | 2026-05-04 | 各第三方服务（OpenRouter / EngageLab / 腾道 / 外贸通 / 励销云）的鉴权方式与密钥来源？ | `03-runtime-inputs.md` §3 |
| D5 | 🟡 | 2026-05-04 | 前端是否有自动化测试？未发现 `tests/` 或 `__tests__/` 目录 | 测试覆盖盘点 |

---

## E. 工作区结构与协作

| # | 状态 | 提出 | 问题 | 影响 |
| --- | --- | --- | --- | --- |
| E1 | 🟡 | 2026-05-04 | 根目录 `opencode.json` + `.opencode/` —— 用户当前是否在用 OpenCode CLI？还是已废弃？ | 是否清理（**本次不动**） |
| E2 | 🟡 | 2026-05-04 | `.playwright-mcp/` 含 146 项截图与 console log——是否仍在使用？是否可清理？ | 工作区瘦身（**本次不动**） |
| E3 | 🟡 | 2026-05-04 | 工作区根 `.pytest_cache/` 与 `backend/.pytest_cache/` 都存在——为什么根目录也有？是否曾在根跑过 pytest？ | 配置一致性 |
| E4 | 🟡 | 2026-05-04 | `blueprint/docs/AGENT_PROGRESS.md` 与 `NEXT_SESSION_PROMPT.md` ——AI 代理工作记录，是否仍准确反映当前状态？ | 是否纳入"基线"还是标 `[HISTORY]` |
| E5 | 🟡 | 2026-05-04 | `blueprint/docs/plans/2026-04-22-collection-independent-deployment-plan.md` 与 `superpowers/specs/2026-04-22-collection-independent-deployment-design.md` 是否仍在执行？ | 部署架构方向 |

---

## G. V3 架构决策（2026-05-05 用户拍板）

| # | 决策 | 影响 | 落地 |
| --- | --- | --- | --- |
| D-001 | V3 代码起点 = `backend/`，**完全独立**，**不复用** aoqi/sysdev-ft-marketing 代码 | aoqi 仅作参考蓝本；现有 13 alembic 迁移 + 44 表 + 4 worker 是 V3 基础 | [`v3/00-v3-target-spec.md` §0.A](../v3/00-v3-target-spec.md) |
| D-002 | 邮件发送 = **EngageLab 集中发**，**不是**租户自配 SMTP | 业务流 UC-05 / §4.4 / `tenant_smtp_credentials` 需要修订（→ Q-002） | 同上 |
| D-003 | 单一真源 = `_control/v3/00-v3-target-spec.md` | 参考材料冲突由用户拍板，AI 不自决 | [`AGENTS.md` §6](../AGENTS.md#6-单一真源原则最高优先级) |

## G+ 用户决策（2026-05-05 续）

| # | 决策 | 影响 |
| --- | --- | --- |
| **D-004** | 一个租户支持 **N 个发件域名**（不限 1 个，可跨子产品 / 邮箱角色分别绑） | `tenant_email_domains` 是 1:N 关系（tenant_id → 多个 domain） |
| **D-005** | 邮件 `Reply-To` **默认 = `From`**（同一邮箱收发）；不需要租户能自定义 Reply-To ≠ From | UI 简化（无 Reply-To 输入项）；sending worker 默认省略 Reply-To header |

## J. §D ER vs Schema 偏差（2026-05-05 用户跑 schema dump 后生成）

> 详细对照表见 [`v3/02-er-schema-divergence.md`](../v3/02-er-schema-divergence.md)。本节仅列**待用户拍板**的决策项。

| # | 决策项 | 影响 | AI 建议 | 状态 |
| --- | --- | --- | --- | --- |
| **D-008 ✅ = (B)** | **重构为业务流 6 raw + 2 clean 模型**（用户 2026-05-05 决策） | 业务流 §9.3/§9.4 保持权威；V3 工作量 +5-10 天；Phase 1.5 D2/D3/D4 **重新打开**；D-001 修订（允许 raw/clean 重构）；D-015 重新评估（励销云落点）；派生 4 子决策 D-008-B.1~4 | 接受 B + 全部代价 | 🟢 已决策 |
| **D-009 ✅ = (A)** | UC-11 V3 完整做（用户 2026-05-05 决策）| 新建 keyword_master 表 + UC-06 命中分支 + UC-11 fan-out + UC-12/14 改写；V3 工作量 +3-4 天；业务流 §3.4 完整满足；4 个子决策 D-009-A.1~4 派生 | 接受完整实施 | 🟢 已决策 |
| **D-010 ✅ = (A)** | 实际 Schema 命名为准（用户 2026-05-05 决策） | 仅 3 处剩余命名分歧（D-008/009 已涵盖大部分）：SendingPlanTarget→sending_plan_recipients / TenantEmailTemplate→email_templates / EmailSendLog→拆为 emails+email_events | 接受 | 🟢 已决策 |
| **D-011 ❌取消** | ~~tenant_companies.is_curated 字段~~ | D-020 取代：精选 = 群组（group_members）→ 不需要字段 | — | 🟢 已取消（用户 2026-05-05） |
| **D-012 ✅ = (A)** | tenant_companies.matched_keywords jsonb 数组字段（用户 2026-05-05 决策）| 同步加 clean_companies.matched_keywords；删 tenant_companies.keyword_id 单 FK；业务流 §9.0 "M:N 优先数组"原则一致；GIN 索引保证查询性能 | 接受 | 🟢 已决策 |
| **D-013 ✅ = (A)** | 复用 domain_warmup_status（用户 2026-05-05 决策）| 不新建 tenant_email_domains；该表已含 spf/dkim/dmarc/verification_status 等所有 D-002 必需字段；D-002 实施直接用此表 | 接受 | 🟢 已决策 |
| **D-014 ✅ = (A)** | emails.reply_* 字段保留 V3 不写入（用户 2026-05-05 决策）| schema 已预留 5 个回信字段，V3 default NULL；sending worker 不填；未来 V3.1+ 接 Inbound 直接用 | 接受 | 🟢 已决策 |
| **D-015 ✅ = (i)** | 励销云数据落 lixiaoyun_raw_* 走业务流原版（用户 2026-05-05 决策；同时关闭 D-008-B.3）| 建 lixiaoyun_raw_companies + lixiaoyun_raw_contacts；cleanup_service 加规则 source_type='lixiaoyun' → 标 done 跳过 clean；competitor_companies V3 暂留待实施时评估 | 接受 | 🟢 已决策 |
| **D-016 ✅ = (A)** | 接受多账号轮换已实现到 V3（用户 2026-05-05 决策）| `data_source_credentials` 已含 rotation_order / current_day_used / consecutive_error_count；业务流 UC-16 A3 "Phase 2" 标注过时；V3 直接启用 | 接受 | 🟢 已决策 |
| **D-017 ✅ = (B)** | 分两阶段升级（用户 2026-05-05 决策）| Stage 1: 0006→0013（7 迁移）+ smoke test；Stage 2: V3 新增重构迁移（D-008/009/012/015 对应 4-6 迁移）；前置必做：pg_dump 备份 + staging 验证 + 0009 review + 回滚预案；派生 4 子决策 D-017-B.1~4 | 接受 | 🟢 已决策 |
| **D-018 ✅ = (A)** | R-3 邮件投递 = from-scratch 实施（用户 2026-05-05 决策）| V3 Delivery Plan Slice 3 标"从零实施"；含 sending worker 部署 + EngageLab 接入 + 域名验证 + 测试租户首次实发邮件 | 接受 | 🟢 已决策 |
| **D-019 ✅ = (A)** | V3 E2E 复用 t-019dc236 + t-019dc238（用户 2026-05-05 决策）| 跳过新建租户；直接进入业务流程测试；inputs/test-data 模板 A/B 字段填这两个 slug | 接受 | 🟢 已决策 |
| **D-020 ✅** | 精选 = CuratedCustomers"群组"模型（用户 2026-05-05 澄清） | 不需要 is_curated 字段（D-011 取消）；查 group_members 即知 | 接受群组模型；V3 实施时核对 backend `prospect_status='selected'` 与 groups 表是否双轨需统一 | 🟢 已决策 |
| **D-024 ✅** | UC-05 配域名 = 仅 admin 端，tenant 端无 UI 入口（用户 2026-05-05 澄清） | 修订 D-002 / Q-002.1；UC-05 状态 PARTIAL 缺口 = 后端 DNS 验证流程 | 接受 admin 单端流程 | 🟢 已决策 |
| **D-025 ✅** | V3 数据流：raw → clean(shared_*) → tenant 视图 → 评分 → 筛选 → 群组(精选) | 与 D-008 shared+sources 模型 + D-020 群组模型一致；明确精选实现路径 | 接受 | 🟢 已决策 |
| **D-021 ✅ = (Other)（D-034 修订）** | ~~UC-30 仅联系人级标记~~ → **D-034 整体推迟 V3.1+**（业务方 2026-05-05 二次修正） | UC-30 完全不在 V3；emails.replied_at V3 期间永远 NULL | — | 🟢 已决策推迟 |
| **D-026 ✅** | 业务方对齐：邮件状态粒度 = 联系人级（用户 2026-05-05）| 业务流 §3.5 Q13 / §4.2 Q17 / §4.6 末 5 态聚合 / §4.7 Q22 公司级中断条款在 V3 范围内**失效**；§B 5 态聚合规则关闭（不需要） | — | 🟢 已决策 |
| **D-030 ✅** | 明确 admin 创建租户表单维持现状字段（业务方 2026-05-05 确认；2026-05-06 据实修订措辞）| 现状创建表单字段 = 租户名称 / 行业 / 联系人 / 联系电话 / 管理员邮箱 / 管理员姓名 / 管理员密码（**原本就无邀请邮件 + 临时密码字段**，本决策为澄清现状）；明确 V3 不增加"邀请邮件链接 → 用户自设密码"流程；不生成临时密码；账号信息线下交租户 | UC-02/UC-03 措辞调整；admin/Tenants 创建表单维持现状 | 🟢 已决策 |
| **D-031 ✅** | 域名 + 预热档位在创建租户时同步配置（业务方修正 2026-05-05）| 之前 D-024：域名是单独 admin 操作；现修订：**创建租户表单**直接含"发件域名"+"起始预热档位"字段；运营一次提交完成 | UC-02 + UC-05 合并；admin/Tenants 创建表单字段扩展 | 🟢 已决策 |
| **D-032 ✅** | UC-31/32/33 推迟 V3.1+（业务方修正 2026-05-05）| 修订 D-023（widget 设计）+ D-029（全部 UC 在 V3）；V3 不做计划复盘多维 widget / Tenant Dashboard 多维 widget / 跨计划趋势折线图；V3 上线时 3 个页面可暂留极简版 | UC-31/32/33 整体出 V3；前端简化；省 1.5-2 天工作量 | 🟢 已决策 |
| **D-033 ✅ = (A)** | UC-25 目标策略 = "按 UC-08 规则自动筛选"单一选项（用户 2026-05-05 决策）| UC-24 取消；UC-25 不再让租户选目标策略；自动取该公司所有匹配 UC-08 优先级序列的联系人；后端可借鉴 aoqi `v_buyer_contacts` 视图模式；业务流 §3.6 末段（主联系人自动选定）+ §4.1 Q15（3 选 1）+ UC-24 整段失效；前端 UC-25 移除目标策略选择 UI / UC-18 移除"设为主联系人"按钮；省 0.5 天 | 接受 | 🟢 已决策 |
| **D-034 ✅** | UC-30 手动标已回复 + 已回复识别 + 公司级中断 整体推迟 V3.1+（业务方 2026-05-05 二次修正）| 修订 D-021；V3 期间 emails.replied_at 永远 NULL；序列按时间表完整推进；不做 IMAP / Inbound / 手动标记；客户回信仅租户邮箱可见，平台无操作入口 | UC-30 完全出 V3；省 1 天 | 🟢 已决策 |
| **D-035 ✅** | 外贸通采集（直采路径）整体推迟 V3.1+（业务方 2026-05-05 三次修正）| V3 仅做反推路径（励销云 stage 1 + 腾道 stage 2）；waimaotong provider 不实现；waimaotong_raw_companies/contacts 表 V3 期间空（schema 保留，alembic 0012 仍跑只为不破坏历史链）；D-008=B 6 raw 模型实际 V3 仅用 4 raw（tendata + lixiaoyun × companies/contacts）；客户库**全部为精准客户**（直采=0）；业务流 §2.1 路径 A / §2.7 外贸通 1000/天 / §3.3 直采标签 V3 期间无意义；省 1.5-2 天 worker 实现 + 0.5-1 天 raw 重构 | UC-12 仅实现 tendata + lixiaoyun provider；省 2-3 天 | 🟢 已决策 |
| **D-036 ✅ = (A)** | V3 多步骤序列模型 = ClientGet 原版 1 plan + N steps（用户 2026-05-05 决策；aoqi 调研后）| 维持现有 schema：sending_plans + sequence_steps + sequence_enrollments；与业务流 §4.2 Q16 + §9.8 ER 一致；不切换到 aoqi N plan + linked 模型；D-034 后无回复中断，两模型功能等价 → 选 0 天工作量方案 | 接受 | 🟢 已决策 |
| **D-037 ✅** | 联系人职位分类规则（用户 2026-05-05 苏格拉底澄清后落档）| 新功能：4 层模型（等级 → 类别 → 关键词），admin 单一权威配置，租户无 UI 入口；业务流 §3.6 / UC-08 整段重写：从 tenant 端搬到 admin 端 | 详细见下表 | 🟢 已决策 |
| **D-038 ✅** | 客户列表 / 精选列表 10 项筛选（用户 2026-05-05 决策 i/i/i/iii；D-039 修订档位）| clean_companies 新加 9 字段；档位筛 + 多选 OR；**第 10 项 = 联系人数量档位筛**（用户 2026-05-06 更正）；**档位与 D-039 评分一致**（Q2 = a）；详情见 §N | 详细见下表 | 🟢 已决策 |
| **D-039 ✅** | 默认评分规则 7 维（用户 2026-05-06 决策 b/a/b/加/a/a）| 平台模板 + 租户仅调权重（Q1=b）；档位与 D-038 一致（Q2=a）；按行业分模板（Q3=b，PCB 维度仅 PCB 行业）；clean_companies 加 factory_type + has_china_pcb_supplier 2 字段（Q4）；等级 S/A/B/C/D 阈值 90/70/50/30；档位外兜底 0 分（Q5）；数据来源维度 V3 保留（Q6=a）；详情见 §O | +3.5-4.5 天 | 🟢 已决策 |
| **D-040 ✅** | V3 范围限定 **PCB 行业**专属 + 移除复盘流程描述（用户 2026-05-06 修订 business-goals）| §1 V3 一句话目标删"复盘"；§2 服务谁改"PCB 外贸厂"；§4 流程闭环删"复盘"节点；D-039 行业分模板架构保留但 V3 期间只配 PCB 模板；非 PCB 行业租户 V3 不服务（V3.1+ 再开放）| 工作量基本不变（D-032 已节省复盘工作；D-039 多行业架构保留预留扩展） | 🟢 已决策 |
| **D-022 ✅ = (A)（2026-05-06 修订）** | V3 全做客户库私有操作 4 件套前端 Drawer 入口（用户 2026-05-05 决策；2026-05-06 二次确认）| 评分调整 + 备注 textarea + 标签 add/remove + **群组管理**（D-020 精选 = 群组；原"主联系人"D-033 已取消）；按 mockup `tenant-companies.html` 实现（commit `7ceb218` 已含原型 enterEditMode + scoreAdjEdit + tagsEdit + noteEdit + showBatchAddGroup）；后端 API PASS；工作量 1.5 天；用户 2026-05-06 答 OpenSpec 拆分 4 问时再次确认"原型已齐 V3 必做"——已映射到 [`v3-tenant-companies`](../openspec/changes/v3-tenant-companies/proposal.md) C4 | 接受 | 🟢 已决策 |
| **D-023 ✅ = (a)** | AI 提议默认 widget 集（用户 2026-05-05 决策）| UC-32 6 个 widget（客户总览/来源分布/邮件累计/AI 余额/最近活动/待处理）+ UC-33 3 个 widget（计划列表/趋势折线/筛选）；按业务流 §4.8 落地；后续按需调整 | 接受 | 🟢 已决策 |
| **D-041 ✅** | 投递监控 6 项指标 V3 必做（撤销 N-08 + N-09；用户 2026-05-06 决策）| 以原型 `_control/v3/mockups/tenant-email-monitor.html` 为准：发送量 / 送达率（含软退信 / 无效邮箱明细）/ 独立打开率（含开信追踪）/ 软退信 / 举报垃圾邮件 / 退订；EngageLab 通道 `open_tracking=true` + webhook 回写或 API 拉取；business-goals §6.2 N-08 / N-09 标"已撤销"；business-goals §5.4 加"投递监控"条款；v3-email-delivery proposal.md Non-Goals 删 N-08 / N-09 引用；新增 emails 表回写字段（opens / open_count / first_opened_at / soft_bounce / invalid_email / report_spam / unsubscribe）+ sending worker EngageLab webhook 处理 | +1.5-2 天工作量（数据库字段 + webhook 接入 + 监控 UI 接 EngageLab 回写） | 🟢 已决策 |

## M. D-037 联系人职位分类规则详细设计（用户 2026-05-05 苏格拉底澄清落档）

### M.1 数据模型（4 层）

| 表 | 字段（核心）| 说明 |
| --- | --- | --- |
| `position_classification_levels` | id, name (e.g. "A"), display_name (e.g. "决策层"), sort_order, **is_sendable bool**, created_at, updated_at | 等级表，admin 可增删 |
| `position_classification_categories` | id, level_id (FK), name (e.g. "老板/创始人"), display_name, sort_order, created_at | 类别表，admin 在 level 下增删 |
| `position_classification_keywords` | id, category_id (FK), keyword (lowercase), created_at | 关键词表，admin 配 |
| `v_tenant_contact_classified`（视图）| sys_contact_id, level_id, category_id, is_sendable | 运行时计算每联系人匹配的等级/类别 |

### M.2 匹配规则

- **切词**：联系人 `position` 用空格 / 标点切词 → 词列表 → 全部小写
- **匹配**：与 `keyword`（已小写）做集合交集判断；命中即视为该 keyword 命中
- **多关键词命中冲突**（Q8 = a）：取**最高等级**（按 `level.sort_order`）
- **未命中任何**（Q7 = c）：归"未分类"虚拟等级，**不投递**
- 大小写：忽略

### M.3 配置权限（Q6 = a）

- **平台单一权威**：admin 在 `admin/contact-classification` 页面配置全套规则
- **租户无配置权**：tenant/settings/contact-rules 页面**完全删除**（D-029 衔接修订）
- **实时生效**（Q10 = a）：admin 改了立即对未来生效；**不**反向重算已生成的草稿

### M.4 V3 上线初始数据（Q12.1 = c）

- **业务方手工提供初始关键词清单** → AI 写入 alembic 数据迁移
- **业务方需提供**：每个等级的 name + display_name + is_sendable + 各类别的 name + 各类别的关键词列表
- 上线前阻塞：业务方未给 → admin 启动后规则空 → 所有邮件计划无目标 → 业务流卡住
- 替代方案：临时用 aoqi A/B/X 默认值兜底（业务方上线前再调整）—— 待你确认是否启用

### M.5 业务流修订记录

| 业务流条款 | 修订前 | 修订后（D-037）|
| --- | --- | --- |
| §1.1 配置者 | 租户自配 | **平台运营统一配置** |
| §3.6 联系人优先级规则 | 租户级"职位关键词优先级序列" | **平台级 4 层模型**（等级/类别/关键词 + is_sendable 开关）|
| UC-08 配置联系人优先级规则 | tenant/settings/contact-rules | **整段搬到 admin/contact-classification** |
| §3.6 末段"主联系人自动选定" | 由优先级规则驱动 | D-033 已取消（无主联系人）|
| §4.1 Q15 邮件计划目标策略 | 主联系人/全部/自定义 | D-033 改为按 D-037 规则自动筛选 is_sendable=true 的等级 |

### M.6 命名（Q12.2 = c）

- 表前缀：`position_classification_*`
- API 路由：`/admin/api/v1/position-classification/levels` / `/categories` / `/keywords`
- 前端 admin 页面：`admin/contact-classification`

### M.7 V3 工作量

- 4 张表 + 1 个视图 + alembic 迁移：0.5 天
- admin 端 UI（树状增删 levels/categories/keywords + is_sendable 开关）：1 天
- 后端服务：classify(position) 函数 + UC-25 目标筛选集成：0.3 天
- 测试 + 业务方关键词清单写入：0.2 天
- **小计：+2 天**
- V3 总：12-23 → **14-25 天**

### M.8 派生子决策（V3 实施时细化）

| # | 子决策 |
| --- | --- |
| D-037-X.1 | 业务方提供初始关键词清单的**截止时间** + 是否启用 aoqi 兜底默认值（M.4 备选）|
| D-037-X.2 | admin 端 UI 设计粒度：树状管理 / 表格 / 弹窗编辑 |
| D-037-X.3 | 联系人 position 切词的具体规则（标点是否含 `/`、`-` 等）|
| D-037-X.4 | 命中关键词后是否记录"为什么是这个等级"（审计 / 调试用途）|

## N. D-038 客户列表 / 精选列表筛选详细设计（用户 2026-05-05 决策）

### N.1 10 项筛选与 clean_companies 字段映射

| # | 筛选项 | clean_companies 字段 | 字段类型 | 是否新加 | 筛选模式 |
| --- | --- | --- | --- | --- | --- |
| 1 | 国家 | `country` | varchar(100) | ✅ 已有 | 多选 OR |
| 2 | 行业细分 | `industry` + `industry_tags` | varchar + jsonb | ✅ 已有 | 多选 OR + GIN |
| 3 | 成立时间 | `established_year` | int | ✅ 已有 | 档位（`<3 年 / 3-5 / 5-10 / >10`）|
| 4 | 注册资金 | **`reg_capital_usd`** | decimal(15,2) | 🆕 新加（V3 允许 NULL）| 档位 |
| 5 | 产品标签 | **`product_tags`** | jsonb（字符串数组）| 🆕 新加（与 product_keywords 分开）| 多选 OR + GIN |
| 6 | 公司规模 | **`employee_count_band`** + `employee_count_raw` | enum + varchar | 🆕 双字段（band 归一档位 / raw 保留原始） | 多选 OR |
| 7 | 数据来源 | `sources` | jsonb | ✅ D-008=B 后含 | 多选 OR + GIN |
| 8 | 进出口额 | **`import_amount_usd`** + **`export_amount_usd`** | decimal × 2 | 🆕 4 字段方案 | 档位 |
| 9 | 进出口次数 | **`import_frequency`** + **`export_frequency`** | int × 2 | 🆕 4 字段方案 | 档位 |
| 10 | 联系人数量 | **COUNT(clean_contacts)** 按 company 聚合（建议加冗余字段 `clean_companies.contact_count int` 由 cleanup_service 维护，避免实时 COUNT）| int | 🆕 加冗余字段 | 档位筛 |

### N.2 8 个新字段 alembic 设计（V3 实施时合并到 D-008=B 重构迁移）

```sql
-- clean_companies 新加字段（D-038 更正后共 9 个）
ALTER TABLE clean_companies ADD COLUMN reg_capital_usd numeric(15,2);
ALTER TABLE clean_companies ADD COLUMN product_tags jsonb DEFAULT '[]';
ALTER TABLE clean_companies ADD COLUMN employee_count_band varchar(20);  -- enum value
ALTER TABLE clean_companies ADD COLUMN employee_count_raw varchar(50);    -- 原始字符串
ALTER TABLE clean_companies ADD COLUMN import_amount_usd numeric(15,2);
ALTER TABLE clean_companies ADD COLUMN export_amount_usd numeric(15,2);
ALTER TABLE clean_companies ADD COLUMN import_frequency int;
ALTER TABLE clean_companies ADD COLUMN export_frequency int;
ALTER TABLE clean_companies ADD COLUMN contact_count int DEFAULT 0;       -- D-038 更正第 10 项

-- 索引
CREATE INDEX idx_clean_companies_country ON clean_companies(country);
CREATE INDEX idx_clean_companies_established ON clean_companies(established_year);
CREATE INDEX idx_clean_companies_employee_band ON clean_companies(employee_count_band);
CREATE INDEX idx_clean_companies_industry_tags ON clean_companies USING gin(industry_tags);
CREATE INDEX idx_clean_companies_product_tags ON clean_companies USING gin(product_tags);
CREATE INDEX idx_clean_companies_sources ON clean_companies USING gin(sources);
CREATE INDEX idx_clean_companies_contact_count ON clean_companies(contact_count);
```

### N.3 第 10 项联系人数量筛选实现（用户 2026-05-06 更正）

`clean_companies` 加冗余字段 `contact_count int`，由 cleanup_service 在 INSERT/UPDATE clean_contacts 时同步维护（避免实时 COUNT 性能问题）。

```sql
ALTER TABLE clean_companies ADD COLUMN contact_count int DEFAULT 0;
CREATE INDEX idx_clean_companies_contact_count ON clean_companies(contact_count);

-- 维护逻辑（cleanup_service 内）
-- 每次 UPSERT clean_contacts 后：
UPDATE clean_companies
SET contact_count = (SELECT COUNT(*) FROM clean_contacts WHERE company_id = $1)
WHERE id = $1;
```

档位筛（建议默认值，admin 可调）：

| 联系人数量档位 |
| --- |
| 0（无联系人） |
| 1-3（少） |
| 4-10（中） |
| 11-30（多） |
| >30（密集） |

### N.4 档位定义（V3 默认值，D-039 后档位与评分一致）

| 项 | 档位（D-039 修订）|
| --- | --- |
| 成立时间 | `<3 年 / 3-5 年 / 5-10 年 / >10 年` |
| 注册资金 | `<10 万 USD / 10-100 万 / 100-1000 万 / >1000 万` |
| **公司规模** | `<10 / 10-49 / 51-499 / 500-1999 / >2000` 人（与 D-039 评分档位一致）|
| **进出口额** | `<10 万 / 10-50 万 / 50-3000 万 / >3000 万` USD（与 D-039 评分档位一致）|
| **进出口次数** | `<6 / 6-36 / 36-360 / >360` 次（与 D-039 评分档位一致）|
| 联系人数量 | `0 / 1-3 / 4-10 / 11-30 / >30` |

档位在 admin 端可配置（与 D-037 模式类似）—— 待 D-038-X.4 子决策定。

### N.5 派生子决策（V3 实施时细化）

| # | 子决策 |
| --- | --- |
| D-038-X.1 | cleanup_service 怎么从 raw 表（tendata + lixiaoyun）映射填 8 个新字段 |
| D-038-X.2 | product_tags 生成方式：(a) 采集时同步 LLM 打 / (b) 异步批量回填脚本 |
| D-038-X.3 | employee_count_band 归一化映射规则（如 `"100-500 人" → '50-200'`）|
| D-038-X.4 | 档位定义是否在 admin 端可配（默认值如 N.4，admin 可调？）|
| D-038-X.5 | 精选列表筛选与客户列表筛选 UI 是否一致（建议复用同一 FilterPanel 组件） |

### N.6 工作量

| 项 | 工作量 |
| --- | --- |
| schema 8 个字段 + 索引 + alembic | 0.5 天 |
| cleanup_service 字段映射逻辑（D-038-X.1）| 0.3-0.5 天 |
| product_tags AI 回填脚本（D-038-X.2）| 0.5-1 天 |
| employee_count_band 归一化逻辑 | 0.2 天 |
| 后端 10 项 filter API + GIN 索引调优 | 1-2 天 |
| 前端筛选 UI（档位 / 多选 / 联系人类别）| 1-2 天 |
| **小计** | **+3.5-6 天** |
| **V3 总** | **14-25 → 17.5-31 天** |

## O. D-039 默认评分规则详细设计（用户 2026-05-06 决策）

### O.1 7 个评分维度（PCB 行业默认模板）

| 维度 | 字段 | 档位与分值 | 默认权重 |
| --- | --- | --- | --- |
| **工厂性质** | `clean_companies.factory_type` enum | 生产制造 10 / OEM 6 / ODM 8 / 其他 0 | TBD |
| **工厂规模** | `clean_companies.employee_count_band` | 中型(51-499) 20 / 大型(500-1999) 16 / 小型(10-49) 16 / 超大型(>2000) 0 / 极小(<10) 0 | TBD |
| **进出口额** | `import_amount_usd + export_amount_usd` | <10 万 12 / 10-50 万 20 / 50-3000 万 16 / >3000 万 0 | TBD |
| **进出口次数** | `import_frequency + export_frequency` | <6 0 / 6-36 6 / 36-360 10 / >360 8 | TBD |
| **联系人** | clean_contacts JOIN（含"采购"类别）| 有采购 10 / 无采购 8 | TBD |
| **数据来源** | `clean_companies.sources` | A 反推 10 / B 外贸通 8 / C 其他网上采集 6 | TBD（V3 全部 A）|
| **PCB 供应商**（仅 PCB 行业）| `clean_companies.has_china_pcb_supplier` bool | 有 20 / 无 10 | TBD |

总分（最高估）= 10 + 20 + 20 + 10 + 10 + 10 + 20 = **100 分**（按权重 100% 计）

### O.2 等级映射（用户决策 Q5 = a + AI 示例）

| 等级 | 分数区间 |
| --- | --- |
| **S** | ≥ 90 |
| **A** | 70 - 89 |
| **B** | 50 - 69 |
| **C** | 30 - 49 |
| **D** | < 30 |

### O.3 兜底规则（Q5 = b）

| 情况 | 分数 |
| --- | --- |
| 字段为 NULL（数据缺失）| 0 分 |
| 档位之外（如工厂规模 < 10、进出口次数 < 6、工厂性质"其他"等）| 0 分 |

### O.4 字段新加（Q4，clean_companies 第 10、11 字段）

```sql
ALTER TABLE clean_companies ADD COLUMN factory_type varchar(20);  -- enum: 生产制造/OEM/ODM/其他
ALTER TABLE clean_companies ADD COLUMN has_china_pcb_supplier boolean;  -- PCB 行业用
CREATE INDEX idx_clean_companies_factory_type ON clean_companies(factory_type);
```

### O.5 配置权限（Q1 = b 调整版）

- **平台运营**配置评分模板（含维度 / 档位 / 分值映射 / 默认权重）
- **租户仅能调权重**（不能加维度 / 不能改档位 / 不能改分值映射）
- 业务流 UC-07 修订：从"租户配评分维度"改为"租户调权重"
- admin 端新增 `admin/scoring-templates` 页面（按行业管理模板）
- 租户端 `tenant/settings/scoring` 仅显示当前模板 + 提供权重滑块 / 数字输入

### O.6 行业分模板（Q3 = b）

- `platform_scoring_templates.industry` 字段已支持
- admin 配置时按行业（PCB / 服装 / 电子等）分别建模板
- 租户创建时根据 `tenants.industry` 自动绑定对应行业模板
- PCB 行业模板含 7 维（含 PCB 供应商）；其他行业模板含 6 维（不含 PCB 供应商）

### O.7 数据来源维度 V3 期间（Q6 = a）

- V3 期间所有客户 `sources` 仅 `[lixiaoyun, tendata]` → 全部 A 档 → 维度无区分度但保留
- 数据来源维度的"B 外贸通"在 V3.1+ 启用（D-035 推迟）
- "C 其他网上采集"无明确实施计划

### O.8 派生子决策（V3 实施时细化）

| # | 子决策 |
| --- | --- |
| **D-039-X.1 ✅** | **factory_type 用 LLM 推断**（cleanup_service 调 LLM 基于公司名/行业/产品分析）+ **has_china_pcb_supplier V3 默认 true**（反推路径全部填 true）（用户 2026-05-06 决策）| 调研结论：腾道**不返回 factory_type**（覆盖率低已移除），用户决定 V3 仍要采集，方案 = LLM 推断；has_china_pcb_supplier 反推链路语义隐含 true，简化版方案；工作量 +0.5-1 天（LLM prompt + 调用 + fallback NULL）|
| D-039-X.2 | 各维度默认权重百分比（PCB 模板 7 维 / 其他行业模板 6 维各定）|
| D-039-X.3 | 行业分类清单（admin 配评分模板时支持哪些行业，是否与业务流 §1.1 / §1.3 关键词归一一致） |
| D-039-X.4 | 租户调权重的限制（如总和必须 100%? 单维度权重上下限？是否允许设 0%？）|
| D-039-X.5 | 是否提供"调权重后预览效果"功能（试算几个客户在新权重下的分数）|

### O.9 工作量

| 项 | 工作量 |
| --- | --- |
| clean_companies 加 2 字段 + 索引 | 0.2 天 |
| platform_scoring_templates / scoring_templates 复用现有 schema + 加默认数据 | 0.3 天 |
| admin 端"评分模板管理"页面（按行业 / 维度 / 档位 / 默认权重）| 1-2 天 |
| 租户端 `tenant/settings/scoring` 改为"调权重"UI | 0.5 天 |
| scoring worker 按模板算分 + 等级映射 + 兜底逻辑 | 1 天 |
| PCB 行业默认模板数据迁移 | 0.3 天 |
| **D-039-X.1 LLM 推断 factory_type**（cleanup_service prompt + 调 OpenRouter + fallback NULL）| **+0.5-1 天** |
| **D-039-X.1 has_china_pcb_supplier 反推默认 true**（cleanup_service IF source=tendata THEN true）| **+0.2 天** |
| 测试 | 0.5 天 |
| **小计** | **+4-5.5 天**（含 D-039-X.1）|
| **V3 总** | **17.5-31 → 21.5-36.5 天** |

## L. D-008 = B 派生的 4 个子决策（V3 实施前需逐项决定）

> D-008 用户 2026-05-05 决策选 B（重构为 6 raw + 2 clean）后派生。V3 Slice 0 启动前需要拍板。

| # | 子决策 | 候选方案 | 状态 |
| --- | --- | --- | --- |
| **D-008-B.1** | 旧 `shared_*` 数据迁移策略 | 先核实数据量：跑 `SELECT count(*) FROM shared_companies` + `shared_contacts` + `company_sources`。<br>(a) 数据量 0 / 极少 → 直接清空重建，最简单<br>(b) 数据量大 → 双写期 + 数据迁移脚本（raw 表 backfill + clean 表合并） | 🟡 待跑核实 SQL |
| **D-008-B.2** | 重构在哪个 Slice 做 | (a) Slice 0：alembic 升级（D-017）→ raw/clean 重构 → 部署 worker → 跑 R-2<br>(b) 单独立"Slice 0.5 数据库重构"在 Slice 0 之后<br>建议 (a)：必须先做完否则采集没地方落 | 🟡 待拍板 |
| **D-008-B.3 ✅ = (i)** | 同 D-015 决策：建 lixiaoyun_raw_*，业务流原版完整 6 raw 模型 | 🟢 已决策 |
| **D-008-B.4** | cleanup_queue 设计（避 Phase 1.5 D4 双唯一索引坑）| 业务流 Phase 1.5 D4：现有 cleanup_queue 对 (raw_table, raw_row_id) UNIQUE，重复采集同公司 DO NOTHING → 第二个租户漏数据。新设计要：避免 ON CONFLICT DO NOTHING 直接丢；改为按 (raw_company_id, sys_company_id) 复合键，或在 worker 层补租户分发 | 🟡 待 V3 实施时设计 |
| **D-009-A.1** | KeywordMaster 表设计 | 字段：normalized_text（全平台 UNIQUE）/ status（pending_collection/collecting/collected）/ first_collected_at / countries_hash（不同国家组合视作不同 master）；外键：collection_tasks 改 master_id；alembic 迁移：拆 collection_keywords | 🟡 V3 实施时设计 |
| **D-009-A.2** | 现有 collection_keywords 拆库策略 | 当前生产 alembic 0006，应该未跑业务（emails 空印证）；建议直接拆：(a) 删 collection_keywords；(b) 建 keyword_master + tenant_keyword(M:N) 两张表；(c) 重新走 UC-06 配置 | 🟡 V3 实施时设计 |
| **D-009-A.3** | fan-out 性能策略 | UC-11 异常 A1 业务流提："fan-out 量极大（10 万+）→ 后台异步处理 + UI 显示装载中"。建议：用 fan-out worker（独立队列）异步批量 UPSERT；提交即返回，租户 UI 显示"装载中 N 分钟" | 🟡 V3 实施时设计 |
| **D-009-A.4** | UC-11 边界处理 | (a) A 租户已 archived 但关键词已采过：B 复用时是否包含？建议**包含**（数据已存在）；(b) 归一冲突：`PCB-board` 与 `pcb board` 已是同 master（业务流 §1.3）；(c) countries 不同：建议视为不同 master（hash 不同） | 🟡 V3 实施时设计 |
| **D-017-B.1** | staging 环境（本地 docker / Sealos 副本 / Sealos clone）| 推荐：本地 docker postgres restore 生产 dump，最简单 | 🟡 V3 Slice 0.2 |
| **D-017-B.2** | pg_dump 文件存哪 + 保留期 | 推荐：本地 + 加密上传 Sealos 对象存储；保留 90 天 | 🟡 V3 Slice 0.1 |
| **D-017-B.3** | 0009 phase1_collection_schema 迁移内容 review | 唯一未读中风险迁移，Slice 0.3 跑前必读迁移源码 | 🟡 V3 Slice 0.3 前 |
| **D-017-B.4** | 跑迁移的实际执行人 | (a) 用户自己跑（kubectl exec backend pod alembic upgrade）；(b) AI 生成命令用户跑；(c) 走 CI/CD pipeline | 🟡 V3 Slice 0.3 |

## K. 已跑扩展 SQL 结果（2026-05-05）

| SQL | 结果 | 含义 |
| --- | --- | --- |
| ① alembic head | **`20260423_0006`** | 🔴 落后 7 个迁移（0007~0013，2026-04-29 ~ 2026-05-01） |
| ② emails.status 分布 | **空表** | 🔴 生产从未发邮件→sending worker 0% ready |
| ③ tenants 当前 | 5 行（3 archived + 2 active：`t-019dc236` / `t-019dc238`） | ✅ 租户基础 ready；2 个 active 可作 V3 E2E 测试 |

新增决策项 D-017/D-018/D-019 已加入 [`v3/02-er-schema-divergence.md` §7](../v3/02-er-schema-divergence.md#7-决策汇总按优先级)：

- **D-017** 🔴 V3 部署前 Slice 0 必须先 `alembic upgrade head`（含潜在 schema 风险）
- **D-018** 🔴 R-3 邮件投递接受当作 from-scratch 实施（不是补缺口）
- **D-019** V3 E2E 测试租户复用现有 `t-019dc236` + `t-019dc238`

## H+ Q-007 R-1 已发布 Sealos 部署清单（2026-05-05 用户回答，**已脱敏**）

> 🔴 用户原消息含数据库密码，已**仅记录脱敏信息**，不入仓库。详细见 [`_control/inputs/sealos/applications.md`](../inputs/sealos/applications.md)（待用户填）。

| 部署单元 | 状态 | 镜像仓库（脱敏） | 备注 |
| --- | --- | --- | --- |
| `clientget-backend` | ✅ 已部署 | aliyuncs CR / `lay_inside/clientget-backend` | — |
| `clientget-admin` | ✅ 已部署 | aliyuncs CR / `lay_inside/clientget-admin` | 前端 SPA |
| `clientget-tenant` | ✅ 已部署 | aliyuncs CR / `lay_inside/clientget-tenant` | 前端 SPA |
| `PostgreSQL` | ✅ 已部署 | Sealos 数据库 / 主机 `clientgetdb-postgresql.ns-3umexz0o.svc:5432` / 用户 `postgres` | **密码不入仓**，**强烈建议立即轮换** |
| `clientget-collection-scheduler` | ❌ 未部署 | — | 业务流 R-2 必需 |
| `clientget-collection-worker` | ❌ 未部署 | — | 业务流 R-2 必需 |
| `clientget-scoring-worker` | ❌ 未部署 | — | 业务流 §3 评分模型必需 |
| `clientget-sending-worker` | ❌ 未部署 | — | 业务流 R-3 邮件投递必需 |

**Q-007 关闭**。R-1 = 当前已部署 backend + admin + tenant + DB；**4 个 worker 全部未部署**——这是 V3 必须补齐的部分。

> 🟢 **Q-007 已决策**：R-1 = "已部署 4 单元（backend + admin + tenant + DB）的功能 ready"。这显著缩小了 V3 范围猜测：**前端 admin/tenant 已建的页面 + backend 已实现的 API 是 V3 起点**，4 个 worker + EngageLab 集成 + Phase 1.5 D1-D4 是 V3 必补缺口。

> 🔴 **新阻塞 Q-009**：当前 4 单元跑通了哪些"功能"？需对比 v0.1 草稿的 33 UC，AI 探查 backend 已实现 API + 前端已就绪页面，输出"R-1 已实现功能清单 vs UC 对照表"——下一轮 todo。

## H. D-002 架构 C 落地细节

> 2026-05-05 用户质疑"EngageLab 集中发会丢品牌+无法收回信"——AI 调研后修订 D-002 为**架构 C**：租户自有发件域名 + EngageLab 验证 + 回信回到租户自己邮箱。详见 [`v3/00-v3-target-spec.md` §0.A D-002](../v3/00-v3-target-spec.md) + [`reference-impl-aoqi.md`](../inputs/reference-impl-aoqi.md)。

| # | 状态 | 问题 | 影响 |
| --- | --- | --- | --- |
| Q-002.1 | 🟢 已决策 (D-024 修订) | UC-05 = **仅 admin 端域名配置流程**（用户 2026-05-05 澄清）：运营在 admin 端添加客户域名 → EngageLab 自动生成 SPF/DKIM/DMARC 记录 → **运营配置 DNS 记录**（DNS 写入由平台运营负责）→ 运营点验证 → 完成。**tenant 端无任何 UI 入口** | 复用现有 admin/Tenants 详情页域名管理；`domain_warmup_status` 表（D-013）已含 spf/dkim/dmarc 字段，复用 |
| Q-002.2 | 🟢 已决策 | EngageLab 凭证管理在 admin 端（与 D-024 同位置：admin/Tenants 详情页或独立 admin/email-providers） | `email_providers` 表（平台级 EngageLab API 账号配置）|
| Q-002.3 | 🟢 已决策 D-004 + D-027 | 1 租户 N 域名（不限）；EngageLab API_USER = **平台单账号全局**（D-027 = a）；所有租户域名挂在 1 个 EngageLab 账号下；当租户量 ≥ 20 时 V3.1+ 重新评估 | `tenant_email_domains` 是 1:N，`email_providers` 单条 |
| Q-002.4 | 🟢 已决策 | "保护发件邮箱信誉" = 由**平台运营**通过预热档位保障；租户域名信誉由租户自己注意 | 文档修订 |
| Q-002.5 | 🟢 已决策 D-005 | 默认 `Reply-To = From`（同一邮箱收发），不支持自定义 Reply-To 不等于 From | UI 简化 |
| Q-002.6 | 🟢 已决策 D-028 = (c) | admin 端域名验证失败诊断 = **完整 EngageLab 诊断信息（SPF/DKIM/DMARC/MX 逐项）+ 一键复制 DNS 记录按钮**；运营拿完整信息后**自行配置 DNS**（DNS 写入由平台运营负责）（D-024 修订后是 admin 端 UI 不是 tenant） | admin/Tenants 详情页域名管理 |
| Q-002.7 | 🟢 已决策 D-007（选 c） | 维持架构 C，**放弃 EngageLab Inbound 自动检测**。回信回租户自己邮箱（业务流 §4.5 原样保留）；UC-30 手动标"已回复"保留；自动检测推迟到 V3.1+ | EngageLab 仅作出口通道（发件 + DKIM 验证），不做 inbound webhook |

## I. V3 整体范围 R-1 待澄清

| # | 状态 | 问题 | 影响 |
| --- | --- | --- | --- |
| Q-007 | 🔴 阻塞 | 用户口述 R-1 "现在线上已发布功能全部 ready" 中的"线上"指什么？AI 调研发现**两条线索**：(1) `frontend/` 有 commit `1c99908 Allow Sealos preview hosts` + `0795351 Allow xinanpcb preview hosts` —— 暗示前端**已部署到 Sealos preview / xinanpcb 域名**；(2) backend 有完整 SEALOS_DEPLOYMENT.md（8 部署单元）+ commit `bb88ca1 document sealos build and args pitfalls` —— 暗示已经部署过且踩过坑。**待用户回答**：(a) `xinanpcb` preview 是哪个 URL？哪些功能已发布？(b) 当前 Sealos 上 8 个单元跑了几个？(c) "线上已发布"指 (a) 还是 (b)？ | §2 Scope 收敛 33 UC 子集 |
| Q-008 | 🟢 已决策 D-029 = (A)（**D-032 修订**）| 全部未表态 UC 在 V3 范围，**但 UC-31/32/33 经 D-032 推迟 V3.1+**；UC-04/07/08/09/17~24 仍在 V3 | 32 UC 中 29 UC 在 V3，3 UC（UC-31/32/33）推迟 V3.1+ |

## 已关闭

<!-- 决策后挪到这里 -->

| # | 决策日期 | 摘要 |
| --- | --- | --- |
| F（决策为 D-003） | 2026-05-05 | 单一真源 = V3 Target Spec，参考材料冲突由用户拍板 |
| A1 范围（部分） | 2026-05-05 | 用户标"重新调整范围"，待口述；v0.1 草稿命题暂保留作参考结构 |
